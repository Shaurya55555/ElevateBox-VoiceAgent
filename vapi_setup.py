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
# llama-3.3-70b-versatile was retired from Groq; this is a model Groq lists
# with tool calling. Override with GROQ_MODEL if it is retired in turn.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
SERVER_URL = os.environ["WEBHOOK_BASE_URL"].rstrip("/") + "/vapi/webhook"

# Groq's free tier allows about 8,000 tokens per minute per model, and the
# whole prompt is re-sent on every turn. Send only the sections the live
# model needs; the welcome message is the assistant's firstMessage and the
# post-call text is composed by app.py.
RUNTIME_SECTIONS = ("Persona", "Language", "Discovery", "Classification",
                    "Mid-call action", "Conversation rules")


def _runtime_notes(path="agent_prompt.md") -> str:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    nl = chr(10)
    head, *parts = text.split(nl + "## ")
    # the persona paragraph that sits before the first "## " header
    keep = [head.split(nl, 1)[-1].strip()]
    for part in parts:
        title = part.split(nl, 1)[0]
        if any(name in title for name in RUNTIME_SECTIONS):
            keep.append("## " + part.strip())
    return (nl + nl).join(k for k in keep if k)


AGENT_DESIGN_NOTES = _runtime_notes()

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
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        "maxTokens": 200,
        "temperature": 0.4,
        "tools": TOOLS,
    },
    "voice": {
        "provider": "deepgram",
        "voiceId": "luna",
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "multi",
    },
    "serverUrl": SERVER_URL,
    # Barge-in: Vapi stops speaking once the caller says this many words
    # (or speaks for this long), then waits before resuming.
    "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.2, "backoffSeconds": 1.0},
    "firstMessage": (
        "Hi, this is Ananya calling on behalf of Shaurya — is this a good time? "
        "I help people get an e-commerce website built, quickly and properly. "
        "Mind if I ask a few quick questions to see if it's a fit?"
    ),
    "backgroundSound": "office",
}


if WEBHOOK_SECRET:
    ASSISTANT_CONFIG["server"] = {"url": SERVER_URL, "secret": WEBHOOK_SECRET}


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
    if not resp.ok:
        print(resp.status_code, resp.text)
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps(data, indent=2))
    print(f"\nAssistant id: {data.get('id')}")
    print("Copy this into .env as VAPI_ASSISTANT_ID if not already set.")


if __name__ == "__main__":
    create_or_update_assistant()
