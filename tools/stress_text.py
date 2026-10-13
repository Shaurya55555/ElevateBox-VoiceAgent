"""Text-mode stress test of the agent prompt against docs/stress_scenarios.json.

What this is: each scenario's caller turns are sent, in order, to the same
model and system prompt the Vapi assistant uses (Groq llama-3.3-70b with the
prompt and tools built in vapi_setup.py). Replies and tool calls are logged
and graded by deterministic checks (phone brevity, no markdown) and an LLM
judge against a per-scenario expectation.

What this is NOT: a voice test. There is no speech recognition, no TTS, no
interruption timing and no telephony here. It tests the prompt's behaviour
on text, and the LLM judge is a model, not a human.

Usage:
    python tools/stress_text.py                 # run all, write docs/stress_results.md
    python tools/stress_text.py S05 S12         # run selected scenarios
"""

import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import vapi_setup  # noqa: E402  (builds SYSTEM_PROMPT and TOOLS; no network at import)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = vapi_setup.ASSISTANT_CONFIG["model"]["model"]
MAX_REPLY_WORDS = 60
MARKDOWN = re.compile(r"(\*\*|^#|^\s*[-*] |`)", re.M)


def groq(messages, tools=None, model=MODEL, temperature=0.4):
    body = {"model": model, "messages": messages, "temperature": temperature}
    if tools:
        body["tools"] = tools
    for attempt in range(8):
        try:
            resp = requests.post(
                GROQ_URL, timeout=60,
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                json=body)
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
            continue
        if resp.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]
    raise RuntimeError("Groq request failed after retries")


def run_conversation(scenario, system_prompt):
    messages = [{"role": "system", "content": system_prompt},
                {"role": "assistant", "content": vapi_setup.ASSISTANT_CONFIG["firstMessage"]}]
    transcript, tool_calls = [], []
    for caller_turn in scenario["turns"]:
        messages.append({"role": "user", "content": caller_turn})
        transcript.append(("Caller", caller_turn))
        msg = groq(messages, vapi_setup.TOOLS)
        if msg.get("tool_calls"):
            messages.append(msg)
            for tc in msg["tool_calls"]:
                tool_calls.append({"name": tc["function"]["name"],
                                   "arguments": tc["function"]["arguments"]})
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": json.dumps({"classification": "ok",
                                                        "confirmed_datetime": "tomorrow 11:00"})})
            msg = groq(messages, vapi_setup.TOOLS)
        reply = (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": reply})
        transcript.append(("Agent", reply))
    return transcript, tool_calls


def deterministic_checks(transcript):
    failures = []
    for speaker, text in transcript:
        if speaker != "Agent":
            continue
        if not text:
            failures.append("empty reply")
        if len(text.split()) > MAX_REPLY_WORDS:
            failures.append(f"reply over {MAX_REPLY_WORDS} words ({len(text.split())})")
        if MARKDOWN.search(text):
            failures.append("markdown/list formatting in a spoken reply")
    return failures


JUDGE_PROMPT = """You are grading an AI phone sales agent. Below is a short text
conversation (the agent speaks on a phone call), the tool calls the agent made,
and what a good agent should do in this scenario.

Expectation: {expect}

Conversation:
{transcript}

Tool calls made: {tools}

Did the agent meet the expectation? Be strict. Respond ONLY with JSON:
{{"pass": true | false, "reason": "<one short sentence>"}}"""


def judge(scenario, transcript, tool_calls):
    text = "\n".join(f"{s}: {t}" for s, t in transcript)
    prompt = JUDGE_PROMPT.format(expect=scenario["expect"], transcript=text,
                                 tools=json.dumps(tool_calls) if tool_calls else "none")
    msg = groq([{"role": "user", "content": prompt}], temperature=0)
    raw = msg["content"].strip()
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def main(selected):
    scenarios = json.loads((ROOT / "docs" / "stress_scenarios.json").read_text(encoding="utf-8"))
    if selected:
        scenarios = [s for s in scenarios if s["id"] in selected]
    results = []
    for sc in scenarios:
        try:
            transcript, tool_calls = run_conversation(sc, vapi_setup.SYSTEM_PROMPT)
            det = deterministic_checks(transcript)
            verdict = judge(sc, transcript, tool_calls)
        except Exception as exc:  # noqa: BLE001 - record and keep going
            print(f"{sc['id']} ERROR {exc}", flush=True)
            results.append({"scenario": sc, "transcript": [], "tool_calls": [],
                            "pass": False, "reason": f"harness error: {str(exc)[:80]}"})
            continue
        passed = bool(verdict.get("pass")) and not det
        reason = verdict.get("reason", "")
        if det:
            reason = "; ".join(det) + ("; judge: " + reason if reason else "")
        results.append({"scenario": sc, "transcript": transcript, "tool_calls": tool_calls,
                        "pass": passed, "reason": reason})
        print(f"{sc['id']} {sc['category']}: {'PASS' if passed else 'FAIL'} - {reason}", flush=True)
        time.sleep(3)

    out = ROOT / "docs" / ("stress_results.md" if not selected else "stress_results_partial.md")
    lines = [
        "# Stress test results (text simulation)",
        "",
        f"Run date: {date.today().isoformat()}. Agent model: `{MODEL}` on Groq, with the system "
        "prompt and tools built in `vapi_setup.py`. Grader: the same model as an LLM judge, plus "
        f"deterministic checks (replies of at most {MAX_REPLY_WORDS} words, no markdown).",
        "",
        "**Scope.** This is a text simulation of caller turns, not a voice test. It does not "
        "exercise speech recognition, TTS, interruption timing or telephony, and the judge is a "
        "model, not a human. Treat it as a prompt regression test. Voice behaviour is verified "
        "separately in `docs/test_calls/`.",
        "",
        f"**Passed {sum(r['pass'] for r in results)} of {len(results)}.**",
        "",
        "| id | category | result | note |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['scenario']['id']} | {r['scenario']['category']} | "
                     f"{'pass' if r['pass'] else 'FAIL'} | {r['reason'].replace('|', '/')} |")
    lines += ["", "## Transcripts", ""]
    for r in results:
        lines.append(f"### {r['scenario']['id']} ({r['scenario']['category']}): "
                     f"{'pass' if r['pass'] else 'FAIL'}")
        lines.append(f"Expectation: {r['scenario']['expect']}")
        lines.append("")
        for speaker, text in r["transcript"]:
            lines.append(f"- **{speaker}:** {text}")
        if r["tool_calls"]:
            lines.append(f"- Tool calls: `{json.dumps(r['tool_calls'], ensure_ascii=False)}`")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
