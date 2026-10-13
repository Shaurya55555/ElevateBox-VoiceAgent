# Classification evaluation

Run date: 2026-10-13. Model: gemini-2.5-flash via `decision_engine.classify()`.

**Scope and caveat.** The transcripts in `classification_set.json` are synthetic, written by hand to cover Hot, Warm and Cold across English, Hindi, Hinglish and Telugu-English, plus borderline cases. Labels were assigned by the author from the rules in `agent_prompt.md`. This is not a measurement on real calls.

**Match rate: 19/19** (6 errored and are excluded)

## Confusion (rows = hand label, columns = predicted)

| label \ predicted | Hot | Warm | Cold |
|---|---|---|---|
| Hot | 7 | 0 | 0 |
| Warm | 0 | 6 | 0 |
| Cold | 0 | 0 | 6 |

## Mismatches

None.

## All cases

| id | lang | label | predicted |
|---|---|---|---|
| h1 | en | Hot | Hot |
| h2 | en | Hot | Hot |
| h3 | hinglish | Hot | Hot |
| h4 | hinglish | Hot | Hot |
| h5 | te-en | Hot | Hot |
| h6 | en | Hot | Hot |
| h7 | hi | Hot | ERROR (mismatch) |
| w1 | en | Warm | ERROR (mismatch) |
| w2 | en | Warm | ERROR (mismatch) |
| w3 | hinglish | Warm | Warm |
| w4 | hinglish | Warm | Warm |
| w5 | te-en | Warm | Warm |
| w6 | en | Warm | Warm |
| w7 | en | Warm | Warm |
| w8 | hi | Warm | Warm |
| c1 | en | Cold | Cold |
| c2 | en | Cold | ERROR (mismatch) |
| c3 | hinglish | Cold | Cold |
| c4 | hinglish | Cold | Cold |
| c5 | te-en | Cold | Cold |
| c6 | en | Cold | Cold |
| c7 | en | Cold | Cold |
| m1 | en | Hot | Hot |
| m2 | en | Warm | ERROR (mismatch) |
| m3 | en | Cold | ERROR (mismatch) |
