# ElevateBox SDE Intern Assignment

Built for ElevateBox's (ElevateScale Technologies) SDE Intern hiring
assignment: an AI voice agent that calls **8688664337** on its own, sells
e-commerce website development in Telugu/Hindi/English, classifies the lead
Hot/Warm/Cold in real time, fires a WhatsApp mid-call on high intent, books
callbacks from spoken time, and sends a post-call WhatsApp with real
conversation context, a resume, a phone number, and an architecture image.
No deck, no proposal — a working system, per their brief.

## Stack

- **[OmniDimension](https://omnidim.io)** — telephony + STT + LLM + TTS +
  interruption handling, bundled. Chosen because it natively supports
  Hindi/Telugu/Tamil/Marathi outbound calling — exactly this brief — and
  because ElevateBox's own assignment doc names it as a reference starting
  point. Free tier, no card.
- **Meta WhatsApp Cloud API** — for the mid-call and post-call messages,
  including sending the resume and architecture image as attachments.
  OmniDimension's own "WhatsApp Integration" is for *inbound* WhatsApp
  channels, not for firing rich outbound messages from call events, so
  that step is owned by our own webhook instead.
- **Flask webhook** (`webhook_server.py`) — the bridge: OmniDimension's
  agent calls into this via a "custom API" action mid-call and at call end;
  the webhook then calls the Meta API.

All API calls in `agent_setup.py`, `dispatch_call.py`, and `whatsapp.py` are
written against the **actual installed `omnidimension` SDK source** (read
directly with `inspect.getsource` — not guessed from docs, since the public
docs pages didn't expose the full outbound-call API surface). The real,
confirmed methods used:

- `client.agent.create(name, context_breakdown, **kwargs)` —
  `context_breakdown` is a list of `{"title", "body"}` dicts.
- `client.integrations.create_custom_api_integration(...)` — registers a
  webhook the agent's LLM can call mid-conversation, with
  `isLLMGenerated: true` body params so the agent fills in what it learned.
- `client.integrations.add_integration_to_agent(agent_id, integration_id)`
- `client.call.dispatch_call(agent_id, to_number, from_number_id, call_context)`
  — the single outbound call trigger (there's also `client.bulk_call` for
  campaigns, not needed here).
- `client.phone_number.list()` / `.attach()` — to use a purchased/imported
  number as the caller ID.
- `client.providers.list_voices(...)` / `list_llms()` / `list_stt()` — to
  pick real voice/model/STT provider values instead of inventing IDs.
- `client.simulation.create(...)` — lets you run AI-simulated test calls
  against scenarios *before* burning a real call to 8688664337. Worth using
  first.

## Setup — what only you can do (account creation)

1. **OmniDimension account** — sign up at https://omnidim.io (free, no
   card). Get an API key from https://omnidim.io/api-management.
2. **A phone number to call from** — OmniDimension's dashboard, Phone &
   Telephony section: either acquire a number directly or SIP-trunk one in
   (Twilio/Vonage/Exotel). Not exposed in the installed SDK version, so
   this step is dashboard-only. Once you have one, `client.phone_number.list()`
   gives you its `id` for `from_number_id`.
3. **Meta WhatsApp Business API** — a Meta Business account + WhatsApp
   Business API app at developers.facebook.com, with a verified sending
   number. Gives you `META_WA_PHONE_NUMBER_ID` and `META_WA_ACCESS_TOKEN`.
4. **A public HTTPS URL for `webhook_server.py`** — for local dev, run the
   Flask app and tunnel it with `ngrok http 8000`; for anything more
   permanent, deploy it anywhere (Render, Railway, a small VPS).

## Run order

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in every value

# 1. Start the webhook server, tunnel it, put the public URL in .env as WEBHOOK_BASE_URL
python webhook_server.py
ngrok http 8000

# 2. Create the agent + register the two webhook actions
python agent_setup.py
# -> prints agent_id

# 3. (Recommended) simulate before spending a real call:
#    client.simulation.create(name=..., agent_id=..., scenarios=[...])
#    — run interactively, see OmniDimension dashboard for simulation results.

# 4. Get a from_number_id: client.phone_number.list() (after acquiring one on the dashboard)

# 5. Place the real call
python dispatch_call.py <agent_id> <from_number_id>
```

## Files

- `agent_prompt.md` — the conversational design in full prose (source of
  truth for `CONTEXT_BREAKDOWN` in `agent_setup.py`): welcome message,
  discovery questions, Hot/Warm/Cold classification logic, WhatsApp
  message templates.
- `agent_setup.py` — creates the agent, registers `send_midcall_whatsapp`
  and `send_followup_whatsapp` as custom API integrations, attaches them.
- `dispatch_call.py` — triggers the outbound call to 8688664337.
- `webhook_server.py` — Flask server the agent calls into; sends the actual
  WhatsApp messages (text, resume document, architecture image).
- `whatsapp.py` — thin Meta Cloud API client (text/document/image sends).
- `architecture.md` — text spec for the required architecture diagram;
  export/draw it as `architecture.png` once the flow is confirmed working,
  and point `ARCHITECTURE_IMAGE_URL` at its raw GitHub URL.
- `resume.pdf` — Shaurya's resume, sent as a WhatsApp document attachment
  via its raw GitHub URL (`RESUME_PUBLIC_URL`).

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
