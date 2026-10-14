import pywhatkit as pwk
import datetime

def send_whatsapp_alert(student_name, parent_phone, time_str):
    try:
        pwk.sendwhatmsg_instantly(
            phone_no=parent_phone, 
            message=f"Alert: Your child {student_name} arrived at college safely and attendance is marked as Present at {time_str}.", 
            wait_time=15, 
            tab_close=True,
            close_time=3
        )
        print("✅ WhatsApp alert sent successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")