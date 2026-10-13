"""Save everything about a Vapi call into docs/test_calls/<call_id>/.

Usage: python tools/fetch_call.py <call_id> [--label "Hindi hot lead"]

Saves call.json (full record), transcript.txt, recording.<ext> (if Vapi
kept one), and a summary.md with the fields the README links to: status,
duration, end reason, the tool calls and their results, and the cost.
Run it after each real test call, then add the WhatsApp delivery result by
hand in summary.md (Meta shows delivery status in the dashboard).
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("call_id")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    resp = requests.get(f"https://api.vapi.ai/call/{args.call_id}", timeout=30,
                        headers={"Authorization": f"Bearer {os.environ['VAPI_API_KEY']}"})
    if not resp.ok:
        sys.exit(f"Vapi returned {resp.status_code}: {resp.text[:300]}")
    call = resp.json()

    out = ROOT / "docs" / "test_calls" / args.call_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "call.json").write_text(json.dumps(call, indent=2, ensure_ascii=False), encoding="utf-8")

    artifact = call.get("artifact") or {}
    transcript = artifact.get("transcript") or call.get("transcript") or ""
    (out / "transcript.txt").write_text(transcript, encoding="utf-8")

    recording_note = "not available"
    rec_url = artifact.get("recordingUrl") or call.get("recordingUrl")
    if rec_url:
        audio = requests.get(rec_url, timeout=60)
        if audio.ok:
            ext = Path(rec_url.split("?")[0]).suffix or ".wav"
            (out / f"recording{ext}").write_bytes(audio.content)
            recording_note = f"recording{ext}"

    tool_lines = []
    for msg in artifact.get("messages") or call.get("messages") or []:
        role = msg.get("role")
        if role in ("tool_calls", "tool_call_result", "tool"):
            tool_lines.append(f"- {role}: `{json.dumps(msg, ensure_ascii=False)[:300]}`")

    summary = [
        f"# Test call {args.call_id}",
        "",
        f"- Label: {args.label or '(none)'}",
        f"- Status: {call.get('status')}",
        f"- Started: {call.get('startedAt')}",
        f"- Ended: {call.get('endedAt')}",
        f"- Ended reason: {call.get('endedReason')}",
        f"- Customer: {(call.get('customer') or {}).get('number')}",
        f"- Cost (Vapi): {call.get('cost')}",
        f"- Recording: {recording_note}",
        "",
        "## Tool calls",
        *(tool_lines or ["(none recorded)"]),
        "",
        "## Fill in by hand",
        "",
        "- Classification the agent reached: ",
        "- Mid-call WhatsApp arrived while the call was live (yes/no, time): ",
        "- Post-call WhatsApp arrived (yes/no): ",
        "- Callback booked and time parsed correctly (yes/no/n.a.): ",
        "- Barge-in tested (interrupted the agent mid-sentence, it stopped): ",
        "- Language spoken: ",
        "- Notes / failures: ",
    ]
    (out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"saved to {out}")


if __name__ == "__main__":
    main()
