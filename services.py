import os
from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def send_sms_otp(phone_number, otp):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_PHONE_NUMBER")
    if not all([sid, token, from_num]):
        print("⚠️ Twilio not configured")
        return False
    try:
        client = Client(sid, token)
        client.messages.create(
            body=f"Your OTP is: {otp}",
            from_=from_num,
            to=phone_number
        )
        print(f"✅ SMS sent to {phone_number}")
        return True
    except Exception as e:
        print(f"❌ SMS error: {e}")
        return False

def send_email_otp(email, otp):
    key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("SENDER_EMAIL")
    if not all([key, sender]):
        print("⚠️ SendGrid not configured")
        return False
    try:
        sg = sendgrid.SendGridAPIClient(key)
        mail = Mail(
            from_email=sender,
            to_emails=email,
            subject="Account Unlock OTP",
            html_content=f"<strong>Your OTP is: {otp}</strong>"
        )
        sg.send(mail)
        print(f"✅ Email sent to {email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False