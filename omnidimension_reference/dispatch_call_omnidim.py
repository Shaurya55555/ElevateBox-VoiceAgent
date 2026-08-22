"""
Triggers the actual outbound call. Run after agent_setup.py and after you've
acquired/attached a phone number to call *from* (client.phone_number.list()
after acquiring one via the OmniDimension dashboard's Phone & Telephony
section — number acquisition itself isn't exposed in this SDK version, so
that step is dashboard-only).

Usage:
    python dispatch_call.py <agent_id> <from_number_id>
"""

import os
import sys

from dotenv import load_dotenv
from omnidimension import Client

load_dotenv()

client = Client(api_key=os.environ["OMNIDIM_API_KEY"])

TARGET_NUMBER = os.environ.get("TARGET_PHONE_NUMBER", "+918688664337")


def dispatch(agent_id: int, from_number_id: int | None = None):
    result = client.call.dispatch_call(
        agent_id=agent_id,
        to_number=TARGET_NUMBER,
        from_number_id=from_number_id,
        call_context={},
    )
    print(result)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dispatch_call.py <agent_id> [from_number_id]")
        sys.exit(1)
    agent_id = int(sys.argv[1])
    from_number_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    dispatch(agent_id, from_number_id)
