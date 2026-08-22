"""
Webhook server the OmniDimension agent calls into as "custom API" actions
during and after the call. This is what actually fires the WhatsApp
messages — see README for why (OmniDimension's native integration types are
'custom_api' and 'cal' only; there's no built-in "send WhatsApp with a
resume+image attached" action, so we own that step ourselves for full
control over content and attachments).

Run locally with `flask --app webhook_server run` behind ngrok (or deploy
anywhere with a public HTTPS URL) — the URL goes into agent_setup.py's
custom_api integrations so OmniDimension can reach it.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import whatsapp

load_dotenv()

app = Flask(__name__)

RESUME_URL = os.environ.get("RESUME_PUBLIC_URL", "")
ARCHITECTURE_IMAGE_URL = os.environ.get("ARCHITECTURE_IMAGE_URL", "")
MY_NUMBER = "+917985200306"


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/webhook/midcall")
def midcall_action():
    """
    Fired by the agent the instant a lead is classified Hot — must not
    block the live call, so this just needs to return fast (< a couple
    seconds). Body params are LLM-generated: the agent fills in what it
    has learned so far.
    """
    data = request.get_json(force=True) or {}
    caller_number = data.get("caller_phone_number", "")
    budget = data.get("budget", "not mentioned yet")
    products = data.get("products", "not mentioned yet")
    timeline = data.get("timeline", "not mentioned yet")

    message = (
        f"Hey! Following up on our call just now — sounds like you're "
        f"looking to sell {products}, budget around {budget}, timeline "
        f"{timeline}. I'll get straight to details — you can reach me "
        f"directly on {MY_NUMBER}."
    )

    try:
        whatsapp.send_text(caller_number, message)
    except Exception as exc:  # noqa: BLE001 - report failure back to the agent, don't crash the call
        return jsonify({"success": False, "error": str(exc)}), 200

    return jsonify({"success": True})


@app.post("/webhook/followup")
def followup_action():
    """
    Fired once at call end, regardless of classification. Carries the full
    post-call WhatsApp required by the assignment: real context, framed
    like a human wrote it, phone number, resume, architecture image.
    """
    data = request.get_json(force=True) or {}
    caller_number = data.get("caller_phone_number", "")
    classification = data.get("classification", "Cold")
    budget = data.get("budget", "")
    products = data.get("products", "")
    timeline = data.get("timeline", "")
    barrier = data.get("barrier", "")
    callback_time = data.get("callback_time", "")

    lines = [
        "Hey! This is Shaurya's team following up after our call.",
    ]
    if products or budget or timeline:
        lines.append(
            f"Sounds like you're looking to build {products or 'your site'}, "
            f"budget-wise thinking {budget or 'TBD'}, hoping to launch "
            f"{timeline or 'soon'}."
        )
    if classification == "Warm" and barrier:
        lines.append(f"Totally understand about {barrier} — no rush at all.")
    if callback_time:
        lines.append(f"I'll give you a call back {callback_time}.")
    lines.append(f"Or reach me directly anytime on {MY_NUMBER}.")
    lines.append("Attaching my resume and a quick look at how this system was built.")

    message = " ".join(lines)

    results = {}
    try:
        results["text"] = whatsapp.send_text(caller_number, message)
        if RESUME_URL:
            results["resume"] = whatsapp.send_document(
                caller_number, RESUME_URL, "Shaurya_Bajpai_Resume.pdf",
                caption="My resume",
            )
        if ARCHITECTURE_IMAGE_URL:
            results["architecture"] = whatsapp.send_image(
                caller_number, ARCHITECTURE_IMAGE_URL,
                caption="How this system was built",
            )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc), "partial": results}), 200

    return jsonify({"success": True, "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
