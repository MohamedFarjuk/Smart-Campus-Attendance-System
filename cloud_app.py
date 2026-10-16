import hmac
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg2
import streamlit as st

st.set_page_config(page_title="Smart Campus Cloud Admin", page_icon="☁️", layout="wide")
TZ = ZoneInfo("Asia/Kolkata")


# ---------------- ADMIN LOGIN ----------------
def check_password() -> bool:
    if st.session_state.get("auth"):
        return True

    st.subheader("🔐 Admin Login - Smart Campus Portal")
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        ok = hmac.compare_digest(user, st.secrets["ADMIN_USER"]) and hmac.compare_digest(
            pwd, st.secrets["ADMIN_PASSWORD"]
        )
        if ok:
            st.session_state["auth"] = True
            st.rerun()
        st.error("😕 User ID or password incorrect")
    return False


if not check_password():
    st.stop()


# ---------------- DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    try:
        att = pd.read_sql("SELECT * FROM attendance", conn)
        stu = pd.read_sql("SELECT * FROM students", conn)
        try:
            logs = pd.read_sql("SELECT * FROM notification_logs ORDER BY id DESC", conn)
        except Exception:
            conn.rollback()
            logs = pd.DataFrame()
    finally:
        conn.close()
    return att, stu, logs


try:
    attendance_df, students_df, logs_df = load_data()
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

if "date" in attendance_df.columns:
    attendance_df["date"] = pd.to_datetime(attendance_df["date"], errors="coerce").dt.date
else:
    attendance_df["date"] = pd.NaT

# Column used to identify a student (first one found in both tables)
ID_CANDIDATES = ["student_id", "roll_no", "reg_no", "register_number", "name"]
common = [c for c in ID_CANDIDATES if c in attendance_df.columns and c in students_df.columns]
ID_COL = common[0] if common else None


def unique_count(df):
    if df.empty:
        return 0
    return df[ID_COL].nunique() if ID_COL else len(df)


# ---------------- SIDEBAR ----------------
today = datetime.now(TZ).date()
with st.sidebar:
    st.header("⚙️ Admin Panel")
    days = st.slider("Analytics range (days)", 7, 90, 30)
    threshold = st.slider("Low attendance below (%)", 50, 95, 75)
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()
    if ID_COL is None:
        st.warning("No common student ID column found. Counts use raw rows.")

start = today - timedelta(days=days - 1)
period_df = attendance_df[(attendance_df["date"] >= start) & (attendance_df["date"] <= today)]
today_df = attendance_df[attendance_df["date"] == today]

# ---------------- HEADER + KPIs ----------------
st.title("☁️ Smart Campus Cloud Dashboard & Analytics")
st.caption(f"Real-time attendance monitoring · {today:%d %b %Y} (IST)")

total_students = len(students_df)
present_today = unique_count(today_df)
absent_today = max(0, total_students - present_today)
pct_today = round(present_today / total_students * 100, 1) if total_students else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Registered Students", total_students)
c2.metric("Present Today", present_today)
c3.metric("Absent Today", absent_today)
c4.metric("Attendance Today", f"{pct_today}%")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Analytics", "📈 Attendance Records", "👥 Students", "🚫 Absentees", "📜 Notification Logs"]
)

