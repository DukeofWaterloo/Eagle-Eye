from twilio.rest import Client
from config import Config
from flask_mail import Message, Mail

def send_sms_alert(phone_number, review_preview, business_name):
    if Config.DEMO_MODE:
        print(f"[DEMO MODE] SMS to {phone_number}: {review_preview}")
        return True
    if not all([Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN, Config.TWILIO_PHONE_NUMBER]):
        print("Twilio credentials not set. Skipping SMS alert.")
        return False

    try:
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"New review for {business_name}: {review_preview[:50]}...\n\nRespond here: http://yourdomain.com/reviews",
            from_=Config.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"SMS sent to {phone_number}: {message.sid}")
        return True
    except Exception as e:
        print(f"Twilio error: {e}")
        return False

mail = Mail()

def send_email_alert(recipient, review_preview, business_name):
    if Config.DEMO_MODE:
        print(f"[DEMO MODE] Email to {recipient}: {review_preview}")
        return True
    try:
        msg = Message(
            subject=f"New review for {business_name}",
            recipients=[recipient],
            body=f"New review for {business_name}: {review_preview[:200]}...\n\nRespond here: http://yourdomain.com/reviews"
        )
        mail.send(msg)
        print(f"Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
