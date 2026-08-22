"""
Text-only sanity check for the conversation brain — no telephony/audio
needed, just GEMINI_API_KEY. Simulates a caller typing instead of speaking,
so you can verify the discovery flow, classification, and that the
WhatsApp tool calls actually fire, before touching Twilio at all.

Usage:
    python test_gemini_agent.py
"""

import os

from dotenv import load_dotenv

load_dotenv()

from llm_agent import ConversationSession  # noqa: E402 (after load_dotenv)


def main():
    test_number = input(
        "Caller phone number to test WhatsApp sends against (E.164, e.g. +91...): "
    ).strip()
    session = ConversationSession(test_number)
    print("Agent:", session.opening_line())
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in ("quit", "exit"):
            break
        reply = session.respond(user_text)
        print("Agent:", reply)


if __name__ == "__main__":
    main()
