"""Run decision_engine.classify() over the hand-labelled set and report the match rate.

Usage: python tools/classification_eval.py
Needs GEMINI_API_KEY. Writes docs/classification_eval.md.

The labelled transcripts in docs/classification_set.json are SYNTHETIC
(written to cover Hot/Warm/Cold in English, Hindi, Hinglish, Telugu-English
and a few borderline cases). They are not recordings of real calls, so the
match rate shows how the classifier handles these cases, not a production
accuracy figure.
"""

import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import decision_engine  # noqa: E402

LABELS = ["Hot", "Warm", "Cold"]


def main() -> None:
    items = json.loads((ROOT / "docs" / "classification_set.json").read_text(encoding="utf-8"))
    rows = []
    for item in items:
        predicted, error = None, ""
        for attempt in range(4):
            try:
                predicted = decision_engine.classify(item["transcript"])["classification"]
                break
            except Exception as exc:  # noqa: BLE001
                error = str(exc)[:120]
                time.sleep(20 * (attempt + 1))  # free-tier 429s are per-minute
        time.sleep(5)  # stay under the free-tier request rate
        rows.append({**item, "predicted": predicted or "ERROR", "error": error})
        print(item["id"], item["label"], "->", predicted or f"ERROR {error}")

    scored = [r for r in rows if r["predicted"] != "ERROR"]
    correct = sum(r["predicted"] == r["label"] for r in scored)
    confusion = Counter((r["label"], r["predicted"]) for r in scored)

    lines = [
        "# Classification evaluation",
        "",
        f"Run date: {date.today().isoformat()}. Model: gemini-2.5-flash via `decision_engine.classify()`.",
        "",
        "**Scope and caveat.** The transcripts in `classification_set.json` are synthetic, "
        "written by hand to cover Hot, Warm and Cold across English, Hindi, Hinglish and "
        "Telugu-English, plus borderline cases. Labels were assigned by the author from the "
        "rules in `agent_prompt.md`. This is not a measurement on real calls.",
        "",
        f"**Match rate: {correct}/{len(scored)}**"
        + (f" ({len(rows) - len(scored)} errored and are excluded)" if len(scored) != len(rows) else ""),
        "",
        "## Confusion (rows = hand label, columns = predicted)",
        "",
        "| label \\ predicted | " + " | ".join(LABELS) + " |",
        "|---|" + "---|" * len(LABELS),
    ]
    for actual in LABELS:
        lines.append(f"| {actual} | " + " | ".join(str(confusion[(actual, p)]) for p in LABELS) + " |")
    misses = [r for r in scored if r["predicted"] != r["label"]]
    lines += ["", "## Mismatches", ""]
    if not misses:
        lines.append("None.")
    for r in misses:
        lines.append(f"- `{r['id']}` ({r['lang']}): labelled {r['label']}, predicted {r['predicted']}. "
                     f"Transcript: {r['transcript'].splitlines()[-1][:160]}")
    lines += ["", "## All cases", "", "| id | lang | label | predicted |", "|---|---|---|---|"]
    for r in rows:
        mark = "" if r["predicted"] == r["label"] else " (mismatch)"
        lines.append(f"| {r['id']} | {r['lang']} | {r['label']} | {r['predicted']}{mark} |")
    (ROOT / "docs" / "classification_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nmatch rate {correct}/{len(scored)}")


if __name__ == "__main__":
    main()
