# Archived: Twilio + Google Cloud implementation

This was the second implementation attempt (after `omnidimension_reference/`),
built on Twilio Media Streams + Google Cloud STT/TTS + Gemini.

**Why abandoned:** Twilio's free trial can only call numbers *you* verify by
receiving an SMS/voice code on that exact number. The target number,
8688664337, belongs to ElevateBox, not Shaurya — there's no way to receive
that code without upgrading to a paid Twilio account (~$20+ to buy a number
and lift the trial restriction). No spend was authorized at the time this
was shelved.

**Current approach:** rebuilt on Vapi (orchestration) + Exotel (telephony —
KYC-gated, not destination-verification-gated, so it can call any number
once approved) + Deepgram (STT/TTS) + Groq/Gemini (LLM) + Meta WhatsApp
Cloud API. See the top-level `README.md` and `architecture.md`.

The code here is kept for reference — the STT/TTS bridging logic
(`app.py`'s `asyncio.Queue` + `call_soon_threadsafe` pattern) and the Gemini
function-calling setup (`llm_agent.py`) may still be useful if Vapi ever
needs to be swapped out for a hand-rolled pipeline.
