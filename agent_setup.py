"""
Creates the OmniDimension agent, wires it to our webhook actions, and
prints the agent_id + phone_number_id you need for dispatch_call.py.

Verified against the installed `omnidimension` SDK source (v as of
2026-08-23) rather than guessed — see README for how. Run once per agent
version; re-run `update_agent()` after editing agent_prompt.md content
below instead of creating duplicates.

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # fill in OMNIDIM_API_KEY, WEBHOOK_BASE_URL
    python agent_setup.py
"""

import os

from dotenv import load_dotenv
from omnidimension import Client

load_dotenv()

client = Client(api_key=os.environ["OMNIDIM_API_KEY"])

WEBHOOK_BASE_URL = os.environ["WEBHOOK_BASE_URL"].rstrip("/")

WELCOME_MESSAGE = (
    "Hi, this is Ananya calling on behalf of Shaurya — is this a good time? "
    "I help people get an e-commerce website built, quickly and properly. "
    "Mind if I ask a few quick questions to see if it's a fit?"
)

CONTEXT_BREAKDOWN = [
    {
        "title": "Persona and credibility",
        "body": (
            "You are Ananya, calling on behalf of Shaurya Bajpai, offering "
            "e-commerce website development. Your credibility is real work: "
            "Shaurya built an e-commerce microservice platform (Next.js, "
            "Node.js, MongoDB, Kafka, GraphQL) with buyer/seller/admin roles, "
            "JWT auth, and an order workflow. Sound like a person on the "
            "phone, not a script — react to what the caller says before "
            "moving to the next question."
        ),
    },
    {
        "title": "Language handling",
        "body": (
            "Detect the caller's language from their first reply: Telugu, "
            "Hindi, or English. Continue in that language for the rest of "
            "the call. Handle code-switching mid-sentence (Telugu/English "
            "or Hindi/English mixed) without breaking flow or forcing a "
            "language switch back."
        ),
    },
    {
        "title": "Discovery questions",
        "body": (
            "Ask, one at a time, acknowledging each answer briefly before "
            "moving on: (1) What are you looking to sell online? (2) "
            "Roughly how many products/listings? (3) Do you already have a "
            "website, or starting from scratch? (4) What's your rough "
            "budget? (5) What's your timeline — weeks, or exploratory? (6) "
            "Anything specific needed — payments, inventory, multiple "
            "sellers?"
        ),
    },
    {
        "title": "Classification and required actions",
        "body": (
            "Continuously classify the lead as Hot, Warm, or Cold. HOT = "
            "clear budget mentioned, or explicit urgency, or a direct ask "
            "for price/timeline, or 'let's do this' — the instant you "
            "detect Hot, call the send_midcall_whatsapp action with the "
            "caller's phone number, budget, products, and timeline learned "
            "so far, without pausing the conversation. WARM = real interest "
            "with a named barrier (budget tight, needs to check with "
            "someone, timing) — capture the barrier's exact wording, ask if "
            "a specific callback time works, and if they give a time call "
            "the same day. COLD = vague/browsing, no budget or timeline, "
            "deflects — don't push, thank them, end politely. In every "
            "case, at the natural end of the call, call the "
            "send_followup_whatsapp action with everything learned: "
            "caller_phone_number, classification, budget, products, "
            "timeline, barrier (if any), callback_time (if any)."
        ),
    },
    {
        "title": "Scheduling from speech",
        "body": (
            "When the caller names a callback time in natural speech (e.g. "
            "'tomorrow morning', 'Monday around 11', 'end of this week'), "
            "resolve it to a concrete time, confirm it back in plain "
            "language, and pass it as callback_time when you call "
            "send_followup_whatsapp."
        ),
    },
]


def create_agent():
    integrations = ensure_integrations()

    agent = client.agent.create(
        name="Shaurya's Ecom Sales Agent",
        context_breakdown=CONTEXT_BREAKDOWN,
        welcome_message=WELCOME_MESSAGE,
        # Verified live against the API 2026-08-23: sarvam voice_id=52
        # ("Manisha" — warm/friendly, hindi+english tagged; Telugu coverage
        # not confirmed by the provider listing, verify on a real test call)
        # requires model.provider="openai" — sarvam's own LLM ("sarvam:
        # sarvam-105b-conversations") returned 400: "not available for your
        # organization" on this account's free tier.
        voice={"provider": "sarvam", "voice_id": 52},
        model={"provider": "openai", "model": "gpt-4o-mini"},
    )
    # client.post() wraps the raw API response as {"status":..., "json":...};
    # verified live: json body is {"id":..., "name":..., "status":...} directly.
    agent_id = agent["json"]["id"]

    for integration_id in integrations.values():
        client.integrations.add_integration_to_agent(agent_id, integration_id)

    return agent_id


def ensure_integrations() -> dict:
    """Create the two custom-API actions the agent calls into. Returns {name: id}."""
    midcall = client.integrations.create_custom_api_integration(
        name="send_midcall_whatsapp",
        description=(
            "Call this the instant the caller is classified Hot, with what "
            "you've learned so far. Does not end or pause the call."
        ),
        url=f"{WEBHOOK_BASE_URL}/webhook/midcall",
        method="POST",
        body_type="json",
        body_params=[
            {"key": "caller_phone_number", "description": "Caller's phone number, E.164",
             "type": "string", "required": True, "isLLMGenerated": True},
            {"key": "budget", "description": "Budget mentioned so far",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "products", "description": "What they're looking to sell",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "timeline", "description": "Timeline mentioned so far",
             "type": "string", "required": False, "isLLMGenerated": True},
        ],
    )

    followup = client.integrations.create_custom_api_integration(
        name="send_followup_whatsapp",
        description=(
            "Call this once, at the natural end of every call, regardless "
            "of classification, with everything learned during the call."
        ),
        url=f"{WEBHOOK_BASE_URL}/webhook/followup",
        method="POST",
        body_type="json",
        body_params=[
            {"key": "caller_phone_number", "description": "Caller's phone number, E.164",
             "type": "string", "required": True, "isLLMGenerated": True},
            {"key": "classification", "description": "Hot, Warm, or Cold",
             "type": "string", "required": True, "isLLMGenerated": True},
            {"key": "budget", "description": "Budget mentioned",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "products", "description": "What they're looking to sell",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "timeline", "description": "Timeline mentioned",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "barrier", "description": "Named barrier for Warm leads, verbatim if possible",
             "type": "string", "required": False, "isLLMGenerated": True},
            {"key": "callback_time", "description": "Resolved callback time, plain language",
             "type": "string", "required": False, "isLLMGenerated": True},
        ],
    )

    def _id(resp):
        return resp["json"].get("integration_id") or resp["json"].get("id")

    return {"midcall": _id(midcall), "followup": _id(followup)}


if __name__ == "__main__":
    agent_id = create_agent()
    print("Agent created. agent_id =", agent_id)
    print("Now: attach/acquire a phone number (see README), then run dispatch_call.py")
