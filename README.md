# ElevateBox SDE Intern Assignment

Built for ElevateBox's (ElevateScale Technologies) SDE Intern hiring
assignment: an AI voice agent that calls **8688664337** on its own, sells
e-commerce website development in Telugu/Hindi/English, classifies the lead
Hot/Warm/Cold in real time, fires a WhatsApp mid-call on high intent, books
callbacks from spoken time, and sends a post-call WhatsApp with real
conversation context, a resume, a phone number, and an architecture image.
No deck, no proposal — a working system, per their brief.

## Stack — free tier only, no purchase

Originally built on OmniDimension (bundled telephony+STT+LLM+TTS — see
`omnidimension_reference/` for that version, and its README notes below for
what was live-verified there), then rebuilt on a fully free stack since
OmniDimension required buying a phone number ($5.06/month) with no free
option. Nothing in the current stack requires paying anything:

- **Twilio** (free trial) — telephony + Media Streams (real-time call audio
  in/out over WebSocket). Trial accounts restrict outbound calls to numbers
  *within your sign-up country* — sign up with Indian account details and
  this becomes exactly what we want, calling 8688664337 for free using
  trial credit (no card charged). You'll need to verify 8688664337 as a
  caller ID via SMS (trial accounts require this).
- **Google Cloud Speech-to-Text** (free tier, streaming) — Hindi primary,
  Telugu/English as alternate language codes, `phone_call` model tuned for
  telephony audio.
- **Gemini API** (free tier, no card) — the conversation brain. Holds the
  discovery flow, Hot/Warm/Cold classification, and calls the WhatsApp
  actions itself via function calling (`llm_agent.py`).
- **Google Cloud Text-to-Speech** (free tier) — genuinely supports Telugu
  (`te-IN`) in addition to Hindi/English, output directly as MULAW/8kHz so
  it matches Twilio's audio format with no transcoding.
- **Meta WhatsApp Cloud API** (free in test mode for verified recipients) —
  mid-call and post-call messages, including resume + architecture image
  as attachments.
- **FastAPI + WebSocket** (`app.py`) — the real-time bridge tying all of
  the above together.

**Honesty check on verification status:** the OmniDimension version's
`agent_setup.py` was live-tested against a real API key (see
`omnidimension_reference/`). This rewrite has **not** been run end-to-end —
no Twilio/Google Cloud/Gemini credentials were available while writing it.
It's built against stable, well-documented APIs (Twilio Media Streams
protocol, `google-cloud-speech` StreamingRecognize, `google-cloud-texttospeech`
MULAW output, Gemini automatic function calling), but test the pieces
standalone (see below) before trusting a live call to work first try.

## Setup — what only you can do (account creation)

1. **Twilio** — sign up at twilio.com with Indian account details. Get a
   trial number (deducted from trial credit, not a real charge) and verify
   **8688664337** as a caller ID (Twilio Console → Phone Numbers → Verified
   Caller IDs → SMS verification). Gives you `TWILIO_ACCOUNT_SID`,
   `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.
2. **Google Cloud** — create a project (free, no charge without exceeding
   free tier), enable the Speech-to-Text and Text-to-Speech APIs, create a
   service account, download its JSON key → `GOOGLE_APPLICATION_CREDENTIALS`
   pointing at that file.
3. **Gemini API key** — https://aistudio.google.com/apikey (free, no card)
   → `GEMINI_API_KEY`.
4. **Meta WhatsApp Business API** — Meta Business account + WhatsApp
   Business API app at developers.facebook.com. API Setup page gives a test
   number + Phone Number ID + temporary access token. Add 8688664337 as a
   verified test recipient there → `META_WA_PHONE_NUMBER_ID`,
   `META_WA_ACCESS_TOKEN`.
5. **ngrok** (or any HTTPS tunnel) — `ngrok http 8000` once `app.py` is
   running → `WEBHOOK_BASE_URL`.

## Test the pieces standalone first

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in every value

# Conversation logic only — no telephony needed, just GEMINI_API_KEY.
# Type as if you were the caller; confirms discovery/classification/WhatsApp
# tool calls work before any audio is involved.
python test_gemini_agent.py

# TTS credentials + Telugu/Hindi/English voice check — writes playable WAVs.
python test_tts.py
```

## Run the real thing

```bash
# 1. Start the bridge server
uvicorn app:app --host 0.0.0.0 --port 8000

# 2. Tunnel it, put the forwarding URL in .env as WEBHOOK_BASE_URL
ngrok http 8000

# 3. Place the call
python dispatch_call.py
```

## Files

- `agent_prompt.md` — the conversational design in full prose (source of
  truth for `SYSTEM_PROMPT` in `llm_agent.py`): welcome message, discovery
  questions, Hot/Warm/Cold classification logic, WhatsApp message templates.
- `llm_agent.py` — Gemini chat session with automatic function calling;
  `send_midcall_whatsapp` / `send_followup_whatsapp` are real Python
  functions Gemini can call directly mid-conversation.
- `app.py` — FastAPI server: `/twiml` (Twilio fetches this on call connect)
  and `/media-stream` (WebSocket bridging Twilio audio ↔ Google STT ↔
  Gemini ↔ Google TTS).
- `dispatch_call.py` — triggers the outbound call to 8688664337 via Twilio.
- `whatsapp.py` — thin Meta Cloud API client (text/document/image sends).
- `test_gemini_agent.py`, `test_tts.py` — standalone verification, no
  telephony required.
- `architecture.md` — text spec for the required architecture diagram;
  export/draw it as `architecture.png` once the flow is confirmed working,
  and point `ARCHITECTURE_IMAGE_URL` at its raw GitHub URL.
- `resume.pdf` — Shaurya's resume, sent as a WhatsApp document attachment
  via its raw GitHub URL (`RESUME_PUBLIC_URL`).
- `omnidimension_reference/` — the original OmniDimension-based build
  (live-verified agent creation against a real API key, abandoned only
  because it required a paid phone number). Useful if the free stack hits
  a wall and paying $5/month becomes worth it.

## What to submit to ElevateBox (per their Section 06 + closing checklist)

WhatsApp all of this to **8688664337**:

1. The working prototype — trigger a live call on demand (or the fact that
   it just called them, if timed live).
2. A one-page architecture diagram, image or PDF (`architecture.png`,
   hand-drawn is explicitly fine per their brief).
3. A short note, **under 200 words**: what works, what doesn't, what you'd
   build next.
4. Your resume (`resume.pdf`).
5. Your mobile number.
6. A repo link, if you have one — this repo.

Do **not** send a deck, a proposal, or a demo video in place of a live
system — the brief is explicit that a working call is the only thing that
counts.
