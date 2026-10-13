"""Backend for the Vapi assistant: tool-call webhook + end-of-call webhook.

Vapi handles the live audio loop (STT/LLM/TTS/turn-taking/interruption).
This service is called at two points:

1. Mid-call, when the assistant invokes a tool: we extract facts, classify
   Hot/Warm/Cold, fire the mid-call WhatsApp on Hot, or store a callback,
   then return a result the assistant reads out.
2. After the call ends, Vapi POSTs an end-of-call report with the full
   transcript, and we compose and send the post-call WhatsApp from it.

Reliability: tool calls are idempotent per toolCallId (a Vapi retry gets the
stored result, never a second WhatsApp), the end-of-call report is processed
once per call id, and every step logs a structured JSON line with the call
id. If WEBHOOK_SECRET is set, requests must carry it in X-Vapi-Secret.

Field names follow Vapi's server-message spec. They have been exercised with
simulated payloads (tests/), not yet with a payload from a real call.
"""

import hmac
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

load_dotenv()

import decision_engine
import messages
import scheduler
import whatsapp
from logging_utils import log_event

app = FastAPI()
scheduler.init_db()

RESUME_PUBLIC_URL = os.environ.get("RESUME_PUBLIC_URL", "")
ARCHITECTURE_IMAGE_URL = os.environ.get("ARCHITECTURE_IMAGE_URL", "")
SHAURYA_PHONE = os.environ.get("SHAURYA_PHONE_DISPLAY", "+91-7985200306")
FOLLOWUP_TEMPLATE = os.environ.get("WA_TEMPLATE_FOLLOWUP", "post_call_followup")

# Per-call state within one process: facts learned and whether the Hot
# WhatsApp has fired. Durable de-duplication lives in scheduler.processed_events.
_call_state: dict[str, dict] = {}


def _state_for(call_id: str) -> dict:
    return _call_state.setdefault(call_id, {"whatsapp_sent": False, "facts": {}})


def _check_secret(request: Request) -> None:
    expected = os.environ.get("WEBHOOK_SECRET", "")
    if not expected:
        return
    supplied = request.headers.get("x-vapi-secret", "")
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="bad secret")


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    _check_secret(request)
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type")
    call_id = (message.get("call") or {}).get("id", "unknown")
    log_event("webhook_received", call_id, type=msg_type)

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
        event_key = f"tool:{tool_call_id}" if tool_call_id else None

        if event_key:
            cached = scheduler.get_event(event_key)
            if cached is not None:
                log_event("tool_call_duplicate", call_id, tool_call_id=tool_call_id)
                results.append({"toolCallId": tool_call_id, "result": cached})
                continue

        fn = tool_call.get("function", {})
        name = fn.get("name")
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}

        try:
            if name == "extract_and_classify":
                result = _run_extract_and_classify(call_id, caller_number, args, state)
            elif name == "schedule_callback":
                result = _run_schedule_callback(call_id, caller_number, args, state)
            else:
                result = {"error": f"unknown tool {name}"}
        except Exception as exc:  # noqa: BLE001 - report to the agent, never crash the call
            log_event("tool_call_error", call_id, tool=name, error=str(exc))
            result = {"error": str(exc)}

        if event_key and "error" not in result:
            scheduler.save_event(event_key, result)
        results.append({"toolCallId": tool_call_id, "result": result})

    return {"results": results}


def _run_extract_and_classify(call_id: str, caller_number: str, args: dict, state: dict) -> dict:
    classification = decision_engine.classify(args.get("transcript_so_far", ""))
    state["facts"] = {**state["facts"], **classification}
    log_event("classified", call_id, label=classification.get("classification"))

    if classification.get("classification") == "Hot" and not state["whatsapp_sent"]:
        body = messages.midcall_message(classification, SHAURYA_PHONE)
        try:
            whatsapp.send_text_or_template(
                caller_number, body, FOLLOWUP_TEMPLATE,
                messages.template_params_followup(classification, SHAURYA_PHONE),
                call_id=call_id)
            state["whatsapp_sent"] = True
            log_event("midcall_whatsapp_sent", call_id)
        except Exception as exc:  # noqa: BLE001
            log_event("midcall_whatsapp_failed", call_id, error=str(exc))
            return {**classification, "whatsapp_error": str(exc)}
    return classification


def _run_schedule_callback(call_id: str, caller_number: str, args: dict, state: dict) -> dict:
    phrase = args.get("requested_time_raw", "")
    barrier = args.get("barrier", "")
    now_iso = datetime.now(timezone.utc).isoformat()
    parsed = decision_engine.parse_callback_time(phrase, now_iso)
    callback_id = scheduler.add_callback(
        caller_phone_number=caller_number, requested_time_raw=phrase,
        parsed_datetime=parsed["parsed_datetime"], barrier=barrier)
    state["facts"]["callback_time"] = parsed["parsed_datetime"]
    log_event("callback_scheduled", call_id, callback_id=callback_id,
              parsed_datetime=parsed["parsed_datetime"])
    return {"confirmed_datetime": parsed["parsed_datetime"]}


async def _handle_end_of_call(message: dict) -> None:
    call = message.get("call", {})
    call_id = call.get("id", "unknown")
    caller_number = (call.get("customer") or {}).get("number", "")

    event_key = f"eoc:{call_id}"
    if call_id != "unknown" and scheduler.get_event(event_key) is not None:
        log_event("end_of_call_duplicate", call_id)
        return

    facts = _state_for(call_id).get("facts") or {}
    artifact = message.get("artifact", {})
    transcript = artifact.get("transcript", "") or message.get("summary", "")

    if not facts and transcript:
        try:
            facts = decision_engine.classify(transcript)
        except Exception as exc:  # noqa: BLE001
            log_event("fallback_classify_failed", call_id, error=str(exc))
            facts = {}

    body = messages.postcall_message(facts, SHAURYA_PHONE)
    try:
        whatsapp.send_text_or_template(
            caller_number, body, FOLLOWUP_TEMPLATE,
            messages.template_params_followup(facts, SHAURYA_PHONE), call_id=call_id)
        # Attachments are free-form and only deliver inside the 24h window.
        if RESUME_PUBLIC_URL:
            whatsapp.send_document(caller_number, RESUME_PUBLIC_URL,
                                   "Shaurya_Bajpai_Resume.pdf", call_id=call_id)
        if ARCHITECTURE_IMAGE_URL:
            whatsapp.send_image(caller_number, ARCHITECTURE_IMAGE_URL,
                                "How this system was built", call_id=call_id)
        log_event("postcall_whatsapp_sent", call_id)
        # Only mark processed on success, so a Vapi retry can try the send again.
        scheduler.save_event(event_key, {"classification": facts.get("classification", "")})
    except Exception as exc:  # noqa: BLE001 - best effort, call already ended
        log_event("postcall_whatsapp_failed", call_id, error=str(exc))

    _call_state.pop(call_id, None)


@app.get("/health")
async def health():
    return {"status": "ok", "db": "postgres" if scheduler.using_postgres() else "sqlite"}
