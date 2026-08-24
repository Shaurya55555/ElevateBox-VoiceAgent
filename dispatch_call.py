"""Trigger an outbound call via Vapi. Target number is a config value —
swap TARGET_NUMBER (or pass one on the command line) once Exotel KYC
clears and the assistant is calling a real telephony number.
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.environ["VAPI_API_KEY"]
ASSISTANT_ID = os.environ["VAPI_ASSISTANT_ID"]
PHONE_NUMBER_ID = os.environ["VAPI_PHONE_NUMBER_ID"]

DEFAULT_TARGET = os.environ.get("TARGET_PHONE_NUMBER", "+917985200306")


def dispatch(target_number: str):
    resp = requests.post(
        "https://api.vapi.ai/call",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "assistantId": ASSISTANT_ID,
            "phoneNumberId": PHONE_NUMBER_ID,
            "customer": {"number": target_number},
        },
        timeout=30,
    )
    if not resp.ok:
        print(resp.status_code, resp.text)
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    dispatch(target)
