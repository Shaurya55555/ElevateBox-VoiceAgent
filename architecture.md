# Architecture (spec for the required diagram image)

Free-tier stack (switched from OmniDimension — see `omnidimension_reference/`
for that version, kept for reference): Twilio for telephony/Media Streams,
Google Cloud STT/TTS, Gemini for the conversation brain, Meta WhatsApp
Cloud API for messaging. All own-account free tiers, no purchase.

Flow, left to right / top to bottom:

```
[dispatch_call.py: Twilio outbound call to 8688664337]
              |
              v
   [Twilio fetches TwiML from /twiml, connects
    call audio to /media-stream over WebSocket]
              |
              v
        [app.py: real-time bridge]
   audio in -> Google STT (streaming, hi-IN +
   alt te-IN/en-IN) -> transcript -> Gemini
   (llm_agent.ConversationSession) -> reply text
   -> Google TTS (MULAW/8kHz) -> audio out
              |
   +----------+-----------+
   |                      |
[Discovery]          [Language detect
 budget/products/      + code-switch
 timeline/features       via STT alt-lang]
   |
   v
[Classification: Hot / Warm / Cold — decided by Gemini,
 per agent_prompt.md / llm_agent.SYSTEM_PROMPT]
   |
   +--- Hot ---> [Gemini calls send_midcall_whatsapp() tool
   |              -> whatsapp.py -> Meta Cloud API,
   |              fires while call is still live]
   |
   +--- Warm --> [Callback time resolved by Gemini from
   |              speech, passed to send_followup_whatsapp]
   |
   +--- Cold --> [Log + disengage politely]
              |
              v
      [Call ends]
              |
              v
   [Gemini calls send_followup_whatsapp() tool ->
    context from conversation + resume + phone
    number + architecture image, via Meta Cloud API]
```

Once a real test call is run, replace this text spec with an actual
drawn/exported image (hand-drawn on paper is explicitly fine per the
assignment) and drop it in this folder as `architecture.png`.
