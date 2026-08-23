"""
The conversation brain: Gemini with automatic function calling. Gemini
decides when to call send_midcall_whatsapp / send_followup_whatsapp based
on the system prompt's classification rules in agent_prompt.md, and the
SDK executes them for us and folds the result back into the conversation.

NOT YET LIVE-TESTED (no Gemini/Twilio/Google Cloud credentials available
while writing this) — verify chat.start_chat(enable_automatic_function_calling=True)
still matches the installed google-generativeai version before relying on it;
this has been a stable, documented feature but pin/check on first run.
"""

import os

import google.generativeai as genai

import whatsapp

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

MY_NUMBER = "+917985200306"

SYSTEM_PROMPT = """
You are Ananya, calling on behalf of Shaurya Bajpai, offering e-commerce
website development. Your credibility is real work: Shaurya built an
e-commerce microservice platform (Next.js, Node.js, MongoDB, Kafka,
GraphQL) with buyer/seller/admin roles, JWT auth, and an order workflow.
Sound like a person on the phone, not a script - react to what the caller
says before moving to the next question.

LANGUAGE: Detect the caller's language from their first reply - Telugu,
Hindi, or English. Continue in that language. Handle code-switching
mid-sentence without breaking flow or forcing a language switch back.

DISCOVERY - ask one at a time, acknowledging each answer before moving on:
1. What are you looking to sell online?
2. Roughly how many products/listings?
3. Do you already have a website, or starting from scratch?
4. What's your rough budget?
5. What's your timeline - weeks, or exploratory?
6. Anything specific needed - payments, inventory, multiple sellers?

CLASSIFICATION - continuously evaluate as Hot, Warm, or Cold:
- HOT: clear budget mentioned, explicit urgency, direct ask for
  price/timeline, or "let's do this". The INSTANT you detect Hot, call
  send_midcall_whatsapp with what you've learned so far. Do not wait for
  the call to end. Do not pause the conversation to do this.
- WARM: real interest with a named barrier (budget tight, needs to check
  with someone, timing). Capture the barrier's exact wording. Ask if a
  specific callback time works; if given, resolve it to plain language.
- COLD: vague/browsing, no budget or timeline, deflects. Don't push, thank
  them, end politely.

At the NATURAL END of every call, regardless of classification, call
send_followup_whatsapp with everything you learned.
""".strip()


def send_midcall_whatsapp(
    caller_phone_number: str,
    budget: str = "not mentioned yet",
    products: str = "not mentioned yet",
    timeline: str = "not mentioned yet",
) -> dict:
    """Call the instant the caller is classified Hot. Fires a WhatsApp with
    what's been learned so far. Does not end or pause the call.

    Args:
        caller_phone_number: caller's phone number, E.164 format.
        budget: budget mentioned so far.
        products: what they're looking to sell.
        timeline: timeline mentioned so far.
    """
    message = (
        f"Hey! Following up on our call just now - sounds like you're "
        f"looking to sell {products}, budget around {budget}, timeline "
        f"{timeline}. I'll get straight to details - you can reach me "
        f"directly on {MY_NUMBER}."
    )
    try:
        whatsapp.send_text(caller_phone_number, message)
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def send_followup_whatsapp(
    caller_phone_number: str,
    classification: str,
    budget: str = "",
    products: str = "",
    timeline: str = "",
    barrier: str = "",
    callback_time: str = "",
) -> dict:
    """Call once, at the natural end of every call, regardless of
    classification. Sends the full context-rich follow-up plus resume and
    architecture image.

    Args:
        caller_phone_number: caller's phone number, E.164 format.
        classification: Hot, Warm, or Cold.
        budget: budget mentioned.
        products: what they're looking to sell.
        timeline: timeline mentioned.
        barrier: named barrier for Warm leads, verbatim if possible.
        callback_time: resolved callback time, plain language.
    """
    lines = ["Hey! This is Shaurya's team following up after our call."]
    if products or budget or timeline:
        lines.append(
            f"Sounds like you're looking to build {products or 'your site'}, "
            f"budget-wise thinking {budget or 'TBD'}, hoping to launch "
            f"{timeline or 'soon'}."
        )
    if classification == "Warm" and barrier:
        lines.append(f"Totally understand about {barrier} - no rush at all.")
    if callback_time:
        lines.append(f"I'll give you a call back {callback_time}.")
    lines.append(f"Or reach me directly anytime on {MY_NUMBER}.")
    lines.append("Attaching my resume and a quick look at how this system was built.")
    message = " ".join(lines)

    results = {}
    try:
        results["text"] = whatsapp.send_text(caller_phone_number, message)
        resume_url = os.environ.get("RESUME_PUBLIC_URL", "")
        arch_url = os.environ.get("ARCHITECTURE_IMAGE_URL", "")
        if resume_url:
            results["resume"] = whatsapp.send_document(
                caller_phone_number, resume_url, "Shaurya_Bajpai_Resume.pdf",
                caption="My resume",
            )
        if arch_url:
            results["architecture"] = whatsapp.send_image(
                caller_phone_number, arch_url, caption="How this system was built",
            )
        return {"success": True, "results": results}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "partial": results}


model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
    tools=[send_midcall_whatsapp, send_followup_whatsapp],
)


class ConversationSession:
    """One per live call. Wraps a Gemini chat with automatic function calling."""

    def __init__(self, caller_phone_number: str):
        self.caller_phone_number = caller_phone_number
        self.chat = model.start_chat(enable_automatic_function_calling=True)

    def opening_line(self) -> str:
        return (
            "Hi, this is Ananya calling on behalf of Shaurya - is this a "
            "good time? I help people get an e-commerce website built, "
            "quickly and properly. Mind if I ask a few quick questions to "
            "see if it's a fit?"
        )

    def respond(self, user_text: str) -> str:
        """Send the caller's latest transcribed utterance, get the agent's
        reply text. Gemini may call the WhatsApp tools internally along the
        way - the SDK handles executing them and folding results back in."""
        # The caller's own phone number isn't something Gemini can know
        # unless told - prime it once per session rather than every turn.
        response = self.chat.send_message(
            f"[caller_phone_number={self.caller_phone_number}] {user_text}"
        )
        return response.text
