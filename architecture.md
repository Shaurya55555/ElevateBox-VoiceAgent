# Architecture (spec for the required diagram image)

Fully free stack (third rebuild — see `omnidimension_reference/` and
`google_twilio_reference/` for the two abandoned attempts and why): **Vapi**
for call orchestration (turn-taking, interruption, STT/LLM/TTS loop,
mid-call tool calls), **Exotel** for telephony (KYC-gated, not
destination-verification-gated — can call 8688664337 once approved, unlike
Twilio's trial), **Deepgram** for STT (Nova-3) and TTS (Aura-2), **Groq**
for fast in-turn LLM replies, **Gemini** for the heavier extraction/
classification step, **Meta WhatsApp Cloud API** for messaging. All
own-account free tiers.

Flow, left to right / top to bottom:

```
[dispatch_call.py: POST /call to Vapi API, assistantId + phoneNumberId
 (Exotel-backed) + target number]
              |
              v
   [Vapi: manages the live call session end-to-end —
    telephony leg via Exotel, turn-taking, interruption
    handling, STT -> LLM -> TTS loop]
              |
   +----------+-----------+
   |                      |
[Deepgram Nova-3 STT   [Deepgram Aura-2 TTS
 language=multi, ->     -> spoken reply]
 handles Hindi/Telugu/
 English + code-switch]
              |
              v
   [Groq llama-3.3-70b: fast in-conversation
    turn replies, per SYSTEM_PROMPT built from
    agent_prompt.md — discovery questions, sales pitch]
              |
              v (assistant calls a tool mid-conversation)
   [Vapi POSTs to app.py: /vapi/webhook, type=tool-calls]
              |
              v
   [decision_engine.py: Gemini classifies the transcript
    so far -> budget/products/timeline/features + Hot/Warm/Cold]
              |
   +--- Hot ---> [app.py fires whatsapp.send_text() to the
   |              caller NOW, via Meta Cloud API — call
   |              keeps running, this doesn't block audio]
   |
   +--- Warm --> [schedule_callback tool -> decision_engine
   |              parses the spoken time -> scheduler.py
   |              writes {caller, requested_time, barrier}
   |              to SQLite]
   |
   +--- Cold --> [logged via the same classify call, no
                  aggressive action]
              |
              v
        [Call ends]
              |
              v
   [Vapi POSTs to app.py: /vapi/webhook, type=end-of-call-report,
    includes full transcript]
              |
              v
   [app.py composes post-call WhatsApp from stored per-call
    facts (or a transcript fallback) + sends resume.pdf +
    architecture image, all via whatsapp.py -> Meta Cloud API]
```

Once a real test call is run, replace this text spec with an actual
drawn/exported image (hand-drawn on paper is explicitly fine per the
assignment) and drop it in this folder as `architecture.png`.
