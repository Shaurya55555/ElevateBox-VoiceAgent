# OmniDimension version (reference)

Original build before switching to the free-tier Twilio/Google/Gemini
stack, because OmniDimension required buying an Indian phone number
($5.06/month, no free option, KYC verification needed).

`agent_setup.py` was **live-tested** against a real OmniDimension API key
on 2026-08-23: a throwaway agent was successfully created and deleted,
confirming `client.agent.create()` works with
`voice={"provider":"sarvam","voice_id":52}` and
`model={"provider":"openai","model":"gpt-4o-mini"}` (Sarvam's own LLM
returns a 400 — not enabled on the free-tier org). `dispatch_call_omnidim.py`
and `webhook_server.py` were written but never run against a live call.

Revisit this if the free stack (see the top-level `README.md`) hits a wall
that's cheaper to solve by paying OmniDimension $5/month than by debugging
Twilio Media Streams + Google STT/TTS glue code ourselves.
