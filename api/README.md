---
title: Getaround Pricing API
emoji: 💰
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Getaround Pricing API

API REST pour estimer le prix journalier d'une location Getaround.
Bloc 5 Jedha CDSD - Aymeric Lahonde.

URL en ligne : https://huggingface.co/spaces/Alh92500/getaround-api

## Endpoints

- `GET /` - page d'accueil HTML
- `GET /health` - etat de l'API et du modele charge (type, 13 features)
- `GET /docs` - Swagger UI
- `POST /predict` - prediction du prix journalier (1+ voitures)

## Architecture

Le modele (pipeline sklearn : preprocessing + RandomForestRegressor) est
**embarque dans le dossier api/** sous forme de `model.joblib` et charge en
LOCAL au demarrage :

```python
import joblib
MODEL = joblib.load("model.joblib")
```

L'API est donc **autonome** : aucune dependance a un serveur MLflow distant,
elle ne peut plus crasher au boot. Le fichier `model.joblib` est produit par
`notebooks/01_train_pricing.py`, qui trace en parallele params / metrics /
artifacts dans MLflow (partie tracking du projet).

Aucun secret a configurer sur le Space.

## Format d'entree (impose par l'enonce Jedha)

`POST /predict` attend `{"input": [[...13 valeurs ordonnees...], ...]}` :

```
[model_key, mileage, engine_power, fuel, paint_color, car_type,
 private_parking_available, has_gps, has_air_conditioning, automatic_car,
 has_getaround_connect, has_speed_regulator, winter_tires]
```

## Test curl

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"input": [["Citroen", 140000, 100, "diesel", "black", "convertible",
                  true, true, false, false, true, true, true]]}' \
  https://alh92500-getaround-api.hf.space/predict
# -> {"prediction":[120.15]}
```

## Tests

```bash
cd api && pytest -v     # 4 tests : /health, /predict simple, batch, 422
```

## Rejouer en local

```bash
# 1. Entrainer + generer api/model.joblib
python notebooks/01_train_pricing.py --n_estimators 200 --max_depth 18

# 2. Lancer l'API
cd api
uvicorn main:app --reload --port 8000
# -> http://127.0.0.1:8000/docs
```

## Deploiement HF Spaces (huggingface_hub)

```python
from huggingface_hub import HfApi
HfApi().upload_folder(
    folder_path="api",
    repo_id="Alh92500/getaround-api",
    repo_type="space",
    token="<HF_TOKEN write>",
)
```
