# Volet prédiction dashboard + fiabilisation démo API + PPT soutenance — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire apparaître l'API `/predict` dans le dashboard Streamlit (formulaire → `requests.post` → réponse affichée), ajouter `GET /health` et des tests à l'API, redéployer les deux Spaces HuggingFace, produire un PPT de soutenance exact (liens cliquables, slide solution, slide vision API, slide présentation API) et un kit de démo pour le mercredi 2026-09-30 19h30.

**Architecture:** Le dashboard passe en deux onglets `st.tabs`. Le contenu actuel de `dashboard/app.py` est déplacé tel quel dans `dashboard/delay_analysis.py` (fonction `render(df)`). Un client HTTP pur (`dashboard/pricing_client.py`, sans Streamlit, testable) parle à l'API ; `dashboard/pricing_ui.py` fait le formulaire Streamlit. Côté API, `main.py` gagne `GET /health` et arrondit les prix ; le format de `/predict` reste celui de l'énoncé. Le PPT est généré par un script python-pptx réutilisant `Jedha/_ppt_helpers.py` (thème Getaround existant) plus un helper de liens cliquables.

**Tech Stack:** Python 3.11 (venv `Jedha/.venv`), Streamlit 1.58, requests, FastAPI + TestClient (httpx), pytest, huggingface_hub, python-pptx 1.0.2, Docker Spaces HF.

## Global Constraints

- Interpréteur pour toutes les commandes : `PY="C:/Users/aymer/Desktop/Jedha certification/Jedha/.venv/Scripts/python.exe"` (Python 3.11.9, scikit-learn 1.8.0 identique à celui qui a produit `model.joblib`). Sous bash, préfixer par `PYTHONIOENCODING=utf-8` pour éviter les erreurs cp1252 à l'affichage.
- Racine du projet : `C:/Users/aymer/Desktop/Jedha certification/Jedha/Bloc_5_Getaround` (repo git, branche `main`, remote GitHub `aymericlahonde-dotcom/cdsd-b5-getaround`). Les helpers PPT sont un niveau au-dessus : `C:/Users/aymer/Desktop/Jedha certification/Jedha/_ppt_helpers.py`.
- Format de `POST /predict` **inchangé** : entrée `{"input": [[13 valeurs]]}`, sortie `{"prediction": [float, ...]}`.
- URL API par défaut : `https://alh92500-getaround-api.hf.space`, surchargée par la variable d'environnement `GETAROUND_API_URL`.
- Timeout HTTP côté dashboard : `60` secondes (cold start HF ≈ 15 s).
- Ordre des 13 features (énoncé) : `model_key, mileage, engine_power, fuel, paint_color, car_type, private_parking_available, has_gps, has_air_conditioning, automatic_car, has_getaround_connect, has_speed_regulator, winter_tires`.
- URLs publiques (à utiliser telles quelles dans le PPT et les docs) :
  - Dashboard : `https://alh92500-getaround-dashboard.hf.space` (Space : `https://huggingface.co/spaces/Alh92500/getaround-dashboard`)
  - API : `https://alh92500-getaround-api.hf.space` ; `/docs`, `/health`, `/predict`  (Space : `https://huggingface.co/spaces/Alh92500/getaround-api`)
  - GitHub : `https://github.com/aymericlahonde-dotcom/cdsd-b5-getaround`
- Les fichiers `PREPARE_JURY.md`, `DEMO_CHECKLIST.md`, `captures/` sont gitignored (usage perso).
- Le PPT ne doit contenir **aucune affirmation absente du code** (pas de docker-compose, pas de multi-stage, pas de « 11 features », pas de lien MLflow HF). Les métriques sont lues dans `mlruns/` (Task 6 Step 1).
- Encodage des fichiers Python : UTF-8.

---

### Task 1: API — `GET /health`, arrondi des prix, tests pytest

**Files:**
- Modify: `api/main.py`
- Create: `api/test_main.py`
- Modify: `requirements.txt` (racine, ajouter `pytest` et `httpx`)

**Interfaces:**
- Produces: `GET /health` → `{"status": "ok", "model_loaded": true, "model_type": str, "n_features": 13, "features": [str×13]}` ; `POST /predict` → `{"prediction": [float arrondi à 2 déc.]}`.

- [ ] **Step 1: Installer pytest dans le venv**

Run: `"$PY" -m pip install pytest`
Expected: `Successfully installed pytest-...`

