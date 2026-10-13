"""STT and TTS comparison harness.

STT:  python tools/stt_tts_compare.py stt
      Reads docs/stt_samples/manifest.json, a list of
      {"file": "hi_01.wav", "lang": "hi", "reference": "<what was said>",
       "speaker": "<who>", "kind": "human" | "synthetic"}
      with the audio files beside it. Transcribes each file with
      Deepgram Nova-3 and Groq whisper-large-v3, computes word error rate
      against the reference, and writes docs/stt_tts_comparison.md.

TTS:  python tools/stt_tts_compare.py tts
      Sends one sentence per language to each Deepgram Aura-2 voice and
      records whether the API accepted it, saving wav files under
      docs/tts_samples/ (gitignored). Naturalness is scored by a human
      listening, on a 1 to 5 rubric, in the table the script prints.

Word error rate here is a plain word-level edit distance after lowercasing
and stripping punctuation. Samples recorded by a person are the only ones
that say anything about dialect accuracy. TTS-generated "synthetic" audio
only proves the pipeline runs and is labelled as such in the report.
"""

import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SAMPLES = ROOT / "docs" / "stt_samples"
TTS_OUT = ROOT / "docs" / "tts_samples"

DEEPGRAM_LANG = {"en": "en", "hi": "hi", "te": "multi", "hinglish": "multi", "te-en": "multi"}
WHISPER_LANG = {"en": "en", "hi": "hi", "te": "te", "hinglish": "hi", "te-en": "te"}

TTS_VOICES = ["aura-2-luna-en", "aura-2-thalia-en", "aura-2-andromeda-en", "aura-2-helena-en"]
TTS_SENTENCES = {
    "en": "Hi, this is Ananya calling on behalf of Shaurya. Is this a good time?",
    "hi": "नमस्ते, मैं शौर्य की तरफ से अनन्या बोल रही हूँ। क्या अभी बात करने का सही समय है?",
    "te": "నమస్తే, నేను శౌర్య తరపున అనన్య మాట్లాడుతున్నాను. ఇప్పుడు మాట్లాడటానికి వీలవుతుందా?",
}


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text.lower())
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def deepgram_stt(path: Path, lang: str) -> str:
    resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-3", "language": DEEPGRAM_LANG.get(lang, "multi"),
                "smart_format": "true"},
        headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}",
                 "Content-Type": "audio/wav"},
        data=path.read_bytes(), timeout=120)
    resp.raise_for_status()
    alt = resp.json()["results"]["channels"][0]["alternatives"][0]
    return alt.get("transcript", "")


def whisper_stt(path: Path, lang: str) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        data={"model": "whisper-large-v3", "language": WHISPER_LANG.get(lang, "en"),
              "response_format": "json", "temperature": "0"},
        files={"file": (path.name, path.read_bytes(), "audio/wav")}, timeout=120)
    resp.raise_for_status()
    return resp.json().get("text", "")


def run_stt() -> None:
    manifest_path = SAMPLES / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"No {manifest_path}. Record samples and list them there first "
                 "(see this file's docstring).")
    items = json.loads(manifest_path.read_text(encoding="utf-8"))
    engines = {"Deepgram Nova-3": deepgram_stt, "Groq Whisper large-v3": whisper_stt}
    rows = []
    for item in items:
        path = SAMPLES / item["file"]
        row = {**item, "results": {}}
        for name, fn in engines.items():
            try:
                hyp = fn(path, item["lang"])
                row["results"][name] = {"text": hyp, "wer": wer(item["reference"], hyp)}
            except Exception as exc:  # noqa: BLE001
                row["results"][name] = {"text": f"ERROR {str(exc)[:80]}", "wer": None}
        rows.append(row)
        print(item["file"], {k: (None if v["wer"] is None else round(v["wer"], 2))
                             for k, v in row["results"].items()})

    lines = ["# STT comparison", "",
             f"Run date: {date.today().isoformat()}. Engines: " + ", ".join(engines) + ".", "",
             "WER is a word-level edit distance against the reference sentence, lower is better. "
             "`kind` says whether a person recorded the sample or it is TTS-generated audio. "
             "Only `human` rows say anything about dialect and accent handling.", ""]
    summary = {}
    for kind in ("human", "synthetic"):
        for lang in sorted({r["lang"] for r in rows}):
            subset = [r for r in rows if r.get("kind") == kind and r["lang"] == lang]
            for name in engines:
                vals = [r["results"][name]["wer"] for r in subset
                        if r["results"][name]["wer"] is not None]
                if vals:
                    summary[(kind, lang, name)] = (sum(vals) / len(vals), len(vals))
    lines += ["## Mean WER by language", "", "| kind | lang | engine | mean WER | samples |",
              "|---|---|---|---|---|"]
    for (kind, lang, name), (mean, n) in sorted(summary.items()):
        lines.append(f"| {kind} | {lang} | {name} | {mean:.2f} | {n} |")
    lines += ["", "## Samples", "", "| file | lang | kind | reference | engine | hypothesis | WER |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        for name, res in r["results"].items():
            w = "n/a" if res["wer"] is None else f"{res['wer']:.2f}"
            lines.append(f"| {r['file']} | {r['lang']} | {r.get('kind', '')} | {r['reference']} | "
                         f"{name} | {res['text']} | {w} |")
    lines += ["", "## Robotic pauses and mispronunciations (TTS)", "",
              "Filled in by a human listener; see the TTS table.", ""]
    (ROOT / "docs" / "stt_tts_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote docs/stt_tts_comparison.md")


def run_tts() -> None:
    TTS_OUT.mkdir(parents=True, exist_ok=True)
    print("| voice | lang | API result | file | naturalness 1-5 (human) | robotic pauses / mispronunciations |")
    print("|---|---|---|---|---|---|")
    for voice in TTS_VOICES:
        for lang, sentence in TTS_SENTENCES.items():
            resp = requests.post(
                "https://api.deepgram.com/v1/speak",
                params={"model": voice, "encoding": "linear16", "container": "wav"},
                headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}",
                         "Content-Type": "application/json"},
                json={"text": sentence}, timeout=60)
            if resp.ok:
                path = TTS_OUT / f"{voice}_{lang}.wav"
                path.write_bytes(resp.content)
                print(f"| {voice} | {lang} | ok ({len(resp.content)} bytes) | {path.name} |  |  |")
            else:
                print(f"| {voice} | {lang} | rejected {resp.status_code}: "
                      f"{resp.text[:60].replace('|', '/')} |  |  |  |")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("stt", "tts"):
        sys.exit("usage: python tools/stt_tts_compare.py stt|tts")
    run_stt() if sys.argv[1] == "stt" else run_tts()
