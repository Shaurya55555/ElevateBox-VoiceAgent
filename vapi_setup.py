"""One-time (re-runnable) setup: create/update the Vapi assistant via API.

Run this after editing agent_prompt.md or the tool definitions below, then
copy the printed assistant id into .env as VAPI_ASSISTANT_ID.

Voice/transcriber/model provider names are per Vapi's documented BYOK
config shape as of their public docs — verify against the Vapi dashboard
if any field gets rejected; the API is the source of truth, this is not.
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.environ["VAPI_API_KEY"]
SERVER_URL = os.environ["WEBHOOK_BASE_URL"].rstrip("/") + "/vapi/webhook"

with open("agent_prompt.md", encoding="utf-8") as f:
    AGENT_DESIGN_NOTES = f.read()

SYSTEM_PROMPT = f"""You are Ananya, calling on behalf of Shaurya Bajpai to \
pitch e-commerce website development services. Follow this design closely; \
it is your full brief, not background reading:

{AGENT_DESIGN_NOTES}

Operational instructions:
- After every caller turn where you've learned something new (budget, \
product type, product count, timeline, features, or a clear intent \
signal), call the `extract_and_classify` tool with the running transcript \
so far. Don't wait until the end of the call.
- If the caller gives a callback time (explicit or vague, e.g. "tomorrow \
morning"), call `schedule_callback` immediately with that phrase verbatim.
- Keep replies short — this is a live phone call, not a chat. One idea per \
turn.
- If interrupted, stop talking immediately and listen.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_and_classify",
            "description": (
                "Extract discovery facts from the conversation so far and "
                "classify the caller as Hot, Warm, or Cold. Call this after "
                "any turn where new information came up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "transcript_so_far": {
                        "type": "string",
                        "description": "The full conversation transcript up to this point.",
                    }
                },
                "required": ["transcript_so_far"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_callback",
            "description": "Book a callback from a spoken time expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "requested_time_raw": {
                        "type": "string",
                        "description": "The caller's exact phrase, e.g. 'tomorrow morning'.",
                    },
                    "barrier": {
                        "type": "string",
                        "description": "The reason for a Warm callback, if any (empty string if none).",
                    },
                },
                "required": ["requested_time_raw"],
            },
        },
    },
]

ASSISTANT_CONFIG = {
    "name": "ElevateBox Sales Agent",
    "model": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        "tools": TOOLS,
    },
    "voice": {
        "provider": "deepgram",
        "voiceId": "aura-2-thalia-en",
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "multi",
    },
    "serverUrl": SERVER_URL,
    "firstMessage": (
        "Hi, this is Ananya calling on behalf of Shaurya — is this a good time? "
        "I help people get an e-commerce website built, quickly and properly. "
        "Mind if I ask a few quick questions to see if it's a fit?"
    ),
    "backgroundSound": "office",
}


def create_or_update_assistant():
    existing_id = os.environ.get("VAPI_ASSISTANT_ID", "")
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    if existing_id:
        resp = requests.patch(
            f"https://api.vapi.ai/assistant/{existing_id}",
            headers=headers,
            json=ASSISTANT_CONFIG,
            timeout=30,
        )
    else:
        resp = requests.post(
            "https://api.vapi.ai/assistant",
            headers=headers,
            json=ASSISTANT_CONFIG,
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps(data, indent=2))
    print(f"\nAssistant id: {data.get('id')}")
    print("Copy this into .env as VAPI_ASSISTANT_ID if not already set.")


if __name__ == "__main__":
    create_or_update_assistant()
