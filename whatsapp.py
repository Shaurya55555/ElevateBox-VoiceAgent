"""
Meta WhatsApp Cloud API sender. Requires a Meta Business + WhatsApp Business
API app with a verified sending number (developers.facebook.com), inside the
24-hour customer-service window opened by the inbound call to the lead's
number (see Meta's messaging docs — service messages don't need template
pre-approval as long as that window is open).
"""

import os

import requests

GRAPH_VERSION = "v20.0"


def _base_url():
    phone_number_id = os.environ["META_WA_PHONE_NUMBER_ID"]
    return f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_number_id}/messages"


def _headers():
    token = os.environ["META_WA_ACCESS_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def send_text(to_number: str, body: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number.lstrip("+"),
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }
    resp = requests.post(_base_url(), headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_document(to_number: str, link: str, filename: str, caption: str = "") -> dict:
    """Send a document (e.g. resume PDF) by public URL. Meta fetches the file itself."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number.lstrip("+"),
        "type": "document",
        "document": {"link": link, "filename": filename, "caption": caption},
    }
    resp = requests.post(_base_url(), headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_image(to_number: str, link: str, caption: str = "") -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number.lstrip("+"),
        "type": "image",
        "image": {"link": link, "caption": caption},
    }
    resp = requests.post(_base_url(), headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()
