"""Bloc 5 — Getaround pricing : training + tracking MLflow.

Pattern aligné sur l'exercice Jedha appointment_cancellation_detector :
    - argparse pour passer les hyperparams en CLI
    - mlflow.sklearn.autolog(log_models=False) -> log auto des params/metrics
    - MlflowClient.create_run() puis mlflow.start_run(run_id=...)
    - mlflow.sklearn.log_model(... registered_model_name=...) pour le registry

Run :
    python notebooks/01_train_pricing.py --n_estimators 200 --max_depth 18
    mlflow ui     # http://127.0.0.1:5000
"""
import argparse
import os
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "get_around_pricing_project.csv"
MLRUNS_DIR = ROOT / "mlruns"
RUN_ID_FILE = ROOT / "api" / ".last_run_id"
# Modele embarque dans l'API : chargé en LOCAL au démarrage (joblib.load),
# ce qui rend l'API autonome (aucune dépendance au serveur MLflow distant).
API_MODEL_FILE = ROOT / "api" / "model.joblib"

EXPERIMENT_NAME = "getaround-pricing"
MODEL_NAME = "getaround_pricer"
ARTIFACT_PATH = "getaround_pricer"

CAT_COLS = ["model_key", "fuel", "paint_color", "car_type"]
BOOL_COLS = [
    "private_parking_available", "has_gps", "has_air_conditioning",
    "automatic_car", "has_getaround_connect", "has_speed_regulator",
    "winter_tires",
]
NUM_COLS = ["mileage", "engine_power"]
TARGET = "rental_price_per_day"


if __name__ == "__main__":
    print("training model...")
    start_time = time.time()

    # --- MLFLOW Experiment setup (pattern Jedha) ---
    # Si MLFLOW_TRACKING_URI est defini (ex: serveur HF Spaces), on l'utilise.
    # Sinon, fallback file backend local pour dev / tests.
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        print(f"[mlflow] tracking distant : {tracking_uri}")
        mlflow.set_tracking_uri(tracking_uri)
    else:
        print(f"[mlflow] tracking local : {MLRUNS_DIR}")
        mlflow.set_tracking_uri(f"file:///{MLRUNS_DIR.as_posix()}")
    mlflow.set_experiment(EXPERIMENT_NAME)
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)

    client = mlflow.tracking.MlflowClient()
    run = client.create_run(experiment.experiment_id)

    # Autolog des params/metrics, on log le modèle à la main pour avoir
    # plus de contrôle (signature + registered_model_name)
    mlflow.sklearn.autolog(log_models=False)

    # --- CLI args ---
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=200)
    parser.add_argument("--max_depth", type=int, default=18)
    parser.add_argument("--min_samples_leaf", type=int, default=2)
    args = parser.parse_args()

    # --- Data loading ---
    # Encoding latin-1 pour fixer les Citroën / Citro�n du CSV source
    df = pd.read_csv(DATA_PATH, encoding="latin-1")
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    for c in BOOL_COLS:
        df[c] = df[c].astype(int)

    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # --- Preprocessing + Pipeline ---
    feature_preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT_COLS),
            ("num", StandardScaler(), NUM_COLS),
            ("bool", "passthrough", BOOL_COLS),
        ]
    )

    model = Pipeline(steps=[
        ("features_preprocessing", feature_preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_leaf=args.min_samples_leaf,
            n_jobs=-1,
            random_state=42,
        )),
    ])

    # --- Log experiment to MLFlow ---
    with mlflow.start_run(run_id=run.info.run_id) as run:
        model.fit(X_train, y_train)
        predictions = model.predict(X_train)

        # Log holdout metrics manuellement (autolog couvre déjà le train)
        y_pred_test = model.predict(X_test)
        rmse = float(np.sqrt(np.mean((y_test - y_pred_test) ** 2)))
        mae = float(np.mean(np.abs(y_test - y_pred_test)))
        mlflow.log_metric("test_rmse", rmse)
        mlflow.log_metric("test_mae", mae)

        # Log model séparément pour avoir signature + registered_model_name
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=ARTIFACT_PATH,
            registered_model_name=MODEL_NAME,
            signature=infer_signature(X_train, predictions),
        )

        # Sauve le run_id pour l'API (pratique en local sans MLflow distant)
        RUN_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        RUN_ID_FILE.write_text(run.info.run_id)

        # Export du pipeline complet (preprocessing + regressor) pour l'API.
        # L'API charge ce fichier en LOCAL au boot -> aucune dépendance au
        # serveur MLflow distant, donc plus de crash au démarrage.
        joblib.dump(model, API_MODEL_FILE)

        print(f"  run_id : {run.info.run_id}")
        print(f"  model  : {API_MODEL_FILE}")
        print(f"  test rmse : {rmse:.2f} EUR/jour")
        print(f"  test mae  : {mae:.2f} EUR/jour")
        print(f"  registry  : models:/{MODEL_NAME}/<version>")

    print("...Done!")
    print(f"---Total training time: {time.time() - start_time:.1f}s")
