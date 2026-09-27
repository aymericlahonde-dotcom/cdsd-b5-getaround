"""Tests du client HTTP de l'API pricing (lancer : cd dashboard && pytest -v)."""
import pytest
import requests

import pricing_client as pc

CITROEN = ["Citroen", 140000, 100, "diesel", "black", "convertible",
           True, True, False, False, True, True, True]


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_build_payload_wraps_row():
    assert pc.build_payload(CITROEN) == {"input": [CITROEN]}


def test_build_payload_rejects_wrong_length():
    with pytest.raises(ValueError):
        pc.build_payload(CITROEN[:5])


def test_curl_command_targets_predict():
    cmd = pc.curl_command("https://x.hf.space", {"input": [CITROEN]})
    assert cmd.startswith("curl -X POST")
    assert cmd.endswith("https://x.hf.space/predict")
    assert '"Citroen"' in cmd


def test_predict_success(monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        lambda url, json, timeout: FakeResponse(200, {"prediction": [120.15]}),
    )
    res = pc.predict("https://x.hf.space/", CITROEN)
    assert res.price == 120.15
    assert res.url == "https://x.hf.space/predict"
    assert res.response_json == {"prediction": [120.15]}
    assert res.latency_s >= 0


def test_predict_http_error_shows_detail(monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        lambda url, json, timeout: FakeResponse(422, {"detail": "ligne 0 : 12 valeurs"}),
    )
    with pytest.raises(pc.ApiError) as exc:
        pc.predict("https://x.hf.space", CITROEN)
    assert "422" in str(exc.value)
    assert "12 valeurs" in str(exc.value)


def test_predict_timeout_message(monkeypatch):
    def boom(url, json, timeout):
        raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(pc.ApiError) as exc:
        pc.predict("https://x.hf.space", CITROEN)
    assert "60" in str(exc.value)


def test_predict_missing_key(monkeypatch):
    monkeypatch.setattr(
        requests, "post", lambda url, json, timeout: FakeResponse(200, {"oops": 1}),
    )
    with pytest.raises(pc.ApiError):
        pc.predict("https://x.hf.space", CITROEN)
