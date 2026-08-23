"""Extraction + classification, called from Vapi tool-calls mid-conversation.

Uses Gemini (tolerates a bit more latency than the live turn loop, which
Vapi/Groq handle directly) to turn a running transcript into structured
facts and a Hot/Warm/Cold label.
"""

import json
import os

import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

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

_model = genai.GenerativeModel("gemini-2.5-flash")


def classify(transcript: str) -> dict:
    prompt = _CLASSIFY_PROMPT.replace("{transcript}", transcript)
    response = _model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    return json.loads(text)


_SCHEDULE_PROMPT = """The caller said this about when to be called back:
"{phrase}"

Today's date/time is {now}. Resolve this into a concrete future datetime.
Respond ONLY with compact JSON, no markdown fences:
{{"parsed_datetime": "<ISO 8601>", "confidence": "high" | "low"}}
"""


def parse_callback_time(phrase: str, now_iso: str) -> dict:
    prompt = _SCHEDULE_PROMPT.format(phrase=phrase, now=now_iso)
    response = _model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    return json.loads(text)
