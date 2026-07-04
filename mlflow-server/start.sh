#!/bin/bash
# Setup A : tout en local sur le Space HF, pas d'AWS.
# - Backend store : SQLite dans /mlflow/mlflow.db
# - Artifact store : /mlflow/artifacts (local au container)
# - --serve-artifacts : le serveur proxie les artefacts -> les clients
#                       (training + API) n'ont besoin QUE de MLFLOW_TRACKING_URI.

mlflow server \
    --host 0.0.0.0 \
    --port 7860 \
    --backend-store-uri sqlite:///mlflow/mlflow.db \
    --default-artifact-root /mlflow/artifacts \
    --serve-artifacts \
    --disable-security-middleware