# ---------------- ANALYTICS ----------------
with tab1:
    if period_df.empty:
        st.info("No attendance data in the selected range.")
    else:
        st.subheader(f"Daily attendance (last {days} days)")
        if ID_COL:
            daily = period_df.groupby("date")[ID_COL].nunique()
        else:
            daily = period_df.groupby("date").size()
        daily.index = pd.to_datetime(daily.index)
        st.line_chart(daily.rename("Present"))

        left, right = st.columns(2)

        with left:
            st.subheader("Attendance by weekday")
            wk = daily.groupby(daily.index.day_name()).mean().round(1)
            order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            wk = wk.reindex([d for d in order if d in wk.index])
            st.bar_chart(wk.rename("Avg present"))

        with right:
            dept_col = next((c for c in ["department", "dept", "course"] if c in students_df.columns), None)
            if dept_col and ID_COL:
                st.subheader(f"Today's presence by {dept_col}")
                merged = students_df[[ID_COL, dept_col]].drop_duplicates(ID_COL)
                present_ids = set(today_df[ID_COL])
                merged["Present"] = merged[ID_COL].isin(present_ids)
                by_dept = merged.groupby(dept_col)["Present"].agg(["sum", "count"])
                by_dept["Percent"] = (by_dept["sum"] / by_dept["count"] * 100).round(1)
                st.bar_chart(by_dept["Percent"])
            else:
                st.subheader("Top 10 most regular students")
                if ID_COL:
                    top = period_df.groupby(ID_COL)["date"].nunique().sort_values(ascending=False).head(10)
                    st.bar_chart(top.rename("Days present"))

        if ID_COL:
            st.subheader(f"⚠️ Low attendance (below {threshold}%)")
            working_days = period_df["date"].nunique()
            per_student = period_df.groupby(ID_COL)["date"].nunique()
            report = students_df[[ID_COL]].drop_duplicates().copy()
            report["Days present"] = report[ID_COL].map(per_student).fillna(0).astype(int)
            report["Working days"] = working_days
            report["Attendance %"] = (report["Days present"] / working_days * 100).round(1)
            low = report[report["Attendance %"] < threshold].sort_values("Attendance %")
            if low.empty:
                st.success("Everyone is above the threshold.")
            else:
                st.dataframe(low, width="stretch", hide_index=True)
                st.download_button(
                    "⬇️ Download low-attendance report",
                    low.to_csv(index=False).encode(),
                    "low_attendance.csv",
                    "text/csv",
                )

# ---------------- RECORDS ----------------
with tab2:
    st.subheader("Attendance Records")
    pick = st.date_input("Date range", value=(start, today))
    view = attendance_df
    if isinstance(pick, tuple) and len(pick) == 2:
        view = attendance_df[(attendance_df["date"] >= pick[0]) & (attendance_df["date"] <= pick[1])]
    q = st.text_input("Search records", placeholder="name / roll number")
    if q:
        mask = view.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        view = view[mask]
    if view.empty:
        st.info("No attendance records found.")
    else:
        st.dataframe(view, width="stretch", hide_index=True)
        st.download_button("⬇️ Download CSV", view.to_csv(index=False).encode(), "attendance.csv", "text/csv")

# ---------------- STUDENTS ----------------
with tab3:
    st.subheader("Registered Students")
    sq = st.text_input("Search students", key="stu_search")
    sview = students_df
    if sq:
        mask = sview.astype(str).apply(lambda col: col.str.contains(sq, case=False, na=False)).any(axis=1)
        sview = sview[mask]
    if sview.empty:
        st.warning("No students found.")
    else:
        st.dataframe(sview, width="stretch", hide_index=True)
        st.download_button("⬇️ Download CSV", sview.to_csv(index=False).encode(), "students.csv", "text/csv")

# ---------------- ABSENTEES ----------------
with tab4:
    st.subheader("Absent Today")
    if ID_COL is None:
        st.info("Needs a common student ID column in both tables.")
    else:
        absent = students_df[~students_df[ID_COL].isin(set(today_df[ID_COL]))]
        if absent.empty:
            st.success("No absentees today 🎉")
        else:
            st.dataframe(absent, width="stretch", hide_index=True)
            st.download_button(
                "⬇️ Download absentee list", absent.to_csv(index=False).encode(), "absent_today.csv", "text/csv"
            )

# ---------------- LOGS ----------------
with tab5:
    st.subheader("WhatsApp Alert History")
    if logs_df.empty:
        st.info("No notification logs found.")
    else:
        st.dataframe(logs_df, width="stretch", hide_index=True)