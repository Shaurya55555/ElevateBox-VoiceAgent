"""Backend for the Vapi assistant: tool-call webhook + end-of-call webhook.

Vapi handles the live audio loop (STT/LLM/TTS/turn-taking/interruption)
itself. This service only gets called at two points:

1. Mid-call, when the assistant invokes a tool (function call) — we extract
   facts, classify Hot/Warm/Cold, and fire the mid-call WhatsApp or store a
   callback, then return a result the assistant reads out.
2. After the call ends, Vapi POSTs an end-of-call report with the full
   transcript — we compose and send the post-call WhatsApp from that.

NOTE: exact Vapi server-message field names (message.type values, the
tool-call/result envelope shape) should be double-checked against a live
test call before relying on this in production — written from the
documented spec, not yet verified against a real webhook payload.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

import decision_engine
import scheduler
import whatsapp

app = FastAPI()
scheduler.init_db()

RESUME_PUBLIC_URL = os.environ.get("RESUME_PUBLIC_URL", "")
ARCHITECTURE_IMAGE_URL = os.environ.get("ARCHITECTURE_IMAGE_URL", "")
SHAURYA_PHONE = os.environ.get("SHAURYA_PHONE_DISPLAY", "+91-7985200306")

# Per-call state: whether the mid-call WhatsApp has already fired, so a
# second Hot classification later in the same call doesn't double-send.
_call_state: dict[str, dict] = {}


def _state_for(call_id: str) -> dict:
    return _call_state.setdefault(call_id, {"whatsapp_sent": False, "facts": {}})


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type")

    if msg_type == "tool-calls":
        return await _handle_tool_calls(message)
    if msg_type == "end-of-call-report":
        await _handle_end_of_call(message)
        return {}

    return {}


async def _handle_tool_calls(message: dict) -> dict:
    call = message.get("call", {})
    call_id = call.get("id", "unknown")
    caller_number = (call.get("customer") or {}).get("number", "")
    state = _state_for(call_id)

    results = []
    for tool_call in message.get("toolCallList", []):
        tool_call_id = tool_call.get("id")
        fn = tool_call.get("function", {})
        name = fn.get("name")
        args = fn.get("arguments", {})
        if isinstance(args, str):
            import json

            args = json.loads(args)

        if name == "extract_and_classify":
            result = _run_extract_and_classify(caller_number, args, state)
        elif name == "schedule_callback":
            result = _run_schedule_callback(caller_number, args)
        else:
            result = {"error": f"unknown tool {name}"}

        results.append({"toolCallId": tool_call_id, "result": result})

    return {"results": results}


def _run_extract_and_classify(caller_number: str, args: dict, state: dict) -> dict:
    transcript_so_far = args.get("transcript_so_far", "")
    classification = decision_engine.classify(transcript_so_far)
    state["facts"] = classification

    if classification.get("classification") == "Hot" and not state["whatsapp_sent"]:
        body = _midcall_message(classification)
        try:
            whatsapp.send_text(caller_number, body)
            state["whatsapp_sent"] = True
        except Exception as exc:  # noqa: BLE001 - report to the agent, don't crash the call
            return {**classification, "whatsapp_error": str(exc)}

    return classification


def _run_schedule_callback(caller_number: str, args: dict) -> dict:
    phrase = args.get("requested_time_raw", "")
    barrier = args.get("barrier", "")
    now_iso = datetime.now(timezone.utc).isoformat()
    parsed = decision_engine.parse_callback_time(phrase, now_iso)
    scheduler.add_callback(
        caller_phone_number=caller_number,
        requested_time_raw=phrase,
        parsed_datetime=parsed["parsed_datetime"],
        barrier=barrier,
    )
    return {"confirmed_datetime": parsed["parsed_datetime"]}


def _midcall_message(facts: dict) -> str:
    parts = ["Hey! Great talking just now — quick summary while it's fresh:"]
    if facts.get("product_type"):
        parts.append(f"- Building for: {facts['product_type']}")
    if facts.get("product_count"):
        parts.append(f"- Catalog size: {facts['product_count']}")
    if facts.get("budget"):
        parts.append(f"- Budget: {facts['budget']}")
    if facts.get("timeline"):
        parts.append(f"- Timeline: {facts['timeline']}")
    parts.append(f"\nReach me directly anytime: {SHAURYA_PHONE}")
    return "\n".join(parts)


async def _handle_end_of_call(message: dict) -> None:
    call = message.get("call", {})
    caller_number = (call.get("customer") or {}).get("number", "")
    call_id = call.get("id", "unknown")
    state = _state_for(call_id)
    facts = state.get("facts") or {}

    artifact = message.get("artifact", {})
    transcript = artifact.get("transcript", "") or message.get("summary", "")

    if not facts:
        # No tool call fired classification during the call (e.g. call ended
        # very early) — classify from the raw transcript as a fallback.
        try:
            facts = decision_engine.classify(transcript)
        except Exception:  # noqa: BLE001
            facts = {}

    body = _postcall_message(facts, transcript)
    try:
        whatsapp.send_text(caller_number, body)
        if RESUME_PUBLIC_URL:
            whatsapp.send_document(caller_number, RESUME_PUBLIC_URL, "Shaurya_Bajpai_Resume.pdf")
        if ARCHITECTURE_IMAGE_URL:
            whatsapp.send_image(caller_number, ARCHITECTURE_IMAGE_URL, "How this system was built")
    except Exception:  # noqa: BLE001 - best effort, call already ended
        pass

    _call_state.pop(call_id, None)


def _postcall_message(facts: dict, transcript: str) -> str:
    lines = ["Hey! This is Shaurya's team following up after our call."]
    detail_bits = []
    if facts.get("product_type"):
        detail_bits.append(f"building {facts['product_type']}")
    if facts.get("product_count"):
        detail_bits.append(f"around {facts['product_count']} products")
    if facts.get("budget"):
        detail_bits.append(f"budget-wise thinking {facts['budget']}")
    if facts.get("timeline"):
        detail_bits.append(f"hoping to launch {facts['timeline']}")
    if detail_bits:
        lines.append("Sounds like you're " + ", ".join(detail_bits) + ".")
    if facts.get("barrier"):
        lines.append(f"Totally understand on {facts['barrier']} — no rush.")
    lines.append(f"\nFeel free to reach me directly on {SHAURYA_PHONE}.")
    lines.append("Attaching my resume and a quick look at how this system was built.")
    return "\n".join(lines)


@app.get("/health")
async def health():
    return {"status": "ok"}
