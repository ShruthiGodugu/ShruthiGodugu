from twilio.rest import Client
import os

TWILIO_SID = os.getenv("twilio_sid")
TWILIO_AUTH_TOKEN = os.getenv("twilio_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("twilio_phone")
USER_PHONE_NUMBER = os.getenv("user_phone")

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

try:
    message = twilio_client.messages.create(
        body="🚨 Test Alert from Twilio!",
        from_=TWILIO_PHONE_NUMBER,
        to=USER_PHONE_NUMBER
    )
    print(f"✅ Test message sent successfully! SID: {message.sid}")
except Exception as e:
    print(f"❌ Twilio Error: {e}")
