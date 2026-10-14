from utils.whatsapp import send_whatsapp_alert
import datetime

current_time = datetime.datetime.now().strftime("%H:%M:%S")
print("Testing WhatsApp alert function...")
send_whatsapp_alert("farjuk", "+919361634055", current_time)
