"""Getaround Pricing API — Bloc 5 Jedha.

Le modèle (pipeline sklearn preprocessing + RandomForest) est EMBARQUÉ dans
le dossier api/ sous forme de `model.joblib` et chargé en LOCAL au démarrage
via joblib.load. L'API est donc autonome : elle ne dépend d'aucun serveur
MLflow distant et ne peut plus crasher au boot si ce serveur est injoignable.

Le fichier model.joblib est produit par `notebooks/01_train_pricing.py`
(qui trace aussi params/metrics/artifacts dans MLflow pour la partie tracking).

Format input imposé par l'énoncé Getaround :
    POST /predict   { "input": [[...13 valeurs...], ...] }

Run local :
    uvicorn main:app --reload --port 8000
    open http://127.0.0.1:8000/docs
"""
from pathlib import Path
from typing import List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# ============================================================
# Chargement du modèle LOCAL au démarrage (joblib)
# ============================================================
HERE = Path(__file__).parent
MODEL_PATH = HERE / "model.joblib"

if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Modèle introuvable : {MODEL_PATH}. "
        "Lance d'abord : python notebooks/01_train_pricing.py "
        "(il génère api/model.joblib)."
    )

print(f"[model] loading {MODEL_PATH}")
MODEL = joblib.load(MODEL_PATH)
print("[model] loaded OK")

# Ordre des features attendu par le pipeline sklearn
FEATURE_NAMES = [
    "model_key", "mileage", "engine_power", "fuel", "paint_color",
    "car_type", "private_parking_available", "has_gps",
    "has_air_conditioning", "automatic_car", "has_getaround_connect",
    "has_speed_regulator", "winter_tires",
]
BOOL_FEATURES = [
    "private_parking_available", "has_gps", "has_air_conditioning",
    "automatic_car", "has_getaround_connect", "has_speed_regulator",
    "winter_tires",
]


# ============================================================
# Documentation API (style Jedha IBM)
# ============================================================
description = """
Getaround Pricing API — estime le prix journalier de location d'une voiture
sur la marketplace Getaround à partir de ses caractéristiques techniques.

## Endpoints

* `GET /` — page d'accueil HTML
* `GET /health` — état de l'API et du modèle chargé
* `GET /docs` — documentation OpenAPI interactive (Swagger UI)
* `POST /predict` — prédit le prix journalier pour une ou plusieurs voitures

Construit pour le Bloc 5 de la certification Jedha CDSD.
"""

tags_metadata = [
    {"name": "Root", "description": "Page d'accueil et health check"},
    {"name": "Predictions", "description": "Endpoint ML de pricing"},
]


# ============================================================
# Modèles Pydantic
# ============================================================
class PredictionInput(BaseModel):
    """Format imposé par l'énoncé Jedha Getaround.

    Chaque ligne contient 13 valeurs ordonnées :
        [model_key, mileage, engine_power, fuel, paint_color, car_type,
         private_parking_available, has_gps, has_air_conditioning,
         automatic_car, has_getaround_connect, has_speed_regulator,
         winter_tires]
    """
    input: List[List] = Field(
        ...,
        examples=[[
            ["Citroen", 140000, 100, "diesel", "black", "convertible",
             True, True, False, False, True, True, True],
        ]],
    )


class PredictionOutput(BaseModel):
    prediction: List[float]


class HealthOutput(BaseModel):
    status: str
    model_loaded: bool
    model_type: str
    n_features: int
    features: List[str]


# ============================================================
# App
# ============================================================
app = FastAPI(
    title="Getaround Pricing API",
    description=description,
    version="1.0",
    contact={"name": "Aymeric Lahonde", "url": "https://app.jedha.co/"},
    openapi_tags=tags_metadata,
)


# ============================================================
# Endpoints
# ============================================================
@app.get("/", response_class=HTMLResponse, tags=["Root"])
def home() -> str:
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <title>Getaround Pricing API</title>
        <style>
            body { font-family: -apple-system, sans-serif; max-width: 720px;
                   margin: 60px auto; padding: 0 24px; color: #2c2c2c; }
            h1 { color: #6A1B9A; }
            code { background: #f3f0fa; padding: 2px 6px; border-radius: 3px; }
            a { color: #00BFA5; }
            pre { background: #f7f6fa; padding: 16px; border-radius: 6px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Getaround Pricing API</h1>
        <p>API REST pour estimer le prix journalier de location d'une voiture.</p>

        <h2>Endpoints</h2>
        <ul>
            <li><code>GET /</code> — cette page</li>
            <li><code>GET <a href="/health">/health</a></code> — état de l'API (modèle chargé ?)</li>
            <li><code>GET <a href="/docs">/docs</a></code> — Swagger UI interactive</li>
            <li><code>POST /predict</code> — prédit le prix journalier</li>
        </ul>

        <h2>Exemple curl</h2>
        <pre>curl -X POST -H "Content-Type: application/json" \\
  -d '{"input": [["Citroen", 140000, 100, "diesel", "black", "convertible",
                  true, true, false, false, true, true, true]]}' \\
  http://127.0.0.1:8000/predict</pre>

        <p style="margin-top:40px; color:#888; font-size:13px;">
            Bloc 5 — Aymeric Lahonde — CDSD Jedha 2026
        </p>
    </body>
    </html>
    """


@app.get("/health", response_model=HealthOutput, tags=["Root"])
def health() -> HealthOutput:
    """Health check : confirme que le modèle est chargé et décrit ses entrées."""
    regressor = MODEL.named_steps["regressor"]
    return HealthOutput(
        status="ok",
        model_loaded=MODEL is not None,
        model_type=type(regressor).__name__,
        n_features=len(FEATURE_NAMES),
        features=FEATURE_NAMES,
    )


@app.post("/predict", response_model=PredictionOutput, tags=["Predictions"])
def predict(payload: PredictionInput) -> PredictionOutput:
    """Prédit le prix journalier (€) pour 1+ voitures.

    Format input ligne (13 valeurs ordonnées) :
        [model_key, mileage, engine_power, fuel, paint_color, car_type,
         private_parking_available, has_gps, has_air_conditioning,
         automatic_car, has_getaround_connect, has_speed_regulator,
         winter_tires]

    Renvoie : { "prediction": [73.5, 91.2, ...] }
    """
    rows = payload.input
    if not rows:
        raise HTTPException(status_code=422, detail="input vide")
    expected = len(FEATURE_NAMES)
    for i, row in enumerate(rows):
        if len(row) != expected:
            raise HTTPException(
                status_code=422,
                detail=f"ligne {i} : {len(row)} valeurs reçues, {expected} attendues",
            )

    df = pd.DataFrame(rows, columns=FEATURE_NAMES)
    # Bool en int (le pipeline a une branche passthrough qui attend numérique)
    for c in BOOL_FEATURES:
        df[c] = df[c].astype(int)

    preds = MODEL.predict(df)
    return PredictionOutput(prediction=[round(float(p), 2) for p in preds])
