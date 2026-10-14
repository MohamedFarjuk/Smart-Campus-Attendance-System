import streamlit as st
import pandas as pd
import psycopg2
import os

st.set_page_config(page_title="Smart Campus Cloud Admin", page_icon="☁️", layout="wide")

# --- ADMIN LOGIN SECURITY ---
def check_password():
    def password_entered():
        if st.session_state["username"] == "admin" and st.session_state["password"] == "college123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔐 Admin Login - Smart Campus Portal")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🔐 Admin Login - Smart Campus Portal")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        st.error("😕 User ID or password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- CLOUD ADMIN DASHBOARD ---
st.title("☁️ Smart Campus Cloud Dashboard & Analytics")
st.markdown("Welcome Admin! Real-time attendance monitoring across the campus.")

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres")
conn = psycopg2.connect(DATABASE_URL)

# Fetch Analytics Data
attendance_df = pd.read_sql("SELECT * FROM attendance", conn)
students_df = pd.read_sql("SELECT * FROM students", conn)
logs_df = pd.read_sql("SELECT * FROM notification_logs ORDER BY id DESC", conn)
conn.close()

# --- METRICS CARDS ---
col1, col2, col3 = st.columns(3)
total_students = len(students_df)
total_present_today = len(attendance_df[attendance_df['date'] == pd.Timestamp.today().strftime('%Y-%m-%d')])
total_absent = max(0, total_students - total_present_today)

col1.metric("Total Registered Students", total_students)
col2.metric("Present Today", total_present_today, delta="Safe")
col3.metric("Absent Today", total_absent, delta="-Alert" if total_absent > 0 else "0")

st.markdown("---")

# --- TABS FOR ADMIN MANAGEMENT ---
tab1, tab2, tab3 = st.tabs(["📈 Live Attendance Records", "👥 Student Database", "📜 WhatsApp Notification Logs"])

with tab1:
    st.subheader("Today's Attendance Logs")
    if not attendance_df.empty:
        st.dataframe(attendance_df, use_container_width=True)
    else:
        st.info("No attendance records found in cloud database.")

with tab2:
    st.subheader("Registered Students List")
    if not students_df.empty:
        st.dataframe(students_df, use_container_width=True)
    else:
        st.warning("No students registered yet.")

with tab3:
    st.subheader("WhatsApp Group Alert History")
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No notification logs found.")