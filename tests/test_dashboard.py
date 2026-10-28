import pytest

import app as app_module
import decision_engine

CALLER = "+919876543210"
HOT = {"classification": "Hot", "budget": "50k", "product_type": "candles",
       "product_count": "40", "timeline": "next month", "features": "",
       "barrier": "", "reasoning": "budget stated"}
ADMIN = {"x-admin-token": "s3cret"}


@pytest.fixture()
def wa(monkeypatch):
    sent = []
    monkeypatch.setattr(app_module.whatsapp, "send_text_or_template",
                        lambda *a, **k: sent.append(a[0]) or {})
    monkeypatch.setattr(app_module.whatsapp, "send_document", lambda *a, **k: {})
    monkeypatch.setattr(app_module.whatsapp, "send_image", lambda *a, **k: {})
    return sent


def tool(call_id, tc_id, name, args):
    return {"message": {"type": "tool-calls",
                        "call": {"id": call_id, "customer": {"number": CALLER}},
                        "toolCallList": [{"id": tc_id, "function": {"name": name, "arguments": args}}]}}


def test_admin_disabled_without_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert client.get("/api/admin/overview").status_code == 503


def test_admin_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"x-admin-token": "no"}).status_code == 401


def test_full_call_shows_up_on_dashboard(client, wa, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))
    monkeypatch.setattr(decision_engine, "parse_callback_time",
                        lambda p, n: {"parsed_datetime": "2026-11-01T10:00:00+05:30"})

    client.post("/vapi/webhook", json=tool("c1", "t1", "extract_and_classify",
                                           {"transcript_so_far": "x"}))
    client.post("/vapi/webhook", json=tool("c1", "t2", "schedule_callback",
                                           {"requested_time_raw": "tomorrow 10am"}))
    client.post("/vapi/webhook", json={"message": {
        "type": "end-of-call-report", "summary": "Wants a 40-product store.",
        "call": {"id": "c1", "customer": {"number": CALLER}}, "artifact": {"transcript": "hi"}}})

    data = client.get("/api/admin/overview", headers=ADMIN).json()
    assert data["stats"]["leads_total"] == 1
    assert data["stats"]["by_label"] == {"Hot": 1}
    lead = data["leads"][0]
    assert lead["phone"] == CALLER and lead["classification"] == "Hot"
    assert lead["midcall_whatsapp"] is True and lead["postcall_whatsapp"] == "sent"
    assert lead["summary"] == "Wants a 40-product store."
    assert lead["facts"]["budget"] == "50k"
    assert data["callbacks"]["pending"][0]["requested_time_raw"] == "tomorrow 10am"


def test_callback_status_can_be_updated(client, monkeypatch, db):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    cid = db.add_callback(CALLER, "tomorrow", "2026-11-01T10:00:00+05:30", "")
    r = client.post(f"/api/admin/callbacks/{cid}", json={"status": "done"}, headers=ADMIN)
    assert r.status_code == 200
    assert db.list_callbacks("pending") == [] and len(db.list_callbacks("done")) == 1
    assert client.post(f"/api/admin/callbacks/{cid}", json={"status": "bogus"},
                       headers=ADMIN).status_code == 400
    assert client.post("/api/admin/callbacks/999", json={"status": "done"},
                       headers=ADMIN).status_code == 404


def test_lead_is_saved_even_when_whatsapp_fails(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    monkeypatch.setattr(decision_engine, "classify", lambda t: dict(HOT))

    def boom(*a, **k):
        raise RuntimeError("meta down")

    monkeypatch.setattr(app_module.whatsapp, "send_text_or_template", boom)
    client.post("/vapi/webhook", json=tool("c2", "t1", "extract_and_classify",
                                           {"transcript_so_far": "x"}))
    leads = client.get("/api/admin/overview", headers=ADMIN).json()["leads"]
    assert leads[0]["classification"] == "Hot" and leads[0]["midcall_whatsapp"] is False
