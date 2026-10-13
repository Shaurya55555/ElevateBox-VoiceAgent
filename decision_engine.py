"""Extraction + classification, called from Vapi tool-calls mid-conversation.

Uses Gemini (tolerates a bit more latency than the live turn loop, which
Vapi/Groq handle directly) to turn a running transcript into structured
facts and a Hot/Warm/Cold label. The Gemini client is created lazily so
modules that import this one (and the tests) work without a key.
"""

import json
import os

LABELS = ("Hot", "Warm", "Cold")
FACT_KEYS = ("budget", "product_type", "product_count", "timeline",
             "features", "barrier", "reasoning")

_CLASSIFY_PROMPT = """You are reading a live sales call transcript for an
e-commerce website development pitch. Extract what's known so far and
classify the caller's buying intent.

Rules:
- Hot: clear budget mentioned, explicit urgency, direct price/timeline ask,
  or "let's do this" / agreement to proceed.
- Warm: real interest and need, but a named barrier (budget tight, needs to
  check with someone, timing not now).
- Cold: vague/browsing, no budget or timeline, deflecting.

Respond ONLY with compact JSON, no markdown fences:
{
  "budget": "<verbatim or best paraphrase, empty string if unmentioned>",
  "product_type": "<what they sell, empty string if unmentioned>",
  "product_count": "<catalog size, empty string if unmentioned>",
  "timeline": "<verbatim or best paraphrase, empty string if unmentioned>",
  "features": "<specific features mentioned, empty string if unmentioned>",
  "classification": "Hot" | "Warm" | "Cold",
  "barrier": "<verbatim barrier if Warm, empty string otherwise>",
  "reasoning": "<one short sentence>"
}

Transcript so far:
{transcript}
"""

_SCHEDULE_PROMPT = """The caller said this about when to be called back:
"{phrase}"

Today's date/time is {now}. Resolve this into a concrete future datetime.
Respond ONLY with compact JSON, no markdown fences:
{{"parsed_datetime": "<ISO 8601>", "confidence": "high" | "low"}}
"""

_model = None


def _get_model():
    global _model
    if _model is None:
        import google.generativeai as genai

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


def parse_json_reply(text: str) -> dict:
    """Parse a model reply that should be bare JSON but may carry fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    end = text.rfind("}")
    if end != -1:
        text = text[: end + 1]
    return json.loads(text)


def normalize_classification(data: dict) -> dict:
    """Coerce the model output to the contract the rest of the app relies on."""
    out = {k: str(data.get(k) or "") for k in FACT_KEYS}
    label = str(data.get("classification", "")).strip().capitalize()
    out["classification"] = label if label in LABELS else "Cold"
    return out


def classify(transcript: str) -> dict:
    prompt = _CLASSIFY_PROMPT.replace("{transcript}", transcript)
    response = _get_model().generate_content(prompt)
    return normalize_classification(parse_json_reply(response.text))


def parse_callback_time(phrase: str, now_iso: str) -> dict:
    prompt = _SCHEDULE_PROMPT.format(phrase=phrase, now=now_iso)
    response = _get_model().generate_content(prompt)
    return parse_json_reply(response.text)
