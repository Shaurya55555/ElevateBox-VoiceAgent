"""WhatsApp message composition. Pure functions, no I/O, easy to test."""


def midcall_message(facts: dict, phone_display: str) -> str:
    parts = ["Hey! Great talking just now, quick summary while it's fresh:"]
    if facts.get("product_type"):
        parts.append(f"- Building for: {facts['product_type']}")
    if facts.get("product_count"):
        parts.append(f"- Catalog size: {facts['product_count']}")
    if facts.get("budget"):
        parts.append(f"- Budget: {facts['budget']}")
    if facts.get("timeline"):
        parts.append(f"- Timeline: {facts['timeline']}")
    parts.append(f"\nReach me directly anytime: {phone_display}")
    return "\n".join(parts)


def postcall_message(facts: dict, phone_display: str) -> str:
    lines = ["Hey! This is Shaurya's team following up after our call."]
    bits = []
    if facts.get("product_type"):
        bits.append(f"building {facts['product_type']}")
    if facts.get("product_count"):
        bits.append(f"around {facts['product_count']} products")
    if facts.get("budget"):
        bits.append(f"budget-wise thinking {facts['budget']}")
    if facts.get("timeline"):
        bits.append(f"hoping to launch {facts['timeline']}")
    if bits:
        lines.append("Sounds like you're " + ", ".join(bits) + ".")
    if facts.get("barrier"):
        lines.append(f"Totally understand on {facts['barrier']}, no rush.")
    if facts.get("callback_time"):
        lines.append(f"I'll call you back {facts['callback_time']}.")
    lines.append(f"\nFeel free to reach me directly on {phone_display}.")
    lines.append("Attaching my resume and a quick look at how this system was built.")
    return "\n".join(lines)


def template_params_followup(facts: dict, phone_display: str) -> list[str]:
    """Body parameters for the `post_call_followup` template (see
    docs/whatsapp_templates.md). Keep in sync with the template text."""
    summary_bits = [
        facts.get("product_type") or "your online store",
        facts.get("timeline") or "no fixed timeline yet",
    ]
    return [", ".join(summary_bits), phone_display]
