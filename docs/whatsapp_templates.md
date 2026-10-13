# WhatsApp message templates (submit in Meta Business Manager)

Free-form messages only deliver inside the 24-hour window that opens when
the recipient messages the business number. A phone call does not open that
window, so a follow-up to someone who has not messaged you first must be a
**template approved by Meta**. `whatsapp.send_text_or_template()` tries
free-form text first and falls back to the template when Meta answers with
error 131047.

Create these in WhatsApp Manager, Message templates, category **Utility**,
language **English**. Approval is by Meta and is not instant.

## 1. `post_call_followup` (used by app.py)

Body:

```
Hi, this is Shaurya's team following up on our call. Noted: {{1}}. You can reach Shaurya directly on {{2}}. Thanks for your time.
```

Parameters:

| var | filled with | example |
|---|---|---|
| `{{1}}` | what the caller told us (product type, timeline) | handmade candles, next month |
| `{{2}}` | Shaurya's number | +91-7985200306 |

Sample values to give Meta at submission: `{{1}}` = "handmade candles, launch next month", `{{2}}` = "+91-7985200306".

The env var `WA_TEMPLATE_FOLLOWUP` sets the template name (default
`post_call_followup`). Parameter order is set in
`messages.template_params_followup()`; keep them in sync.

## 2. `callback_confirmation` (for booked callbacks)

Body:

```
Hi, confirming your callback with Shaurya's team on {{1}}. Reply here if you would like a different time.
```

| var | filled with | example |
|---|---|---|
| `{{1}}` | the parsed callback time in plain language | tomorrow at 11:00 AM |

This template is defined here but not yet sent by the backend; wiring it is
a small change in `_run_schedule_callback` once the template is approved.

## Notes

- Templates cannot contain the resume PDF or architecture image unless you
  add a media header. The backend sends those as free-form attachments,
  which deliver only if a window is open. Outside a window the caller gets
  the template text only.
- Until the templates are approved and a message has been seen arriving on a
  phone outside an open window, do not claim approved-template delivery.
