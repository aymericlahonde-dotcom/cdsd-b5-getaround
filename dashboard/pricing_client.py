"""Client HTTP minimal pour l'API de pricing Getaround.

Utilisé par le dashboard Streamlit (onglet « Estimer un prix »). Aucune
dépendance à Streamlit : ce module est testable seul (voir test_pricing_client.py).
"""
import json
import os
import time
from dataclasses import dataclass

import requests

DEFAULT_API_URL = os.getenv("GETAROUND_API_URL", "https://alh92500-getaround-api.hf.space")
TIMEOUT_S = 60  # cold start d'un Space HuggingFace ≈ 15 s

FEATURE_NAMES = [
    "model_key", "mileage", "engine_power", "fuel", "paint_color",
    "car_type", "private_parking_available", "has_gps",
    "has_air_conditioning", "automatic_car", "has_getaround_connect",
    "has_speed_regulator", "winter_tires",
]


class ApiError(Exception):
    """Erreur d'appel API, message en clair prêt à être affiché."""


@dataclass
class PredictResult:
    price: float
    payload: dict
    response_json: dict
    latency_s: float
    url: str


def build_payload(row: list) -> dict:
    """Construit le JSON imposé par l'énoncé : {"input": [[13 valeurs]]}."""
    if len(row) != len(FEATURE_NAMES):
        raise ValueError(f"{len(row)} valeurs reçues, {len(FEATURE_NAMES)} attendues")
    return {"input": [list(row)]}


def curl_command(api_url: str, payload: dict) -> str:
    """Commande curl équivalente, à copier-coller devant le jury."""
    body = json.dumps(payload, ensure_ascii=False)
    return (
        'curl -X POST -H "Content-Type: application/json" '
        f"-d '{body}' {api_url.rstrip('/')}/predict"
    )


def check_health(api_url: str, timeout: float = TIMEOUT_S) -> dict:
    """GET /health ; lève ApiError si injoignable ou réponse non 200."""
    url = f"{api_url.rstrip('/')}/health"
    try:
        r = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise ApiError(f"Pas de réponse de {url} en {timeout:.0f} s.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(f"Connexion impossible à {url}.") from exc
    if r.status_code != 200:
        raise ApiError(f"{url} a répondu HTTP {r.status_code}.")
    return r.json()


def predict(api_url: str, row: list, timeout: float = TIMEOUT_S) -> PredictResult:
    """POST /predict pour une voiture ; renvoie le prix et les données brutes."""
    payload = build_payload(row)
    url = f"{api_url.rstrip('/')}/predict"
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise ApiError(
            f"L'API n'a pas répondu en {timeout:.0f} s. Le Space HuggingFace est "
            "peut-être en train de se réveiller : réessaie dans quelques secondes."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(
            f"Connexion impossible à {url}. Vérifie l'URL de l'API dans la sidebar "
            "(en secours : http://127.0.0.1:8000 avec l'API lancée en local)."
        ) from exc
    latency = time.perf_counter() - t0

    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(f"L'API a répondu HTTP {r.status_code} : {detail}")

    data = r.json()
    preds = data.get("prediction") if isinstance(data, dict) else None
    if not preds:
        raise ApiError(f"Réponse inattendue (pas de clé 'prediction') : {data}")

    return PredictResult(
        price=float(preds[0]),
        payload=payload,
        response_json=data,
        latency_s=latency,
        url=url,
    )
