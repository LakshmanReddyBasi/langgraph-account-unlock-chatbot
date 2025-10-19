import os
from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

def send_sms_otp(phone_number, otp):
    """Sends an OTP via Twilio SMS with improved error logging."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([sid, token, from_num]):
        print("⚠️ Twilio credentials are not fully configured. Skipping SMS.", file=sys.stderr)
        return False
        
    if not phone_number:
        print("⚠️ No phone number provided for user. Skipping SMS.", file=sys.stderr)
        return False
        
    try:
        client = Client(sid, token)
        message = client.messages.create(
            body=f"Your account unlock OTP is: {otp}",
            from_=from_num,
            to=phone_number
        )
        print(f"✅ SMS sent to {phone_number} with SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ SMS error when sending to '{phone_number}': {e}", file=sys.stderr)
        return False

def send_email_otp(email, otp):
    """Sends an OTP via SendGrid Email with improved error logging."""
    key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("SENDER_EMAIL")
    
    if not all([key, sender]):
        print("⚠️ SendGrid credentials are not fully configured. Skipping email.", file=sys.stderr)
        return False
        
    if not email:
        print(f"⚠️ No email address provided for user. Skipping email.", file=sys.stderr)
        return False
        
    message = Mail(
        from_email=sender,
        to_emails=email,
        subject='Your Account Unlock OTP',
        html_content=f'<strong>Your one-time password is: {otp}</strong>'
    )
    try:
        sg = sendgrid.SendGridAPIClient(key)
        response = sg.send(message)
        print(f"✅ Email sent to {email} with status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Email error when sending to '{email}': {e}", file=sys.stderr)
        return False

