import pywhatkit as pwk
import pyautogui
import time
import sqlite3
from datetime import datetime

def send_group_alert(student_name, roll_no, status="Present", time_str=""):
    try:
        # Ungaloda WhatsApp Group ID
        GROUP_ID = "BsI0z8g4Lks2J4BUj9TXs1" 
        
        print(f"📲 Sending {status} alert to College Parent Group for {student_name} ({roll_no})")
        
        if status == "Present":
            message = f"🟢 Attendance Alert:\nStudent: {student_name} ({roll_no})\nStatus: PRESENT\nTime: {time_str}\nArrived safely at college."
        else:
            message = f"🔴 Attendance Alert:\nStudent: {student_name} ({roll_no})\nStatus: ABSENT\nDate: {time_str}\nPlease verify with the college."
            
        # Send message instantly to the WhatsApp Group using Group ID
        pwk.sendwhatmsg_to_group_instantly(
            group_id=GROUP_ID,
            message=message,
            wait_time=15,
            tab_close=False
        )
        
        time.sleep(4)
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.press('return')
        
        print(f"✅ Group alert sent successfully for {student_name}!")
        
        # Save log to database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notification_logs (name, roll_no, parent_phone, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (student_name, roll_no, "Parent WhatsApp Group", status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        time.sleep(2)
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Error sending group alert: {e}")