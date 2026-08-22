# Architecture (spec for the required diagram image)

Flow, left to right / top to bottom:

```
[Trigger: outbound call API call to 8688664337]
              |
              v
      [OmniDimension Agent]
   (telephony + STT + LLM + TTS,
    Hindi/Telugu/English, interruption-aware)
              |
   +----------+-----------+
   |                      |
[Discovery]          [Language detect
 budget/products/      + code-switch
 timeline/features       handling]
   |
   v
[Classification: Hot / Warm / Cold]
   |
   +--- Hot ---> [Mid-call action: WhatsApp fires
   |              while call is still live]
   |
   +--- Warm --> [Scheduler: parse spoken time ->
   |              book callback (Calendar/Cal.com)]
   |
   +--- Cold --> [Log + disengage politely]
              |
              v
      [Call ends]
              |
              v
   [Post-call WhatsApp: context from transcript +
    resume + phone number + architecture image]
```

Once a real test call is run, replace this text spec with an actual
drawn/exported image (hand-drawn on paper is explicitly fine per the
assignment) and drop it in this folder as `architecture.png`.