- [ ] **Step 2: Écrire les tests (échouent d'abord)**

Créer `api/test_main.py` :

```python
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
```

- [ ] **Step 3: Vérifier que les tests échouent**

Run: `cd api && "$PY" -m pytest test_main.py -v`
Expected: `test_health_reports_model_loaded FAILED` (404), `test_predict_returns_one_rounded_price FAILED` (arrondi), les 2 autres PASS.

- [ ] **Step 4: Implémenter `/health` et l'arrondi dans `api/main.py`**

Remplacer le bloc `description = """..."""` par :

```python
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
```

Après `class PredictionOutput`, ajouter :

```python
class HealthOutput(BaseModel):
    status: str
    model_loaded: bool
    model_type: str
    n_features: int
    features: List[str]
```

Dans la page HTML `home()`, ajouter dans la liste `<ul>` juste après la ligne `GET /` :

```html
            <li><code>GET <a href="/health">/health</a></code> — état de l'API (modèle chargé ?)</li>
```

Après la fonction `home()` et avant `predict()`, ajouter :

```python
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
```

Dans `predict()`, remplacer la dernière ligne par :

```python
    return PredictionOutput(prediction=[round(float(p), 2) for p in preds])
```

- [ ] **Step 5: Vérifier que les 4 tests passent**

Run: `cd api && "$PY" -m pytest test_main.py -v`
Expected: `4 passed`

- [ ] **Step 6: Ajouter pytest/httpx au requirements racine**

Ajouter à la fin de `requirements.txt` (racine, pas `api/requirements.txt`) :

```
# Tests (API + client dashboard)
pytest
httpx
```

- [ ] **Step 7: Commit**

```bash
git add api/main.py api/test_main.py requirements.txt
git commit -m "API : endpoint /health, prix arrondis, 4 tests pytest"
```

---

### Task 2: Dashboard — client HTTP pur `pricing_client.py` + tests

**Files:**
- Create: `dashboard/pricing_client.py`
- Create: `dashboard/test_pricing_client.py`
- Modify: `dashboard/requirements.txt` (ajouter `requests`)

**Interfaces:**
- Produces:
  - `FEATURE_NAMES: list[str]` (13 noms), `DEFAULT_API_URL: str`, `TIMEOUT_S = 60`
  - `build_payload(row: list) -> dict` → `{"input": [row]}` ; `ValueError` si `len(row) != 13`
  - `curl_command(api_url: str, payload: dict) -> str`
  - `check_health(api_url: str, timeout: float = 60) -> dict`
  - `predict(api_url: str, row: list, timeout: float = 60) -> PredictResult`
  - `PredictResult` dataclass : `price: float, payload: dict, response_json: dict, latency_s: float, url: str`
  - `ApiError(Exception)` avec message en français prêt à afficher.

- [ ] **Step 1: Écrire les tests (échouent d'abord)**

Créer `dashboard/test_pricing_client.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `cd dashboard && "$PY" -m pytest test_pricing_client.py -v`
Expected: `ModuleNotFoundError: No module named 'pricing_client'`

- [ ] **Step 3: Implémenter `dashboard/pricing_client.py`**

```python
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
```

- [ ] **Step 4: Vérifier que les 7 tests passent**

Run: `cd dashboard && "$PY" -m pytest test_pricing_client.py -v`
Expected: `7 passed`

- [ ] **Step 5: Ajouter `requests` aux dépendances du dashboard**

`dashboard/requirements.txt` devient :

```
streamlit
pandas
plotly
openpyxl
requests
```

- [ ] **Step 6: Commit**

```bash
git add dashboard/pricing_client.py dashboard/test_pricing_client.py dashboard/requirements.txt
git commit -m "Dashboard : client HTTP pricing_client (predict, health, curl) + 7 tests"
```

---

### Task 3: Dashboard — onglets, `delay_analysis.py`, `pricing_ui.py`, Dockerfile

**Files:**
- Create: `dashboard/delay_analysis.py` (contenu actuel de `app.py` à partir de la sidebar, déplacé dans `render(df)`)
- Create: `dashboard/pricing_ui.py`
- Modify: `dashboard/app.py` (devient court : config, chargement données, sidebar API, onglets)
- Modify: `dashboard/Dockerfile` (copier les 4 fichiers .py)

**Interfaces:**
- Consumes: `pricing_client.predict`, `check_health`, `curl_command`, `DEFAULT_API_URL`, `ApiError`, `PredictResult` (Task 2).
- Produces: `delay_analysis.render(df: pd.DataFrame) -> None` ; `pricing_ui.render(api_url: str) -> None`.

- [ ] **Step 1: Créer `dashboard/delay_analysis.py` en déplaçant le code existant**

Le fichier contient les imports `numpy`, `pandas`, `plotly.express`, `streamlit`, la fonction `filter_scope` existante, et une fonction `render(df)` qui contient **à l'identique** tout le code actuel de `app.py` depuis `st.sidebar.header("⚙️ Parametres de la mesure")` jusqu'à `st.caption("🎓 Aymeric Lahonde - Jedha CDSD Bloc 5 Getaround")` inclus, indenté d'un niveau. Le calcul de `prev` / `consecutive` / `next_driver_impacted` reste tel quel à l'intérieur de `render`. Squelette :

```python
"""Onglet « Analyse des retards » : réponses aux 4 questions du Product Manager.

Code déplacé tel quel depuis app.py pour laisser place à l'onglet prédiction.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def filter_scope(d: pd.DataFrame, scope_choice: str) -> pd.DataFrame:
    return d if scope_choice == "all" else d[d["checkin_type"] == "connect"]


def render(df: pd.DataFrame) -> None:
    """Affiche sidebar (seuil, scope), KPI, Q1..Q4 et recommandation."""
    st.sidebar.header("⚙️ Parametres de la mesure")
    threshold_min = st.sidebar.slider(
        "Seuil minimum entre 2 locations (minutes)",
        min_value=0, max_value=720, value=90, step=15,
        help="Une location est bloquee si elle commence < threshold min apres la fin de la precedente",
    )
    # ... suite identique à app.py (scope, consecutive, KPI, Q1, Q2, Q3, Q4,
    # recommandation), indentée dans render()
```

Vérification syntaxe : `"$PY" -c "import ast; ast.parse(open('dashboard/delay_analysis.py', encoding='utf-8').read()); print('ok')"` → `ok`.

- [ ] **Step 2: Créer `dashboard/pricing_ui.py`**

```python
"""Onglet « Estimer un prix » : formulaire → POST /predict de l'API → résultat.

C'est ici que le dashboard UTILISE l'API (critères jury « interface web
incluant l'utilisation de l'API »).
"""
import json

import streamlit as st

import pricing_client as pc

# Valeurs vues dans get_around_pricing_project.csv (codées en dur pour ne pas
# dépendre du CSV au runtime sur HF Spaces).
MODEL_KEYS = [
    "Alfa Romeo", "Audi", "BMW", "Citroën", "Ferrari", "Fiat", "Ford", "Honda",
    "KIA Motors", "Lamborghini", "Lexus", "Maserati", "Mazda", "Mercedes",
    "Mini", "Mitsubishi", "Nissan", "Opel", "PGO", "Peugeot", "Porsche",
    "Renault", "SEAT", "Subaru", "Suzuki", "Toyota", "Volkswagen", "Yamaha",
]
FUELS = ["diesel", "petrol", "hybrid_petrol", "electro"]
COLORS = ["black", "grey", "white", "blue", "silver", "red", "brown",
          "beige", "green", "orange"]
CAR_TYPES = ["convertible", "coupe", "estate", "hatchback", "sedan",
             "subcompact", "suv", "van"]
BOOL_LABELS = {
    "private_parking_available": "Parking privé",
    "has_gps": "GPS",
    "has_air_conditioning": "Climatisation",
    "automatic_car": "Boîte automatique",
    "has_getaround_connect": "Getaround Connect",
    "has_speed_regulator": "Régulateur de vitesse",
    "winter_tires": "Pneus hiver",
}
# Exemple de l'énoncé : Citroën diesel noire convertible, 140 000 km, 100 ch
DEFAULT_BOOLS = {
    "private_parking_available": True, "has_gps": True,
    "has_air_conditioning": False, "automatic_car": False,
    "has_getaround_connect": True, "has_speed_regulator": True,
    "winter_tires": True,
}


def _health_panel(api_url: str) -> None:
    st.markdown("#### 🩺 État de l'API")
    st.code(api_url, language=None)
    if st.button("Réveiller / vérifier l'API (GET /health)"):
        with st.spinner("Appel de /health…"):
            try:
                info = pc.check_health(api_url)
            except pc.ApiError as e:
                st.error(str(e))
            else:
                st.success(
                    f"API en ligne — modèle chargé : {info.get('model_type')} "
                    f"({info.get('n_features')} features)"
                )
                st.json(info)


def _form() -> list | None:
    """Affiche le formulaire ; renvoie la ligne de 13 valeurs si soumis."""
    with st.form("predict_form"):
        c1, c2, c3 = st.columns(3)
        model_key = c1.selectbox("Marque (model_key)", MODEL_KEYS,
                                 index=MODEL_KEYS.index("Citroën"))
        fuel = c2.selectbox("Carburant (fuel)", FUELS, index=0)
        car_type = c3.selectbox("Type (car_type)", CAR_TYPES, index=0)
        c4, c5, c6 = st.columns(3)
        paint_color = c4.selectbox("Couleur (paint_color)", COLORS, index=0)
        mileage = c5.number_input("Kilométrage (mileage)", min_value=0,
                                  max_value=1_000_000, value=140_000, step=1_000)
        engine_power = c6.number_input("Puissance ch (engine_power)", min_value=0,
                                       max_value=500, value=100, step=5)
        st.markdown("**Options**")
        bools = {}
        cols = st.columns(4)
        for i, (key, label) in enumerate(BOOL_LABELS.items()):
            bools[key] = cols[i % 4].checkbox(label, value=DEFAULT_BOOLS[key],
                                              key=f"bool_{key}")
        submitted = st.form_submit_button("🚀 Appeler l'API /predict", type="primary")

    if not submitted:
        return None
    return [
        model_key, int(mileage), int(engine_power), fuel, paint_color, car_type,
        bools["private_parking_available"], bools["has_gps"],
        bools["has_air_conditioning"], bools["automatic_car"],
        bools["has_getaround_connect"], bools["has_speed_regulator"],
        bools["winter_tires"],
    ]


def _show_result(res: pc.PredictResult) -> None:
    st.metric("Prix journalier estimé", f"{res.price:.2f} € / jour",
              delta=f"réponse en {res.latency_s * 1000:.0f} ms", delta_color="off")
    with st.expander("🔍 Détails techniques (ce que le dashboard a envoyé / reçu)",
                     expanded=True):
        st.markdown(f"**URL appelée :** `POST {res.url}`")
        st.markdown("**JSON envoyé** (format imposé par l'énoncé) :")
        st.code(json.dumps(res.payload, ensure_ascii=False, indent=2), language="json")
        st.markdown("**JSON reçu** (réponse brute de l'API) :")
        st.code(json.dumps(res.response_json, indent=2), language="json")
        st.markdown("**Équivalent curl :**")
        base = res.url.rsplit("/predict", 1)[0]
        st.code(pc.curl_command(base, res.payload), language="bash")


def render(api_url: str) -> None:
    st.subheader("💰 Estimer le prix journalier d'une voiture via l'API")
    st.caption(
        "Le formulaire construit le JSON attendu par `POST /predict`, l'envoie à "
        "l'API FastAPI déployée sur HuggingFace Spaces et affiche la réponse brute."
    )
    left, right = st.columns([2, 1])
    with right:
        _health_panel(api_url)
    with left:
        row = _form()
        if row is not None:
            with st.spinner("Appel de l'API… (jusqu'à 15 s si le Space se réveille)"):
                try:
                    res = pc.predict(api_url, row)
                except pc.ApiError as e:
                    st.error(str(e))
                else:
                    _show_result(res)
```

- [ ] **Step 3: Réécrire `dashboard/app.py` en fichier court**

```python
"""Dashboard Streamlit Getaround — Bloc 5 Jedha CDSD.

Deux onglets :
1. Analyse des retards de checkout (4 questions du Product Manager).
2. Estimation de prix : formulaire qui appelle l'API FastAPI /predict.

Usage local :
    streamlit run app.py
    GETAROUND_API_URL=http://127.0.0.1:8000 streamlit run app.py   # API locale

Déploiement HuggingFace Spaces (Docker) : voir Dockerfile.
"""
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

import delay_analysis
import pricing_ui
from pricing_client import DEFAULT_API_URL

st.set_page_config(
    page_title="Getaround - Delay Analysis & Pricing",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Getaround — Analyse des retards & estimation de prix")
st.caption(
    "Dashboard interactif : aide au choix d'un seuil minimum entre 2 locations, "
    "et appel de l'API de pricing. Bloc 5 Jedha CDSD — Aymeric Lahonde."
)

# ============================================================
# Chargement dataset (cache + fallback URL si fichier local absent)
# ============================================================
DATASET_URL = "https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx"
HERE = Path(__file__).parent
LOCAL_CANDIDATES = [
    HERE / "get_around_delay_analysis.xlsx",                 # bundle Docker
    HERE.parent / "data" / "get_around_delay_analysis.xlsx", # repo dev local
]


@st.cache_data
def load_data() -> pd.DataFrame:
    for p in LOCAL_CANDIDATES:
        if p.exists():
            return pd.read_excel(p)
    target = HERE / "get_around_delay_analysis.xlsx"
    urllib.request.urlretrieve(DATASET_URL, str(target))
    return pd.read_excel(target)


try:
    df = load_data()
except Exception as e:
    st.error(f"Impossible de charger le dataset : {e}")
    st.stop()

# ============================================================
# Sidebar — URL de l'API (modifiable en direct, ex. secours local)
# ============================================================
st.sidebar.header("🔌 API de pricing")
api_url = st.sidebar.text_input(
    "URL de l'API", value=DEFAULT_API_URL,
    help="Secours pendant la démo : http://127.0.0.1:8000 (uvicorn en local)",
)
st.sidebar.markdown("---")

# ============================================================
# Onglets
# ============================================================
tab_delay, tab_price = st.tabs(["📊 Analyse des retards", "💰 Estimer un prix (API)"])
with tab_delay:
    delay_analysis.render(df)
with tab_price:
    pricing_ui.render(api_url)
```

- [ ] **Step 4: Mettre à jour le Dockerfile**

Dans `dashboard/Dockerfile`, remplacer `COPY --chown=user:user app.py .` par :

```dockerfile
COPY --chown=user:user app.py delay_analysis.py pricing_client.py pricing_ui.py ./
```

- [ ] **Step 5: Vérifier en local, API locale + dashboard**

Terminal 1 : `cd api && "$PY" -m uvicorn main:app --port 8000`
Terminal 2 : `cd dashboard && GETAROUND_API_URL=http://127.0.0.1:8000 "$PY" -m streamlit run app.py --server.headless true --server.port 8501`
Expected : onglet 1 identique à avant (slider, 4 sections, recommandation) ; onglet 2 : bouton « Réveiller » → succès ; formulaire → clic → « 120.15 € / jour », expander avec JSON envoyé, JSON reçu, curl.
Vérification automatisée minimale : `"$PY" -c "import requests; print(requests.get('http://localhost:8501/_stcore/health').text)"` → `ok`, et aucune trace d'exception dans le terminal 2. Prendre une capture d'écran de l'onglet prédiction avec le résultat (servira au PPT et au plan de secours) : `captures/dashboard_prediction.png`.

- [ ] **Step 6: Vérifier contre l'API HuggingFace en ligne**

Relancer le dashboard sans `GETAROUND_API_URL` → l'URL sidebar est `https://alh92500-getaround-api.hf.space`. Clic « Réveiller » → succès (jusqu'à 15 s). Clic « Appeler l'API » → prix affiché.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app.py dashboard/delay_analysis.py dashboard/pricing_ui.py dashboard/Dockerfile
git commit -m "Dashboard : onglet Estimer un prix qui appelle POST /predict de l'API"
```

---

### Task 4: Script de déploiement HF + redéploiement + push GitHub

**Files:**
- Create: `deploy.py` (racine)
- Modify: `README.md` (racine), `dashboard/README.md`, `api/README.md`

**Interfaces:**
- Consumes: `.env` avec `HF_TOKEN`, `HF_USERNAME` (déjà présents).

- [ ] **Step 1: Créer `deploy.py`**

```python
"""Pousse api/ et dashboard/ vers leurs Spaces HuggingFace (Docker).

Usage :
    python deploy.py            # les deux
    python deploy.py api        # API seulement
    python deploy.py dashboard  # dashboard seulement

Lit HF_TOKEN et HF_USERNAME dans .env (jamais commité).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TOKEN = os.environ["HF_TOKEN"]
USER = os.environ.get("HF_USERNAME", "Alh92500")

SPACES = {
    "api": f"{USER}/getaround-api",
    "dashboard": f"{USER}/getaround-dashboard",
}
IGNORE = ["__pycache__/*", "test_*.py", ".last_run_id", "*.pyc", ".pytest_cache/*"]

targets = sys.argv[1:] or list(SPACES)
api = HfApi(token=TOKEN)
for name in targets:
    repo_id = SPACES[name]
    print(f"[deploy] {name}/ -> https://huggingface.co/spaces/{repo_id}")
    api.upload_folder(
        folder_path=str(ROOT / name),
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=IGNORE,
        commit_message=f"Deploy {name} (rattrapage Bloc 5)",
    )
    print("[deploy] OK")
```

- [ ] **Step 2: Déployer l'API puis le dashboard**

Run: `"$PY" deploy.py api` puis `"$PY" deploy.py dashboard`
Expected: `[deploy] OK` deux fois. Attendre que les Spaces passent RUNNING :
`curl -s https://huggingface.co/api/spaces/Alh92500/getaround-api | "$PY" -c "import sys,json;print(json.load(sys.stdin)['runtime']['stage'])"` → `RUNNING` (répéter toutes les 30 s, build Docker ≈ 2-4 min). Idem pour `getaround-dashboard`.

- [ ] **Step 3: Vérifier en ligne**

```bash
curl -s https://alh92500-getaround-api.hf.space/health
# -> {"status":"ok","model_loaded":true,"model_type":"RandomForestRegressor","n_features":13,"features":[...]}
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"input": [["Citroen",140000,100,"diesel","black","convertible",true,true,false,false,true,true,true]]}' \
  https://alh92500-getaround-api.hf.space/predict
# -> {"prediction":[120.15]}
```

Puis ouvrir `https://alh92500-getaround-dashboard.hf.space`, onglet « Estimer un prix », clic « Appeler l'API » → prix affiché. Si le Space dashboard affiche une erreur d'import, vérifier les logs du Space (onglet Logs sur huggingface.co) : cause probable = fichier manquant dans le `COPY` du Dockerfile.

- [ ] **Step 4: Mettre à jour les 3 README**

`README.md` racine :
- Dans « Livrables en ligne », ajouter `| Endpoint santé de l'API | <https://alh92500-getaround-api.hf.space/health> |`.
- Dans « Axe 1 », après « → Livrable : dashboard Streamlit en ligne », ajouter : « Le dashboard contient aussi un onglet **« Estimer un prix »** qui appelle l'API `/predict` (axe 2) depuis un formulaire. »
- Dans « Structure du projet », sous `dashboard/`, ajouter `delay_analysis.py`, `pricing_client.py`, `pricing_ui.py`, `test_pricing_client.py` ; sous `api/`, ajouter `test_main.py` ; à la racine ajouter `deploy.py`.
- Dans « Comment rejouer le projet en local », ajouter avant le dashboard :
  ```bash
  # Tests (API + client dashboard) : 11 tests
  (cd api && pytest -v) && (cd dashboard && pytest -v)
  ```
  et remplacer le bloc « Push via huggingface_hub » par `python deploy.py`.

`dashboard/README.md` : dans « Comment ça marche », ajouter un point 4 : « Onglet **Estimer un prix** : formulaire de 13 caractéristiques → `POST /predict` sur l'API FastAPI (Space `getaround-api`) → prix journalier + JSON brut + commande curl. » Mettre `short_description: Analyse retards + estimation prix via API` (≤ 60 caractères).

`api/README.md` : dans « Endpoints », ajouter `- GET /health - etat de l'API et du modele charge`.

- [ ] **Step 5: Commit et push GitHub**

```bash
git add deploy.py README.md dashboard/README.md api/README.md docs/superpowers/plans/
git commit -m "Déploiement : deploy.py + README (onglet prédiction, /health, tests)"
git push origin main
```

Expected : `main -> main` sans erreur ; le repo GitHub affiche le nouveau README.

---

### Task 5: Kit de soutenance (DEMO_CHECKLIST.md + PREPARE_JURY.md)

**Files:**
- Create: `DEMO_CHECKLIST.md` (gitignored)
- Modify: `PREPARE_JURY.md`
- Modify: `.gitignore` (ajouter `DEMO_CHECKLIST.md` et `captures/` sous `PREPARE_JURY.md`)

**Interfaces:** aucune (documents).

- [ ] **Step 1: Créer `DEMO_CHECKLIST.md`**

Contenu attendu, en français, sections :

1. **La veille (mardi 29/09)** : répéter la démo complète en chronométrant ; enregistrer une vidéo d'écran de 2 min (Xbox Game Bar `Win+G` ou OBS) du parcours dashboard → API → Swagger → curl ; faire 4 captures d'écran (dashboard onglet prédiction avec résultat, Swagger `/docs` avec réponse 200, terminal curl, MLflow UI) dans `captures/`. Vérifier micro/caméra/partage d'écran sur un appel test avec quelqu'un.
2. **T-30 min (19h00)** : lancer `cd api && uvicorn main:app --port 8000` (secours local) ; lancer `mlflow ui` ; ouvrir dans l'ordre les onglets navigateur : (1) dashboard HF, (2) `/docs`, (3) `/health`, (4) GitHub repo, (5) `http://127.0.0.1:5000` MLflow ; cliquer « Réveiller l'API » dans le dashboard ; exécuter le curl en ligne dans un terminal et le laisser affiché ; fermer Slack/mails ; ouvrir `captures/` ; ouvrir le PPT en mode présentateur.
3. **Déroulé minuté (10 min)** : tableau `minute | écran | ce que je dis`, démo API en position 2 (après 1 min de contexte), avec pour chaque étape la phrase clé (ex. « Voici le JSON que le dashboard envoie, et voici la réponse brute de l'API : c'est exactement le format demandé dans l'énoncé »).
4. **Échelle de secours** : tableau `panne | symptôme | action` : Space API endormi (→ attendre 15 s, cliquer Réveiller) ; Space API mort (→ URL sidebar `http://127.0.0.1:8000`) ; Space dashboard mort (→ `streamlit run app.py` local) ; partage d'écran mort (→ coller les 3 URLs publiques dans le chat de la visio, demander au jury d'ouvrir `/docs` et de cliquer « Try it out ») ; connexion internet morte (→ partage 4G du téléphone, sinon captures + vidéo).
5. **Phrase d'ouverture** : « Je vais commencer par vous montrer l'API de prédiction en fonctionnement, puisque c'est le cœur du bloc ».

- [ ] **Step 2: Mettre à jour `PREPARE_JURY.md`**

- En tête : encart **« Leçon de la 1re soutenance »** (montrer l'API en premier, jamais en fin ; plan de secours ouvert, voir DEMO_CHECKLIST.md ; grille précédente : Insuffisant sur « qualité des données retournées par l'API », Moyen sur les 3 critères « interface web incluant l'utilisation de l'API »).
- Q3 : réponse `{"prediction":[120.15]}` arrondie ; « le dashboard appelle ce même endpoint depuis l'onglet Estimer un prix ».
- **Q3 bis — Comment le dashboard utilise l'API ?** : `pricing_client.predict` construit `{"input": [[13 valeurs]]}`, fait `requests.post(url + "/predict", json=payload, timeout=60)`, distingue timeout / connexion / HTTP ≠ 200 avec messages clairs ; l'UI affiche prix + JSON envoyé + JSON reçu + curl ; URL configurable (env `GETAROUND_API_URL` ou sidebar).
- **Q3 ter — Que retourne exactement l'API ?** : `/predict` → liste de prix €/jour, un par ligne d'entrée, 2 décimales, format de l'énoncé ; `/health` → statut, type de modèle, 13 features ; erreurs → 422 avec `detail` lisible.
- **Q — Pourquoi `handle_unknown="ignore"` ?** : marque inconnue → vecteur one-hot nul au lieu d'un 500 ; choix de robustesse ; piste : 422 explicite avec valeurs acceptées.
- Q10 : ajouter « 11 tests pytest verts (4 API + 7 client dashboard) ».

- [ ] **Step 3: Commit du .gitignore**

```bash
git add .gitignore
git commit -m "gitignore : DEMO_CHECKLIST.md et captures/"
git push origin main
```

---

### Task 6: PPT de soutenance (python-pptx, liens cliquables)

**Files:**
- Create: `C:/Users/aymer/Desktop/Jedha certification/Jedha/build_getaround_v2.py` (à côté de `build_all_ppts.py`, réutilise `_ppt_helpers.py`)
- Output: `Bloc_5_Getaround/Presentation_Getaround_Soutenance.pptx` (l'ancien `Presentation_Getaround.pptx` est conservé mais n'est plus utilisé)

**Interfaces:**
- Consumes: `_ppt_helpers.py` : `new_prs, blank_slide, add_title_bar, add_text_box, add_notes, add_footer, title_slide, architecture_slide, kpi_slide, two_columns_slide, conclusion_slide, Theme, rgb, WHITE`. Thème : copier `THEME_GETAROUND` de `build_all_ppts.py` (purple `#6A1B9A`, turquoise `#00BFA5`, indigo `#311B92`, success `#00C853`, bg `#F5F2FA`, text `#5A5773`, rounded, bar left).
- Produces: 9 slides 16:9 avec notes orateur, chaque slide portant une barre de liens cliquables.

- [ ] **Step 1: Relever les métriques réelles dans mlruns**

Run :
```bash
cd "C:/Users/aymer/Desktop/Jedha certification/Jedha/Bloc_5_Getaround"
for r in mlruns/345925119498564608/*/; do echo "$r"; cat "$r/metrics/test_rmse" 2>/dev/null; echo; cat "$r/metrics/test_mae" 2>/dev/null; echo; cat "$r/params/regressor__n_estimators" "$r/params/regressor__max_depth" 2>/dev/null; echo; done
PYTHONIOENCODING=utf-8 "$PY" -c "
import pandas as pd
df=pd.read_excel('data/get_around_delay_analysis.xlsx')
n=len(df); late=(df.delay_at_checkout_in_minutes>0).mean()*100
prev=df.set_index('rental_id')['delay_at_checkout_in_minutes']
c=df.dropna(subset=['previous_ended_rental_id']).copy()
c['prev_delay']=c['previous_ended_rental_id'].map(prev)
imp=((c.prev_delay>0)&(c.prev_delay>c.time_delta_with_previous_rental_in_minutes)).mean()*100
print(f'rentals={n} late={late:.1f}% consecutive={len(c)} next_driver_impacted={imp:.1f}%')
"
```
Noter : RMSE test, MAE test, n_estimators, max_depth du run correspondant à `api/.last_run_id` (`e3e9ab4062214642978e94b708dd4316`), et les 4 chiffres dashboard. Ces valeurs remplacent les constantes `RMSE`, `MAE`, `N_RENTALS`, `PCT_LATE`, `N_CONSEC`, `PCT_IMPACTED` du script.

- [ ] **Step 2: Écrire `build_getaround_v2.py`**

```python
"""PPT de soutenance Bloc 5 Getaround (rattrapage) — 9 slides, liens cliquables.

Chaque slide porte une barre de liens cliquables (dashboard, API /docs, GitHub).
Aucune affirmation qui ne soit pas dans le code du repo.

Run :  python build_getaround_v2.py
Out :  Bloc_5_Getaround/Presentation_Getaround_Soutenance.pptx
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

from _ppt_helpers import (
    new_prs, blank_slide, add_title_bar, add_text_box, add_notes, add_footer,
    title_slide, architecture_slide, kpi_slide, two_columns_slide,
    conclusion_slide, Theme, rgb, WHITE, shape_for,
)

AUTHOR = "Aymeric Lahonde — CDSD Jedha 2026 — RNCP35288"
TH = Theme(
    primary=rgb('#6A1B9A'), accent=rgb('#00BFA5'), secondary=rgb('#311B92'),
    success=rgb('#00C853'), bg=rgb('#F5F2FA'), text=rgb('#5A5773'),
    card_bg=WHITE, title_text=WHITE, shape='rounded', bar='left',
)

# --- URLs publiques ---------------------------------------------------------
URL_DASH = "https://alh92500-getaround-dashboard.hf.space"
URL_API = "https://alh92500-getaround-api.hf.space"
URL_DOCS = URL_API + "/docs"
URL_HEALTH = URL_API + "/health"
URL_GITHUB = "https://github.com/aymericlahonde-dotcom/cdsd-b5-getaround"
URL_SPACE_API = "https://huggingface.co/spaces/Alh92500/getaround-api"
URL_SPACE_DASH = "https://huggingface.co/spaces/Alh92500/getaround-dashboard"

# --- Chiffres réels (Task 6 Step 1) — À REMPLACER par les valeurs relevées --
RMSE = "17"        # test_rmse du run e3e9ab40…
MAE = "11"         # test_mae
N_TREES = "200"
MAX_DEPTH = "18"
N_RENTALS = "21 310"
PCT_LATE = "17"
N_CONSEC = "1 841"
PCT_IMPACTED = "9.6"
PRICE_EXAMPLE = "120.15"

LINKS_ALL = [("Dashboard", URL_DASH), ("API /docs", URL_DOCS), ("GitHub", URL_GITHUB)]


def add_links_bar(slide, links, top=Inches(6.55)):
    """Barre de pastilles cliquables (label → URL) en bas de slide."""
    left = Inches(0.5)
    for label, url in links:
        w = Inches(0.25 + 0.11 * len(label))
        pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, Inches(0.38))
        pill.fill.solid()
        pill.fill.fore_color.rgb = TH.accent
        pill.line.fill.background()
        tf = pill.text_frame
        tf.margin_left = tf.margin_right = Inches(0.08)
        tf.margin_top = tf.margin_bottom = Inches(0.02)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "🔗 " + label
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = WHITE
        run.hyperlink.address = url
        pill.click_action.hyperlink.address = url
        left += w + Inches(0.15)


def add_link_line(slide, left, top, width, label, url, size=13):
    """Une ligne de texte 'label : url' où l'URL est cliquable."""
    box = slide.shapes.add_textbox(left, top, width, Inches(0.4))
    p = box.text_frame.paragraphs[0]
    r1 = p.add_run()
    r1.text = label + "  "
    r1.font.size = Pt(size)
    r1.font.bold = True
    r1.font.color.rgb = TH.primary
    r2 = p.add_run()
    r2.text = url
    r2.font.size = Pt(size)
    r2.font.color.rgb = TH.accent
    r2.font.underline = True
    r2.hyperlink.address = url
    return box


def card(slide, left, top, width, height, title, lines, border=None, size=13):
    """Carte blanche avec titre coloré + puces."""
    box = slide.shapes.add_shape(shape_for(TH), left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = TH.card_bg
    box.line.color.rgb = border or TH.primary
    box.line.width = Pt(1.5)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.2)
    tf.margin_top = Inches(0.12)
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(size + 4)
    p.font.bold = True
    p.font.color.rgb = border or TH.primary
    for line in lines:
        p = tf.add_paragraph()
        mono = line.startswith("`")
        p.text = line.strip("`") if mono else "•  " + line
        p.font.size = Pt(size - 1 if mono else size)
        if mono:
            p.font.name = "Consolas"
        p.font.color.rgb = TH.secondary if mono else TH.text
        p.space_before = Pt(3)
    return box


def build():
    prs = new_prs()

    # ---- 1. Titre ---------------------------------------------------------
    title_slide(prs, TH,
        title="Getaround — Delay analysis & Pricing API",
        subtitle="Bloc 5 — Industrialisation & déploiement (Streamlit + MLflow + FastAPI + Docker + HF Spaces)",
        attentes_title="Ce qu'attend Getaround",
        attentes_lines=[
            "Un dashboard pour aider le Product Manager à choisir un délai minimum entre 2 locations",
            "Une API POST /predict qui renvoie un prix journalier à partir de 13 caractéristiques",
            "Une documentation /docs publique et une mise en ligne (HuggingFace Spaces)",
            "Le code sur GitHub, reproductible",
        ],
        author=AUTHOR)
    add_links_bar(prs.slides[-1], LINKS_ALL, top=Inches(6.9))
    add_notes(prs.slides[-1], """[~45 s — INTRO]
Bonjour. Je présente le projet Getaround du Bloc 5 : industrialisation et déploiement.
Getaround, c'est l'Airbnb des voitures : 5 millions d'utilisateurs, 20 000 véhicules.
Deux demandes : un dashboard d'aide à la décision pour le PM, et une API de prédiction de prix.
Je vais commencer par vous montrer l'API de prédiction en fonctionnement, puisque c'est le cœur du bloc, puis le dashboard, puis comment tout est industrialisé.
Les liens en bas de chaque slide sont cliquables.""")

    # ---- 2. Problème → Solution ------------------------------------------
    s = blank_slide(prs, TH)
    add_title_bar(s, prs, TH, "La solution en une slide",
                  "Deux besoins métier → trois livrables en ligne")
    card(s, Inches(0.7), Inches(1.4), Inches(3.9), Inches(4.6), "1. Besoin PM : seuil entre 2 locations", [
        "Retards de checkout → friction pour le client suivant",
        "Un délai minimum réduit les frictions mais coûte du revenu",
        "→ Dashboard Streamlit : simuler seuil × scope",
        "Réponses aux 4 questions du PM",
    ], border=TH.primary)
    card(s, Inches(4.75), Inches(1.4), Inches(3.9), Inches(4.6), "2. Besoin Data Science : pricing", [
        "Suggérer un prix journalier aux propriétaires",
        "→ Modèle Random Forest entraîné et tracké (MLflow)",
        "→ API FastAPI POST /predict, format imposé par l'énoncé",
        "→ Le dashboard appelle cette API (onglet « Estimer un prix »)",
    ], border=TH.accent)
    card(s, Inches(8.8), Inches(1.4), Inches(3.9), Inches(4.6), "3. Industrialisation", [
        "2 images Docker (dashboard, API)",
        "2 Spaces HuggingFace publics",
        "Tests pytest (API + client dashboard)",
        "Script deploy.py, README, code GitHub",
    ], border=TH.secondary)
    add_links_bar(s, [("Dashboard", URL_DASH), ("API /docs", URL_DOCS),
                      ("API /health", URL_HEALTH), ("GitHub", URL_GITHUB)])
    add_notes(s, """[~45 s — SOLUTION]
Deux besoins, trois livrables. Le point important : les deux axes sont reliés, le dashboard consomme l'API de pricing via HTTP. C'est ce que je vous montre tout de suite.""")

    # ---- 3. Vision de l'API ----------------------------------------------
    s = blank_slide(prs, TH)
    add_title_bar(s, prs, TH, "Vision de l'API de pricing",
                  "À quoi elle sert, qui l'appelle, ce qu'elle renvoie")
    boxes = [("Client", "dashboard Streamlit\ncurl / Python requests", TH.primary),
             ("POST /predict", "JSON {\"input\": [[13 valeurs]]}", TH.accent),
             ("Pipeline sklearn", "OneHot + Scaler\n+ RandomForest", TH.secondary),
             ("Réponse JSON", "{\"prediction\": [120.15]}\n€ / jour", TH.success)]
    n = len(boxes); total_w = Inches(12.3); gap = Inches(0.25)
    bw = (total_w - gap * (n - 1)) / n
    for i, (lab, sub, col) in enumerate(boxes):
        left = Inches(0.5) + (bw + gap) * i
        b = s.shapes.add_shape(shape_for(TH), left, Inches(1.5), bw, Inches(1.5))
        b.fill.solid(); b.fill.fore_color.rgb = col; b.line.fill.background()
        tf = b.text_frame; tf.margin_top = Inches(0.1)
        p = tf.paragraphs[0]; p.text = lab; p.font.size = Pt(15); p.font.bold = True
        p.font.color.rgb = WHITE; p.alignment = PP_ALIGN.CENTER
        p2 = tf.add_paragraph(); p2.text = sub; p2.font.size = Pt(11)
        p2.font.color.rgb = WHITE; p2.alignment = PP_ALIGN.CENTER
        if i < n - 1:
            ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, left + bw + Emu(15000),
                                    Inches(2.05), gap - Emu(30000), Inches(0.4))
            ar.fill.solid(); ar.fill.fore_color.rgb = TH.text; ar.line.fill.background()
    card(s, Inches(0.5), Inches(3.3), Inches(6.0), Inches(3.1), "Pourquoi une API ?", [
        "Le modèle est utilisable par n'importe quel client HTTP, sans connaître sklearn",
        "Un seul modèle servi, versionné (joblib exporté depuis le run MLflow)",
        "Contrat d'entrée/sortie documenté automatiquement (OpenAPI /docs)",
        "Découplage : on peut ré-entraîner et redéployer sans toucher aux clients",
    ], border=TH.primary)
    card(s, Inches(6.8), Inches(3.3), Inches(6.0), Inches(3.1), "Qui l'appelle aujourd'hui ?", [
        "Le dashboard Streamlit (onglet « Estimer un prix ») via requests.post",
        "Swagger UI /docs (bouton Try it out) — pour le jury",
        "curl / Python requests — commande de l'énoncé",
        "Les tests pytest (TestClient) à chaque modification",
    ], border=TH.accent)
    add_links_bar(s, [("Dashboard → onglet Estimer un prix", URL_DASH),
                      ("API /docs", URL_DOCS), ("GitHub api/main.py", URL_GITHUB + "/blob/main/api/main.py")])
    add_notes(s, """[~1 min — VISION API]
Le flux : un client envoie un JSON avec 13 valeurs par voiture, l'API applique le pipeline sklearn et renvoie une liste de prix en euros par jour.
Pourquoi une API et pas un notebook : n'importe quel client HTTP peut l'utiliser, le contrat est documenté, et on peut redéployer le modèle sans toucher aux clients.
Trois clients concrets : le dashboard, Swagger, curl.""")

    # ---- 4. Présentation de l'API ----------------------------------------
    s = blank_slide(prs, TH)
    add_title_bar(s, prs, TH, "L'API en détail — endpoints, entrée, sortie",
                  "FastAPI + Pydantic + uvicorn, image Docker, Space HuggingFace")
    card(s, Inches(0.5), Inches(1.4), Inches(6.1), Inches(4.9), "Endpoints livrés", [
        "GET /  — page d'accueil HTML",
        "GET /health  — modèle chargé ? type, 13 features",
        "GET /docs  — Swagger UI (OpenAPI auto-générée)",
        "POST /predict  — prix journalier, 1 ligne = 1 prix",
        "`{\"input\": [[\"Citroen\",140000,100,\"diesel\",\"black\",",
        "`  \"convertible\",true,true,false,false,true,true,true]]}",
        "`→ {\"prediction\": [" + PRICE_EXAMPLE + "]}",
        "Input malformé → 422 avec message explicite",
    ], border=TH.primary, size=13)
    card(s, Inches(6.9), Inches(1.4), Inches(5.9), Inches(4.9), "Modèle servi", [
        f"Pipeline sklearn : OneHotEncoder + StandardScaler + RandomForestRegressor",
        f"{N_TREES} arbres, profondeur max {MAX_DEPTH}, 13 features (4 catégorielles, 2 numériques, 7 booléennes)",
        f"Test (20 %) : RMSE ≈ {RMSE} € / jour, MAE ≈ {MAE} € / jour",
        "Tracké dans MLflow (params, métriques, signature, registry getaround_pricer)",
        "Exporté en model.joblib, embarqué dans l'image Docker, chargé au démarrage",
        "scikit-learn épinglé en 1.8.0 (compatibilité du pickle)",
    ], border=TH.accent, size=13)
    add_link_line(s, Inches(0.5), Inches(6.35), Inches(12.3), "Tester l'API :", URL_DOCS)
    add_links_bar(s, [("Swagger /docs", URL_DOCS), ("/health", URL_HEALTH),
                      ("Space HF API", URL_SPACE_API), ("GitHub", URL_GITHUB)], top=Inches(6.75))
    add_notes(s, """[~1 min 30 — API EN DÉTAIL + DÉMO]
→ DÉMO ICI : j'ouvre /docs, Try it out sur /predict avec l'exemple, réponse 200 avec le prix. Puis /health. Puis le curl dans le terminal.
Quatre endpoints. /predict respecte exactement le format de l'énoncé : une liste de listes en entrée, une liste de prix en sortie.
Le modèle est un pipeline sklearn complet, tracké avec MLflow, exporté en joblib et embarqué dans l'image Docker : l'API n'a aucune dépendance réseau au démarrage.""")

    # ---- 5. Dashboard → onglet prédiction (utilisation de l'API) ---------
    s = blank_slide(prs, TH)
    add_title_bar(s, prs, TH, "Le dashboard utilise l'API",
                  "Onglet « Estimer un prix » : formulaire → requests.post → réponse brute")
    card(s, Inches(0.5), Inches(1.4), Inches(6.1), Inches(4.9), "Ce que voit l'utilisateur", [
        "13 champs : listes déroulantes (marque, carburant, couleur, type), km, puissance, 7 options",
        "Bouton « Appeler l'API /predict »",
        "Prix journalier estimé + temps de réponse",
        "Détails techniques : URL appelée, JSON envoyé, JSON reçu, commande curl équivalente",
        "Bouton « Réveiller / vérifier l'API » (GET /health)",
        "URL de l'API modifiable dans la sidebar (secours local)",
    ], border=TH.primary)
    card(s, Inches(6.9), Inches(1.4), Inches(5.9), Inches(4.9), "Ce qui se passe dans le code", [
        "dashboard/pricing_client.py : build_payload → requests.post(url + '/predict', json=..., timeout=60)",
        "Erreurs gérées : timeout (Space endormi), connexion refusée, HTTP ≠ 200 (detail affiché)",
        "dashboard/pricing_ui.py : formulaire Streamlit + affichage",
        "7 tests pytest sur le client (payload, curl, succès, 422, timeout…)",
        "Aucune dépendance à sklearn côté dashboard : seul l'API connaît le modèle",
    ], border=TH.accent)
    add_link_line(s, Inches(0.5), Inches(6.35), Inches(12.3), "Ouvrir le dashboard :", URL_DASH)
    add_links_bar(s, [("Dashboard", URL_DASH), ("GitHub dashboard/pricing_client.py",
                      URL_GITHUB + "/blob/main/dashboard/pricing_client.py")], top=Inches(6.75))
    add_notes(s, """[~1 min 30 — DÉMO DASHBOARD → API]
→ DÉMO ICI : onglet Estimer un prix, je change la marque et le kilométrage, je clique. Prix affiché. J'ouvre les détails : voilà le JSON envoyé, voilà la réponse brute de l'API, voilà le curl équivalent.
Point clé pour le jury : le dashboard n'embarque pas le modèle, il consomme l'API par HTTP comme n'importe quel client.""")

    # ---- 6. Dashboard analyse des retards -------------------------------
    kpi_slide(prs, TH,
        title="Dashboard — analyse du trade-off seuil × scope",
        subtitle="Réponses aux 4 questions du Product Manager",
        tiles=[(N_RENTALS, "locations analysées", "dataset Delay Analysis"),
               (f"{PCT_LATE} %", "checkouts en retard", "delay > 0 min"),
               (f"{PCT_IMPACTED} %", "clients suivants impactés", f"sur {N_CONSEC} locations consécutives")],
        bottom_lines=[
            "Paramètres interactifs : seuil (0 → 720 min) et scope (toutes / Connect uniquement)",
            "Q1 part du revenu impactée · Q2 locations bloquées · Q3 fréquence/amplitude des retards · Q4 cas résolus",
            "Courbe de trade-off : % de cas résolus vs % de revenu impacté selon le seuil",
            "Recommandation : 60 à 90 min sur les voitures Connect (mesure applicable techniquement)",
        ])
    add_links_bar(prs.slides[-1], [("Dashboard → onglet Analyse des retards", URL_DASH),
                                   ("Space HF dashboard", URL_SPACE_DASH)])
    add_notes(prs.slides[-1], f"""[~1 min — DASHBOARD ANALYSE]
{N_RENTALS} locations, {PCT_LATE} % de checkouts en retard, {PCT_IMPACTED} % des locations consécutives où le client suivant est impacté.
Le PM règle le seuil et le scope, et lit en direct : revenu impacté, locations bloquées, cas résolus. La courbe de trade-off montre le sweet spot vers 60-90 min sur Connect.""")

    # ---- 7. Industrialisation : MLflow + Docker + déploiement -----------
    architecture_slide(prs, TH,
        title="Industrialisation — de l'entraînement au Space",
        subtitle="MLflow → joblib → Docker → HuggingFace Spaces → tests",
        boxes=[
            ("Training", "01_train_pricing.py\nargparse + autolog", 'primary'),
            ("MLflow", "params, métriques,\nsignature, registry", 'secondary'),
            ("model.joblib", "pipeline exporté,\nembarqué dans l'image", 'accent'),
            ("Docker", "python:3.11-slim\nuser non-root, port 7860", 'secondary'),
            ("HF Spaces", "2 Spaces Docker\ndeploy.py (huggingface_hub)", 'success'),
        ],
        left_lines=[
            "Reproductible en 3 commandes",
            "python notebooks/01_train_pricing.py --n_estimators 200 --max_depth 18",
            "cd api && uvicorn main:app          → /docs local",
            "python deploy.py                    → pousse api/ et dashboard/",
        ],
        right_lines=[
            "Qualité",
            "11 tests pytest : 4 sur l'API (TestClient), 7 sur le client dashboard",
            "Validation Pydantic + 422 explicites sur input malformé",
            "Choix assumé : modèle embarqué (un Space MLflow gratuit perd ses artifacts au redémarrage)",
        ])
    add_links_bar(prs.slides[-1], [("GitHub", URL_GITHUB),
                                   ("Dockerfile API", URL_GITHUB + "/blob/main/api/Dockerfile"),
                                   ("Training script", URL_GITHUB + "/blob/main/notebooks/01_train_pricing.py")])
    add_notes(prs.slides[-1], """[~1 min 15 — INDUSTRIALISATION]
Le script d'entraînement prend ses hyperparamètres en ligne de commande, logue tout dans MLflow (autolog + signature + registry) et exporte le pipeline en joblib.
L'image Docker de l'API embarque ce joblib : aucune dépendance réseau au boot. J'avais d'abord chargé le modèle depuis un serveur MLflow sur HF Spaces : sans stockage persistant, les artifacts disparaissaient au redémarrage et l'API crashait. D'où ce choix.
→ Si le temps le permet : montrer mlflow ui en local avec les runs.""")

    # ---- 8. Démo & plan de secours --------------------------------------
    two_columns_slide(prs, TH,
        title="Démo live — parcours et plan de secours",
        subtitle="Tout est public : le jury peut rejouer chaque étape",
        left_title="Parcours de démo (dans cet ordre)",
        left_lines=[
            "1.  Dashboard → onglet Estimer un prix → Appeler l'API",
            "    → prix + JSON envoyé / reçu + curl",
            "2.  Swagger /docs → Try it out sur /predict",
            "3.  /health dans le navigateur",
            "4.  curl POST /predict dans le terminal",
            "5.  Dashboard → onglet Analyse des retards (seuil, scope)",
            "6.  GitHub : README, Dockerfiles, tests",
        ],
        right_title="Si quelque chose tombe",
        right_lines=[
            "Space endormi → 15 s, bouton « Réveiller l'API »",
            "Space API mort → URL sidebar = http://127.0.0.1:8000 (uvicorn local)",
            "Partage d'écran mort → le jury ouvre lui-même /docs (Try it out)",
            "    → liens cliquables sur chaque slide",
            "Connexion morte → captures d'écran + vidéo enregistrée",
        ])
    add_links_bar(prs.slides[-1], [("Dashboard", URL_DASH), ("API /docs", URL_DOCS),
                                   ("API /health", URL_HEALTH), ("GitHub", URL_GITHUB)])
    add_notes(prs.slides[-1], """[~30 s — DÉMO / SECOURS]
Si la démo a déjà été faite aux slides 4 et 5, cette slide sert de récapitulatif et de filet de sécurité : tous les liens sont cliquables, le jury peut tester lui-même.""")

    # ---- 9. Conclusion ---------------------------------------------------
    conclusion_slide(prs, TH,
        title="Conclusion & perspectives",
        subtitle="Bloc 5 — un modèle industrialisé et accessible par une interface web",
        acquis_lines=[
            "API FastAPI /predict en ligne, documentée (/docs), testée (pytest)",
            "Dashboard Streamlit qui consomme l'API (onglet Estimer un prix)",
            "Modèle tracké MLflow, exporté joblib, embarqué dans Docker",
            "2 Spaces HuggingFace publics + script de déploiement",
            "Code GitHub reproductible (README, requirements, Dockerfiles)",
        ],
        prod_lines=[
            "CI/CD GitHub Actions : tests + build + deploy automatiques",
            "Stockage d'artifacts persistant (S3) pour un MLflow distant",
            "422 explicite sur valeur catégorielle inconnue (liste des valeurs acceptées)",
            "Authentification (API key) et logs structurés sur /predict",
            "Comparer GradientBoosting / XGBoost, tuning par validation croisée",
            "Monitoring de dérive des prix et ré-entraînement planifié",
        ])
    add_links_bar(prs.slides[-1], LINKS_ALL, top=Inches(6.3))
    add_notes(prs.slides[-1], """[~30 s — CONCLUSION]
Ce que le bloc demande est en place : un modèle industrialisé, servi par une API documentée et testée, et accessible par une interface web qui l'utilise réellement.
Pistes : CI/CD, stockage persistant pour MLflow, validation plus stricte des entrées, auth, meilleurs modèles.
Merci, je suis prêt pour vos questions — et pour refaire n'importe quelle étape de la démo.""")

    total = len(prs.slides)
    for i, sl in enumerate(prs.slides, start=1):
        add_footer(sl, prs, TH, i, total, f"{AUTHOR}  ·  Bloc 5 Getaround")
    out = os.path.join("Bloc_5_Getaround", "Presentation_Getaround_Soutenance.pptx")
    prs.save(out)
    print(f"OK -> {out} ({total} slides)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()
```

- [ ] **Step 3: Générer et vérifier le PPT**

Run : `cd "C:/Users/aymer/Desktop/Jedha certification/Jedha" && PYTHONIOENCODING=utf-8 "$PY" build_getaround_v2.py`
Expected : `OK -> Bloc_5_Getaround/Presentation_Getaround_Soutenance.pptx (9 slides)`.

Vérification des liens :
```bash
PYTHONIOENCODING=utf-8 "$PY" -c "
from pptx import Presentation
p=Presentation('Bloc_5_Getaround/Presentation_Getaround_Soutenance.pptx')
for i,s in enumerate(p.slides,1):
    links=set()
    for sh in s.shapes:
        if sh.has_text_frame:
            for par in sh.text_frame.paragraphs:
                for r in par.runs:
                    if r.hyperlink.address: links.add(r.hyperlink.address)
    print(i, len(links), sorted(links))
"
```
Expected : chaque slide a ≥ 2 liens, toutes les URLs commencent par `https://`.

Ouvrir le fichier dans PowerPoint, vérifier visuellement : pas de texte qui déborde des cartes (réduire `size` de la carte si besoin), pastilles de liens lisibles, notes orateur présentes. Faire une capture de la slide 4 pour `captures/`.

- [ ] **Step 4: Copier le PPT dans le dossier de travail de l'examen**

Run : `cp "C:/Users/aymer/Desktop/Jedha certification/Jedha/Bloc_5_Getaround/Presentation_Getaround_Soutenance.pptx" "C:/Users/aymer/Desktop/Jedha certification/Bloc 5 - a revoir pour examen/"`

Le PPT n'est pas commité dans le repo GitHub (fichier binaire de présentation, pas de code) : ajouter `Presentation_Getaround_Soutenance.pptx` à `.gitignore` si `git status` le montre comme non suivi… **Non** : l'ancien `Presentation_Getaround.pptx` est déjà suivi dans le repo, on suit le même usage et on commite le nouveau :

```bash
cd "C:/Users/aymer/Desktop/Jedha certification/Jedha/Bloc_5_Getaround"
git add Presentation_Getaround_Soutenance.pptx
git commit -m "PPT de soutenance (rattrapage) : liens cliquables, slides solution / vision API / API"
git push origin main
```
