# ElevateBox SDE Intern Assignment

Built for ElevateBox's (ElevateScale Technologies) SDE Intern hiring
assignment: an AI voice agent that calls **8688664337** on its own, sells
e-commerce website development in Telugu/Hindi/English, classifies the lead
Hot/Warm/Cold in real time, fires a WhatsApp mid-call on high intent, books
callbacks from spoken time, and sends a post-call WhatsApp with real
conversation context, a resume, a phone number, and an architecture image.
No deck, no proposal — a working system, per their brief.

## Stack — fully free, no purchase required anywhere

Third build. Two earlier attempts are kept for reference and to explain the
path here:

- `omnidimension_reference/` — bundled telephony+STT+LLM+TTS, live-verified
  against a real API key, abandoned because it required buying a phone
  number ($5.06/month) with no free option.
- `google_twilio_reference/` — hand-rolled Twilio Media Streams + Google
  Cloud STT/TTS + Gemini. Abandoned because Twilio's free trial can only
  call numbers *you* verify by receiving an SMS/voice code on that exact
  number — 8688664337 belongs to ElevateBox, not Shaurya, so there's no way
  to receive that code without paying to lift the trial restriction.

Current stack, chosen specifically because every piece is free (not just a
trial credit) or gated on something other than payment:

- **Exotel** (telephony) — trial restriction is **KYC** (identity document
  verification), not destination-number verification. Once approved, it
  can call any number, including 8688664337, using ₹1000 free trial credit.
- **Vapi** (orchestration) — $10 free credit, no card required at signup.
  Handles the two hardest engineering problems named in the brief: low-
  latency turn-taking with interruption handling, and mid-call tool calls
  without blocking the audio stream. Configured in BYOK mode so it uses our
  own Deepgram/Groq/Gemini keys and Exotel telephony rather than billing
  through Vapi's own default providers.
- **Deepgram** (STT: Nova-3, TTS: Aura-2) — $200 free credit, no card,
  never expires. Nova-3 handles Hindi/Telugu/English and code-switching in
  `language=multi` mode.
- **Groq** (fast in-conversation LLM turns) — free, no card, used for the
  live back-and-forth where latency matters most.
- **Gemini API** (extraction/classification) — free tier, no card, used
  between turns for the heavier structured work (budget/timeline/features
  extraction, Hot/Warm/Cold classification) via `decision_engine.py`.
- **Meta WhatsApp Cloud API** — free for service messages within the
  24-hour window opened by the call; used for both the mid-call Hot-lead
  alert and the post-call follow-up.
- **FastAPI** (`app.py`) — receives Vapi's tool-call and end-of-call
  webhooks; this is where classification, WhatsApp sends, and scheduling
  actually happen.
- **SQLite** (`scheduler.py`) — one table for booked callbacks.

**Honesty check on verification status:** none of this has been run
end-to-end yet — no Vapi/Exotel/Deepgram/Groq/Gemini/Meta credentials exist
yet (accounts are being created in parallel; Exotel needs KYC approval,
1-2 business days). Vapi's exact server-webhook payload shape in
`app.py`/`vapi_setup.py` is written from documented spec, not verified
against a live call — check it against a real webhook payload during step 2
of the build order below before trusting it.

## Setup — what only you (Shaurya) can do (account creation, KYC, payment info)

1. **Exotel** — sign up at exotel.com (free, instant). Submit KYC (PAN
   card is normally enough for an individual account) as early as possible
   — it's the longest lead time in this stack. → `EXOTEL_SID`,
   `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_EXOPHONE` (from Numbers →
   Exophones once approved).
2. **Vapi** — sign up at vapi.ai (free, no card for the $10 credit). Get an
   API key from the dashboard → `VAPI_API_KEY`.
3. **Deepgram** — sign up at deepgram.com/console (free, no card). Get an
   API key → `DEEPGRAM_API_KEY`.
4. **Groq** — sign up at console.groq.com (free, no card) → `GROQ_API_KEY`.
5. **Gemini** — https://aistudio.google.com/apikey (free, no card) →
   `GEMINI_API_KEY`.
6. **Meta WhatsApp Business API** — Meta Business account + WhatsApp
   Business API app at developers.facebook.com. API Setup page gives a test
   number + Phone Number ID + temporary access token. Add the interim test
   number (+91-7985200306) as a verified test recipient there, later add
   8688664337 → `META_WA_PHONE_NUMBER_ID`, `META_WA_ACCESS_TOKEN`.
7. **ngrok** (or any HTTPS tunnel) — `ngrok http 8000` once `app.py` is
   running → `WEBHOOK_BASE_URL`.

## Run order

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in every value as accounts come online

# 1. Start the backend that Vapi's webhooks hit
uvicorn app:app --host 0.0.0.0 --port 8000

# 2. Tunnel it, put the forwarding URL in .env as WEBHOOK_BASE_URL
ngrok http 8000

# 3. Create/update the Vapi assistant (rerun after editing agent_prompt.md
#    or the tool definitions in vapi_setup.py)
python vapi_setup.py
# copy the printed assistant id into .env as VAPI_ASSISTANT_ID

# 4. Place a call — defaults to the interim test number
#    (+91-7985200306) while Exotel KYC is pending; pass 8688664337
#    explicitly once Exotel is approved and VAPI_PHONE_NUMBER_ID is set
#    to the Exotel-backed Vapi number
python dispatch_call.py
python dispatch_call.py +918688664337
```

## Files

- `agent_prompt.md` — the conversational design in full prose (source of
  truth for the system prompt built in `vapi_setup.py`): welcome message,
  discovery questions, Hot/Warm/Cold classification logic, WhatsApp message
  templates.
- `vapi_setup.py` — creates/updates the Vapi assistant via API: model
  (Groq), voice (Deepgram Aura-2), transcriber (Deepgram Nova-3, multi-
  language), tool definitions (`extract_and_classify`, `schedule_callback`),
  `serverUrl` pointing at `app.py`.
- `app.py` — FastAPI server handling Vapi's webhooks: `tool-calls` (runs
  classification, fires the mid-call WhatsApp) and `end-of-call-report`
  (composes and sends the post-call WhatsApp).
- `decision_engine.py` — Gemini-based extraction/classification
  (`classify`) and spoken-time parsing (`parse_callback_time`).
- `scheduler.py` — SQLite-backed callback table.
- `dispatch_call.py` — triggers an outbound call via the Vapi API.
- `whatsapp.py` — thin Meta Cloud API client (text/document/image sends).
- `architecture.md` — text spec for the required architecture diagram;
  export/draw it as `architecture.png` once the flow is confirmed working,
  and point `ARCHITECTURE_IMAGE_URL` at its raw GitHub URL.
- `resume.pdf` — Shaurya's resume, sent as a WhatsApp document attachment
  via its raw GitHub URL (`RESUME_PUBLIC_URL`).
- `omnidimension_reference/`, `google_twilio_reference/` — the two earlier
  abandoned builds, kept for reference (see their own READMEs for why).

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
