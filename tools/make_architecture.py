"""Render architecture.png from the flow described in architecture.md.

Usage: python tools/make_architecture.py
Needs matplotlib. Output: architecture.png in the repo root.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "architecture.png"

BLUE, GREEN, AMBER, GREY = "#dbeafe", "#dcfce7", "#fef3c7", "#f1f5f9"


def box(ax, x, y, w, h, text, color, size=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                linewidth=1.2, edgecolor="#334155", facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            color="#0f172a", wrap=True)


def arrow(ax, x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color="#334155", lw=1.4))
    if label:
        ax.text((x1 + x2) / 2 + 0.08, (y1 + y2) / 2, label, fontsize=8, color="#475569",
                ha="left", va="center")


def main() -> None:
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis("off")
    ax.text(6.5, 8.65, "ElevateBox voice sales agent: architecture", ha="center",
            fontsize=15, fontweight="bold", color="#0f172a")

    box(ax, 0.3, 7.2, 3.2, 0.9, "dispatch_call.py\nPOST /call to Vapi API", GREY)
    box(ax, 4.6, 7.2, 3.6, 0.9, "Vapi\ncall orchestration, turn-taking,\ninterruption handling", BLUE)
    box(ax, 9.3, 7.2, 3.4, 0.9, "Exotel\nIndian telephony (PSTN)", BLUE)
    arrow(ax, 3.5, 7.65, 4.6, 7.65)
    arrow(ax, 8.2, 7.65, 9.3, 7.65)

    box(ax, 0.3, 5.5, 3.6, 0.95, "Deepgram Nova-3 STT\nHindi / Telugu / English\nlanguage=multi", GREEN)
    box(ax, 4.7, 5.5, 3.6, 0.95, "Groq llama-3.3-70b\nlive turn replies\nprompt from agent_prompt.md", GREEN)
    box(ax, 9.1, 5.5, 3.6, 0.95, "Deepgram Aura-2 TTS\nspoken reply", GREEN)
    arrow(ax, 6.4, 7.2, 2.1, 6.45, "caller audio")
    arrow(ax, 3.9, 5.97, 4.7, 5.97)
    arrow(ax, 8.3, 5.97, 9.1, 5.97)
    arrow(ax, 10.9, 6.45, 7.6, 7.2, "reply audio")

    box(ax, 4.2, 3.8, 4.6, 0.95, "FastAPI backend (app.py), Render\n/vapi/webhook: tool-calls,\nend-of-call-report", AMBER)
    arrow(ax, 6.5, 5.5, 6.5, 4.75, "tool call mid-conversation")

    box(ax, 0.3, 2.0, 3.6, 0.95, "decision_engine.py\nGemini 2.5 Flash\nfacts + Hot / Warm / Cold", AMBER)
    box(ax, 4.7, 2.0, 3.6, 0.95, "whatsapp.py\nMeta Cloud API\ntext, template fallback,\nresume, image", AMBER)
    box(ax, 9.1, 2.0, 3.6, 0.95, "scheduler.py\ncallbacks + idempotency keys\nSQLite / Postgres", AMBER)
    arrow(ax, 5.3, 3.8, 2.1, 2.95)
    arrow(ax, 6.5, 3.8, 6.5, 2.95)
    arrow(ax, 7.7, 3.8, 10.9, 2.95)

    ax.text(2.1, 1.65, "Hot / Warm / Cold", ha="center", fontsize=8, color="#475569")
    ax.text(5.55, 1.65, "Hot: WhatsApp now", ha="center", fontsize=8, color="#475569")
    ax.text(10.9, 1.65, "Warm: spoken time parsed, stored", ha="center", fontsize=8, color="#475569")

    box(ax, 4.7, 0.35, 3.6, 0.8, "Caller's WhatsApp", GREY)
    arrow(ax, 6.5, 2.0, 6.5, 1.15)

    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
