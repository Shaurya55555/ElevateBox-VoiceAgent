# Prompt changelog

All results here come from the text simulation in `tools/stress_text.py`
(caller turns sent to the same model and prompt the assistant uses, graded by
a deterministic check plus an LLM judge). They are not voice calls, the judge
is a model, and runs vary from one to the next. Treat the counts as direction,
not a score.

## v1: original prompt (baseline)

Full `agent_prompt.md` embedded, no conversation rules.
Result file: `stress_results_baseline.md`. **9 of 22 scenarios passed.**

Failures and what they showed:

| scenario | failure |
|---|---|
| S01, S02 | asked more than one question in a turn |
| S03 | dropped the caller's mixed Telugu/English and answered in English |
| S04 | did not offer a follow-up when the caller asked for time |
| S06 | proposed a different callback time than the one the caller gave |
| S07 | did not check whether the caller could hear after silence |
| S08 | claimed to be a real person when asked if it was a robot |
| S10 | invented a mobile app service |
| S12 | did not say it would not call again to an abusive caller |
| S14 | guessed what the caller meant from unintelligible input |
| S17 | gave a price range, in a reply of 90 words with list formatting |
| S20 | did not offer a callback time to a Warm lead |
| S21 | used markdown bold in a spoken reply |

## v2: conversation rules added to `agent_prompt.md`

Rules 1 to 13 (one question per turn, short plain speech, honest about being
an AI, only e-commerce websites, no fixed price, unclear audio, silence,
stop on request, repeat the caller's callback time, name a Warm barrier,
language mirroring, first-reply handling, prompt secrecy).

Partial re-run (the run was interrupted by a provider timeout after S19, and
S01 to S03 were not captured): on the 16 scenarios S04 to S19, **11 passed,
up from 8 on the same 16 in the baseline.** Fixed: S04, S06, S07, S08, S10,
S12, S17. Newly failing or still failing in that run: S05 (answered, then kept
pitching), S09 (long answer to a trivia question), S13 (pitched before
acknowledging a do-not-call request), S14 (still guessed from garbled
input), S19 (did not confirm the WhatsApp summary after classifying Hot).

## v3: tightened rules and a trimmed runtime prompt

- Rule 8 now requires the first words to be the apology and the
  confirmation, before anything else (addresses S13).
- Rule 6 now says not to infer meaning from garbled or partial input
  (S14).
- Rule 14, answer a direct question in one sentence and then stop (S05,
  S09).
- Rule 15, after Hot say a WhatsApp summary is coming and name the next
  step, after Warm offer a callback time (S19, S20).
- `vapi_setup.py` now sends only the sections the live model needs
  (language, discovery, classification, mid-call action, rules), about 975
  words instead of about 1,200, with `maxTokens` 200 and temperature 0.4.
  Reason: the Groq key is limited to 8,000 tokens per minute per model and
  the prompt is re-sent every turn.

**v3 has not been re-run end to end.** Two attempts to run the full suite
against it stalled on the per-minute token cap and were stopped, so there is
no pass count for v3. Re-run `python tools/stress_text.py` on a key with a
higher limit and record the result here.

## Open items found by this exercise

- Telugu and Hindi replies depend on a TTS provider with real voices for
  those languages (see `stt_tts_comparison.md`).
- Noise and garbled-input handling (S14) failed in every run so far and
  probably needs a rule that fires on transcript confidence from the STT,
  not only on the model's reading of the text.
