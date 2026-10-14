import streamlit as st
import cv2
import face_recognition
import pickle
import os
import sqlite3
import numpy as np
from datetime import datetime
import pandas as pd
from utils.whatsapp import send_group_alert  # type: ignore

# Page Configuration
st.set_page_config(page_title="Smart Campus Attendance System", page_icon="🎓", layout="wide")

# Initialize Database (Attendance, Students & Notification Logs Tables)
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # 1. Attendance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll_no TEXT,
            date TEXT,
            time TEXT,
            session TEXT,
            status TEXT
        )
    ''')
    
    # 2. Students Master Table (Store Parent Phone Numbers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT,
            parent_phone TEXT
        )
    ''')
    
    # 3. Notification Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll_no TEXT,
            parent_phone TEXT,
            status TEXT,
            timestamp TEXT
        )
    ''')
    
    # --- DEFAULT TEST STUDENTS (Farjuk & ABC) ---
    cursor.execute("INSERT OR IGNORE INTO students (roll_no, name, parent_phone) VALUES (?, ?, ?)", 
                   ("CSE001", "Farjuk", "+919361634055"))
    cursor.execute("INSERT OR IGNORE INTO students (roll_no, name, parent_phone) VALUES (?, ?, ?)", 
                   ("CSE002", "ABC", "+919659458530"))
    
    conn.commit()
    conn.close()

init_db()

# Sidebar Navigation
st.sidebar.markdown("## Navigation Menu")
menu = st.sidebar.selectbox("Go to", [
    "Live Attendance Dashboard", 
    "Student Registration", 
    "Manage Students & Parents", 
    "Attendance Reports & Analytics", 
    "Notification Logs"
])

# --- 1. STUDENT REGISTRATION ---
if menu == "Student Registration":
    st.title("🎓 Student Registration")
    st.write("Register a student with face samples and parent contact details.")
    
    with st.form("registration_form"):
        name = st.text_input("Student Name")
        roll_no = st.text_input("Roll Number (e.g., CSE001)")
        father_phone = st.text_input("Father Phone Number (e.g., +919876543210)")
        mother_phone = st.text_input("Mother Phone Number (Optional, e.g., +919123456789)")
        submit = st.form_submit_button("Start Capturing Faces")
        
    if submit and name and roll_no and father_phone:
        parent_phones = f"{father_phone},{mother_phone}" if mother_phone else father_phone
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO students (roll_no, name, parent_phone) VALUES (?, ?, ?)", 
                       (roll_no, name, parent_phones))
        conn.commit()
        conn.close()
        
        os.makedirs("dataset", exist_ok=True)
        cap = cv2.VideoCapture(0)
        count = 0
        st.info("Capturing 20 face samples. Please look at the camera...")
        
        while count < 20:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to access camera.")
                break
                
            cv2.imshow("Capturing - Press Q to stop", frame)
            cv2.imwrite(f"dataset/{name}_{roll_no}_{count}.jpg", frame)
            count += 1
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()
        st.success(f"Successfully registered {name}! Now run `python train.py` in your terminal.")

# --- 2. MANAGE STUDENTS & PARENTS ---
elif menu == "Manage Students & Parents":
    st.title("👥 Registered Students & Parent Numbers")
    st.write("Check and manage all registered students and their respective parent contact numbers.")
    
    conn = sqlite3.connect("database.db")
    students_df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    
    if not students_df.empty:
        st.dataframe(students_df, use_container_width=True)
        
        st.markdown("### ✏️ Update Parent Phone Number")
        with st.form("update_parent_form"):
            r_no = st.selectbox("Select Roll Number", students_df['roll_no'].tolist())
            new_parent_phone = st.text_input("New Parent Phone Number(s) (e.g., +919876543210,+919123456789)")
            update_btn = st.form_submit_button("Update Parent Number")
            
            if update_btn and new_parent_phone:
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE students SET parent_phone = ? WHERE roll_no = ?", (new_parent_phone, r_no))
                conn.commit()
                conn.close()
                st.success(f"Successfully updated parent phone number for Roll No: {r_no}!")
                st.rerun()
    else:
        st.warning("No students registered yet!")

# --- 3. LIVE ATTENDANCE DASHBOARD (SINGLE & MULTI-FACE DETECTION) ---
elif menu == "Live Attendance Dashboard":
    st.title("🤖 AI-Powered Smart Campus Attendance System")
    st.subheader("Single & Crowded Classroom Multi-Face Attendance with Group WhatsApp Alerts")
    
    run_camera = st.checkbox("Start Classroom Camera")
    frame_window = st.image([])
    
    if run_camera:
        if not os.path.exists("embeddings/encodings.pickle"):
            st.warning("Encodings not found! Please register a student and run `python train.py` first.")
        else:
            data = pickle.loads(open("embeddings/encodings.pickle", "rb").read())
            cap = cv2.VideoCapture(0)
            marked_today = set()
            
            while run_camera:
                ret, frame = cap.read()
                if not ret:
                    st.error("Camera access failed.")
                    break
                    
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    matches = face_recognition.compare_faces(data["encodings"], face_encoding)
                    name = "Unknown"
                    roll_no = "N/A"
                    
                    face_distances = face_recognition.face_distance(data["encodings"], face_encoding)
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            full_info = data["names"][best_match_index]
                            parts = full_info.split("_")
                            name = parts[0]
                            roll_no = parts[1] if len(parts) > 1 else "CSE001"
                    
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, f"{name} ({roll_no})", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    if name != "Unknown" and name not in marked_today:
                        current_date = datetime.now().strftime("%Y-%m-%d")
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        current_hour = datetime.now().hour
                        session_name = "FN (Morning)" if current_hour < 13 else "AN (Afternoon)"
                        
                        conn = sqlite3.connect("database.db")
                        cursor = conn.cursor()
                        
                        cursor.execute("SELECT * FROM attendance WHERE roll_no = ? AND date = ? AND session = ?", (roll_no, current_date, session_name))
                        existing = cursor.fetchone()
                        
                        if not existing:
                            cursor.execute("INSERT INTO attendance (name, roll_no, date, time, session, status) VALUES (?, ?, ?, ?, ?, ?)",
                                           (name, roll_no, current_date, current_time, session_name, "Present"))
                            conn.commit()
                            
                            try:
                                msg_time = f"{current_time} [{session_name}]"
                                send_group_alert(name, roll_no, status="Present", time_str=msg_time)
                                print(f"Group Present alert sent successfully for {name} ({session_name})!")
                            except Exception as e:
                                print(f"WhatsApp Error: {e}")
                                
                        conn.close()
                        marked_today.add(name)
                        
                frame_window.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
            cap.release()
            cv2.destroyAllWindows()

# --- 4. ATTENDANCE REPORTS & ABSENT ALERTS (WITH SQL JOIN & TABS) ---
elif menu == "Attendance Reports & Analytics":
    st.title("📊 Attendance Reports, Analytics & Absent Alerts")
    
    tab1, tab2 = st.tabs(["🟢 Present Students Report", "🔴 Absent Students Report"])
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # --- TAB 1: PRESENT REPORT ---
    with tab1:
        st.subheader("Students Marked Present")
        conn = sqlite3.connect("database.db")
        df = pd.read_sql_query("SELECT * FROM attendance", conn)
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Present Attendance CSV",
                data=csv,
                file_name=f"present_attendance_{current_date}.csv",
                mime='text/css',
            )
        else:
            st.info("No present attendance records found yet.")

    # --- TAB 2: ABSENT REPORT (USING SQL JOIN) ---
    with tab2:
        st.subheader(f"Students Marked Absent (Date: {current_date})")
        
        conn = sqlite3.connect("database.db")
        query = """
            SELECT roll_no, name, parent_phone 
            FROM students 
            WHERE roll_no NOT IN (
                SELECT roll_no FROM attendance WHERE date = ?
            )
        """
        absent_df = pd.read_sql_query(query, conn, params=(current_date,))
        conn.close()
        
        if not absent_df.empty:
            st.dataframe(absent_df, use_container_width=True)
            
            st.markdown("---")
            if st.button("🚨 Send Absent Alerts to WhatsApp Group"):
                st.info("Sending automated absent alerts to parent group...")
                for index, row in absent_df.iterrows():
                    send_group_alert(row['name'], row['roll_no'], status="Absent", time_str=current_date)
                st.success("All Absent WhatsApp group alerts sent successfully!")
                
            absent_csv = absent_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Absent Report CSV",
                data=absent_csv,
                file_name=f"absent_students_{current_date}.csv",
                mime='text/css',
            )
        else:
            st.success("🎉 Excellent! All registered students are present today. No absent students found.")

# --- 5. NOTIFICATION LOGS ---
elif menu == "Notification Logs":
    st.title("📜 WhatsApp Notification Logs")
    st.write("Track all automated WhatsApp group alerts sent for Present and Absent statuses.")
    
    conn = sqlite3.connect("database.db")
    logs_df = pd.read_sql_query("SELECT * FROM notification_logs ORDER BY id DESC", conn)
    conn.close()
    
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No notification logs recorded yet.")