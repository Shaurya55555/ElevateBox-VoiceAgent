import pytest

import app as app_module
import decision_engine

CALLER = "+919876543210"

HOT = {"classification": "Hot", "budget": "50k", "product_type": "candles",
       "product_count": "40", "timeline": "next month", "features": "",
       "barrier": "", "reasoning": "budget stated"}


@pytest.fixture()
def sent(monkeypatch):
    log = []
    monkeypatch.setattr(app_module.whatsapp, "send_text_or_template",
                        lambda *a, **k: log.append(("text", a[0], a[1])) or {})
    monkeypatch.setattr(app_module.whatsapp, "send_document",
                        lambda *a, **k: log.append(("doc", a[0])) or {})
    monkeypatch.setattr(app_module.whatsapp, "send_image",
                        lambda *a, **k: log.append(("img", a[0])) or {})
    return log


def tool_call_payload(call_id, tool_call_id, name, args):
    return {"message": {
        "type": "tool-calls",
        "call": {"id": call_id, "customer": {"number": CALLER}},
        "toolCallList": [{"id": tool_call_id, "function": {"name": name, "arguments": args}}],
    }}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_hot_fires_midcall_whatsapp_once(client, sent, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))
    for tc in ("tc1", "tc2"):  # two different Hot classifications in one call
        r = client.post("/vapi/webhook", json=tool_call_payload(
            "call-1", tc, "extract_and_classify", {"transcript_so_far": "x"}))
        assert r.json()["results"][0]["result"]["classification"] == "Hot"
    assert [e for e in sent if e[0] == "text"] == [("text", CALLER, sent[0][2])]


def test_tool_call_retry_returns_cached_result_without_resending(client, sent, monkeypatch):
    calls = []
    monkeypatch.setattr(decision_engine, "classify",
                        lambda t: calls.append(1) or dict(HOT))
    payload = tool_call_payload("call-2", "tc-same", "extract_and_classify",
                                {"transcript_so_far": "x"})
    first = client.post("/vapi/webhook", json=payload).json()
    second = client.post("/vapi/webhook", json=payload).json()
    assert first == second
    assert len(calls) == 1
    assert len(sent) == 1


def test_cold_sends_nothing_midcall(client, sent, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify",
                        lambda t: {**HOT, "classification": "Cold"})
    client.post("/vapi/webhook", json=tool_call_payload(
        "call-3", "tc1", "extract_and_classify", {"transcript_so_far": "just looking"}))
    assert sent == []


def test_whatsapp_failure_does_not_break_tool_result(client, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))

    def boom(*a, **k):
        raise RuntimeError("no token")

    monkeypatch.setattr(app_module.whatsapp, "send_text_or_template", boom)
    r = client.post("/vapi/webhook", json=tool_call_payload(
        "call-4", "tc1", "extract_and_classify", {"transcript_so_far": "x"}))
    result = r.json()["results"][0]["result"]
    assert result["classification"] == "Hot"
    assert "no token" in result["whatsapp_error"]


def test_schedule_callback_persists(client, db, monkeypatch):
    monkeypatch.setattr(decision_engine, "parse_callback_time",
                        lambda p, n: {"parsed_datetime": "2026-10-14T10:00:00+05:30"})
    r = client.post("/vapi/webhook", json=tool_call_payload(
        "call-5", "tc1", "schedule_callback",
        {"requested_time_raw": "tomorrow morning", "barrier": "checking with partner"}))
    assert r.json()["results"][0]["result"]["confirmed_datetime"].startswith("2026-10-14")
    rows = db.list_callbacks()
    assert len(rows) == 1
    assert rows[0]["caller_phone_number"] == CALLER
    assert rows[0]["barrier"] == "checking with partner"


def test_arguments_as_json_string(client, sent, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify", lambda t: {**HOT, "classification": "Warm"})
    r = client.post("/vapi/webhook", json=tool_call_payload(
        "call-6", "tc1", "extract_and_classify", '{"transcript_so_far": "hi"}'))
    assert r.json()["results"][0]["result"]["classification"] == "Warm"


def test_unknown_tool_returns_error(client):
    r = client.post("/vapi/webhook", json=tool_call_payload("call-7", "tc1", "nope", {}))
    assert "unknown tool" in r.json()["results"][0]["result"]["error"]


def end_of_call(call_id, transcript="caller wants a shop"):
    return {"message": {"type": "end-of-call-report",
                        "call": {"id": call_id, "customer": {"number": CALLER}},
                        "artifact": {"transcript": transcript}}}


def test_end_of_call_sends_text_resume_image_once(client, sent, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))
    monkeypatch.setattr(app_module, "RESUME_PUBLIC_URL", "https://example.com/r.pdf")
    monkeypatch.setattr(app_module, "ARCHITECTURE_IMAGE_URL", "https://example.com/a.png")
    assert client.post("/vapi/webhook", json=end_of_call("call-8")).status_code == 200
    assert [e[0] for e in sent] == ["text", "doc", "img"]
    client.post("/vapi/webhook", json=end_of_call("call-8"))  # duplicate delivery
    assert len(sent) == 3


def test_end_of_call_failed_send_can_be_retried(client, monkeypatch):
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))
    attempts = []

    def flaky(*a, **k):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("down")
        return {}

    monkeypatch.setattr(app_module.whatsapp, "send_text_or_template", flaky)
    monkeypatch.setattr(app_module.whatsapp, "send_document", lambda *a, **k: {})
    monkeypatch.setattr(app_module.whatsapp, "send_image", lambda *a, **k: {})
    client.post("/vapi/webhook", json=end_of_call("call-9"))
    client.post("/vapi/webhook", json=end_of_call("call-9"))
    assert len(attempts) == 2


def test_secret_enforced_when_configured(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    body = {"message": {"type": "status-update", "call": {"id": "c"}}}
    assert client.post("/vapi/webhook", json=body).status_code == 401
    ok = client.post("/vapi/webhook", json=body, headers={"x-vapi-secret": "s3cret"})
    assert ok.status_code == 200
