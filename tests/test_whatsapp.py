import pytest

import whatsapp


class FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.ok = 200 <= status < 300
        self.text = str(body)

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(whatsapp.time, "sleep", lambda s: None)


def patch_post(monkeypatch, responses):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return responses.pop(0)

    monkeypatch.setattr(whatsapp.requests, "post", fake_post)
    return calls


def test_send_text_ok(monkeypatch):
    calls = patch_post(monkeypatch, [FakeResp(200, {"messages": [{"id": "wamid.1"}]})])
    assert whatsapp.send_text("+919999999999", "hi")["messages"][0]["id"] == "wamid.1"
    assert calls[0]["to"] == "919999999999"


def test_retries_on_server_error_then_succeeds(monkeypatch):
    calls = patch_post(monkeypatch, [FakeResp(503, {}), FakeResp(200, {"messages": [{"id": "x"}]})])
    whatsapp.send_text("+919999999999", "hi")
    assert len(calls) == 2


def test_does_not_retry_client_error(monkeypatch):
    calls = patch_post(monkeypatch, [FakeResp(400, {"error": {"message": "bad", "code": 100}})])
    with pytest.raises(whatsapp.WhatsAppError) as exc:
        whatsapp.send_text("+919999999999", "hi")
    assert exc.value.code == 100
    assert len(calls) == 1


def test_gives_up_after_max_attempts(monkeypatch):
    calls = patch_post(monkeypatch, [FakeResp(500, {})] * whatsapp.MAX_ATTEMPTS)
    with pytest.raises(whatsapp.WhatsAppError):
        whatsapp.send_text("+919999999999", "hi")
    assert len(calls) == whatsapp.MAX_ATTEMPTS


def test_falls_back_to_template_outside_24h_window(monkeypatch):
    calls = patch_post(monkeypatch, [
        FakeResp(400, {"error": {"message": "re-engagement", "code": 131047}}),
        FakeResp(200, {"messages": [{"id": "wamid.t"}]}),
    ])
    whatsapp.send_text_or_template("+919999999999", "hello", "post_call_followup",
                                   ["candles", "+91-7985200306"])
    assert calls[0]["type"] == "text"
    assert calls[1]["type"] == "template"
    assert calls[1]["template"]["name"] == "post_call_followup"
    params = calls[1]["template"]["components"][0]["parameters"]
    assert [p["text"] for p in params] == ["candles", "+91-7985200306"]


def test_other_errors_do_not_fall_back(monkeypatch):
    patch_post(monkeypatch, [FakeResp(400, {"error": {"message": "bad token", "code": 190}})])
    with pytest.raises(whatsapp.WhatsAppError):
        whatsapp.send_text_or_template("+919999999999", "hello", "t", [])
