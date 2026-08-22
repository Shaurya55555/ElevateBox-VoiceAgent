"""
Places the outbound call via Twilio. Twilio then fetches TwiML from
/twiml on our own server (app.py), which connects the call's audio to
/media-stream over WebSocket.

Usage:
    python dispatch_call.py
"""

import os

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TARGET_NUMBER = os.environ.get("TARGET_PHONE_NUMBER", "+918688664337")


def dispatch():
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    webhook_base = os.environ["WEBHOOK_BASE_URL"].rstrip("/")
    call = client.calls.create(
        to=TARGET_NUMBER,
        from_=os.environ["TWILIO_FROM_NUMBER"],
        url=f"{webhook_base}/twiml",
    )
    print("Call SID:", call.sid, "status:", call.status)
    return call


if __name__ == "__main__":
    dispatch()
