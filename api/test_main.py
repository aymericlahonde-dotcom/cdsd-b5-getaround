"""Tests de l'API de pricing Getaround (lancer : cd api && pytest -v)."""
from fastapi.testclient import TestClient

from main import FEATURE_NAMES, app

client = TestClient(app)

CITROEN = ["Citroen", 140000, 100, "diesel", "black", "convertible",
           True, True, False, False, True, True, True]


def test_health_reports_model_loaded():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["n_features"] == 13
    assert body["features"] == FEATURE_NAMES


def test_predict_returns_one_rounded_price():
    r = client.post("/predict", json={"input": [CITROEN]})
    assert r.status_code == 200
    preds = r.json()["prediction"]
    assert len(preds) == 1
    assert preds[0] > 0
    assert round(preds[0], 2) == preds[0]


def test_predict_batch_returns_one_price_per_row():
    r = client.post("/predict", json={"input": [CITROEN, CITROEN]})
    assert r.status_code == 200
    assert len(r.json()["prediction"]) == 2


def test_predict_rejects_wrong_number_of_values():
    r = client.post("/predict", json={"input": [CITROEN[:12]]})
    assert r.status_code == 422
    assert "12 valeurs" in r.json()["detail"]
