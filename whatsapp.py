"""Meta WhatsApp Cloud API sender.

Free-form messages (text/document/image) only deliver inside the 24-hour
customer-service window. Outside it Meta rejects them (error code 131047),
and only pre-approved templates are allowed. `send_text_or_template` tries
free-form first and falls back to a template, so follow-ups still arrive
after the window has closed. Template names and wording live in
docs/whatsapp_templates.md and must be approved in Meta Business Manager.
"""

import os
import time

import requests

from logging_utils import log_event

GRAPH_VERSION = "v20.0"
REENGAGEMENT_ERROR_CODE = 131047
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class WhatsAppError(Exception):
    def __init__(self, message: str, status: int | None = None, code: int | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


def _base_url() -> str:
    phone_number_id = os.environ["META_WA_PHONE_NUMBER_ID"]
    return f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_number_id}/messages"


def _headers() -> dict:
    token = os.environ["META_WA_ACCESS_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post(payload: dict, call_id: str = "-") -> dict:
    """POST with retry on transient failures. Never retries a 4xx (except 429)."""
    last: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(_base_url(), headers=_headers(), json=payload, timeout=15)
        except requests.RequestException as exc:
            last = WhatsAppError(f"network error: {exc}")
            log_event("whatsapp_retry", call_id, attempt=attempt, reason=str(exc))
        else:
            if resp.ok:
                data = resp.json()
                log_event("whatsapp_sent", call_id, type=payload.get("type"),
                          message_id=(data.get("messages") or [{}])[0].get("id"))
                return data
            err = {}
            try:
                err = resp.json().get("error", {})
            except ValueError:
                pass
            last = WhatsAppError(err.get("message", resp.text[:200]),
                                 status=resp.status_code, code=err.get("code"))
            if resp.status_code not in RETRY_STATUS:
                log_event("whatsapp_failed", call_id, status=resp.status_code,
                          code=err.get("code"), message=err.get("message"))
                raise last
            log_event("whatsapp_retry", call_id, attempt=attempt, status=resp.status_code)
        if attempt < MAX_ATTEMPTS:
            time.sleep(0.5 * 2 ** (attempt - 1))
    assert last is not None
    raise last


def _to(number: str) -> str:
    return number.lstrip("+")


def send_text(to_number: str, body: str, call_id: str = "-") -> dict:
    return _post({"messaging_product": "whatsapp", "to": _to(to_number), "type": "text",
                  "text": {"body": body, "preview_url": False}}, call_id)


def send_document(to_number: str, link: str, filename: str, caption: str = "",
                  call_id: str = "-") -> dict:
    return _post({"messaging_product": "whatsapp", "to": _to(to_number), "type": "document",
                  "document": {"link": link, "filename": filename, "caption": caption}}, call_id)


def send_image(to_number: str, link: str, caption: str = "", call_id: str = "-") -> dict:
    return _post({"messaging_product": "whatsapp", "to": _to(to_number), "type": "image",
                  "image": {"link": link, "caption": caption}}, call_id)


def send_template(to_number: str, template_name: str, body_params: list[str],
                  language: str = "en", call_id: str = "-") -> dict:
    components = []
    if body_params:
        components.append({"type": "body",
                           "parameters": [{"type": "text", "text": p} for p in body_params]})
    return _post({"messaging_product": "whatsapp", "to": _to(to_number), "type": "template",
                  "template": {"name": template_name, "language": {"code": language},
                               "components": components}}, call_id)


def send_text_or_template(to_number: str, body: str, template_name: str,
                          body_params: list[str], language: str = "en",
                          call_id: str = "-") -> dict:
    """Free-form text inside the 24h window, approved template outside it."""
    try:
        return send_text(to_number, body, call_id)
    except WhatsAppError as exc:
        if exc.code != REENGAGEMENT_ERROR_CODE:
            raise
        log_event("whatsapp_template_fallback", call_id, template=template_name)
        return send_template(to_number, template_name, body_params, language, call_id)
