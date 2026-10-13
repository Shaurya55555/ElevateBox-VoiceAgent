# STT and TTS comparison

Status: **harness built and smoke-tested; human-recorded dialect samples not yet collected.**
Run date: 2026-10-13. Tool: `tools/stt_tts_compare.py`.

## What was measured

### TTS: do the available voices handle Hindi and Telugu?

Deepgram Aura-2 voices (`luna`, `thalia`, `andromeda`, `helena`) were sent one
sentence each in English, Hindi (Devanagari) and Telugu script. The API accepts
every request. To get an objective signal without a listener, each generated
clip was transcribed back with Groq Whisper large-v3 and compared with the
input sentence (word error rate, lower is better). This is a round-trip
intelligibility proxy, not a naturalness score.

| voice | language | round-trip WER |
|---|---|---|
| aura-2-luna-en | English | 0.07 |
| aura-2-luna-en | Hindi | 0.52 |
| aura-2-luna-en | Telugu | 0.75 |
| aura-2-thalia-en | English | 0.07 |
| aura-2-thalia-en | Hindi | 0.64 |
| aura-2-thalia-en | Telugu | 0.62 |

Reading: the Aura-2 voices are English voices. They produce Hindi and Telugu
that is only partly intelligible (roughly half the words did not survive the
round trip) while English is almost clean. A Hindi or Telugu reply spoken by
this stack should be expected to sound wrong to a native listener. Fixing it
needs a TTS provider with real Hindi and Telugu voices; changing the voice in
`vapi_setup.py` is a one-line change once a provider and key are chosen.

Limits: two voices were round-tripped (the other two were generated but not
transcribed), one sentence per language, one STT model as the judge, and no
human listening. Whisper itself makes errors on Telugu.

### STT: Deepgram Nova-3 against Groq Whisper large-v3

The harness is ready (`python tools/stt_tts_compare.py stt`), but it needs
recordings of real people speaking known sentences, listed in
`docs/stt_samples/manifest.json`. None exist yet, so **no STT accuracy
number is claimed anywhere.**

To collect: record 10 to 20 short sentences each in English, Hindi,
Hinglish and Telugu-English (phone voice memos are fine, WAV or convert to
WAV), write what was said as the `reference`, set `"kind": "human"`, and run
the command. Have a native Telugu speaker produce and check the Telugu
references.

## Still to do by a person

- Listen to the samples in `docs/tts_samples/` (regenerate with
  `python tools/stt_tts_compare.py tts`) and fill a 1 to 5 naturalness score
  and a list of robotic pauses and mispronunciations with timestamps.
- Record the STT sample set above.
