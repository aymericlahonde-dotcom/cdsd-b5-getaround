# Dossier projet — Bloc 5 Getaround (MLOps)

**Certification Jedha CDSD — RNCP35288**
**Bloc 5 : Industrialisation d'un algorithme de machine learning et automatisation des processus de décision**
Auteur : Aymeric Lahonde — promotion CDSD 2026

---

## 1. Contexte et problématique

Getaround est une marketplace de location de voitures entre particuliers
(« Airbnb de la voiture »), avec ~5M d'utilisateurs et ~20K voitures. Deux
problèmes métier sont adressés dans ce projet :

1. **Retards au checkout** — quand un conducteur rend la voiture en retard, le
   client suivant peut être impacté (attente, voire annulation). Getaround
   envisage d'imposer un **délai minimum entre deux locations** pour la même
   voiture. Ce délai réduit les frictions mais fait perdre du chiffre
   d'affaires. Il faut aider le Product Manager à arbitrer.
2. **Optimisation du prix** — l'équipe Data Science veut mettre à disposition un
   modèle de prédiction du prix journalier de location, servi via une API.

## 2. Livrables

| Livrable | Nature | URL |
|---|---|---|
| Dashboard d'analyse des délais | Streamlit / Docker / HF Spaces | https://huggingface.co/spaces/Alh92500/getaround-dashboard |
| API de pricing | FastAPI / Docker / HF Spaces | https://huggingface.co/spaces/Alh92500/getaround-api |
| Code source | Repository GitHub | https://github.com/aymericlahonde-dotcom/cdsd-b5-getaround |

## 3. Données

- `get_around_delay_analysis.xlsx` — historique des locations avec retards au
  checkout et délai avant la location suivante (axe 1).
- `get_around_pricing_project.csv` — ~4800 voitures décrites par 13 features
  techniques + prix journalier cible (axe 2).

Datasets fournis par Jedha, stockés dans `data/` (gitignored).

## 4. Axe 1 — Dashboard d'analyse des délais

Application **Streamlit** (`dashboard/app.py`). L'utilisateur règle dans la
sidebar :
- le **seuil minimum** entre deux locations (minutes) ;
- le **scope** : toutes les voitures ou uniquement celles équipées de Getaround
  **Connect** (déverrouillage à distance).

Le dashboard répond aux 4 questions du Product Manager :
1. Part du chiffre d'affaires impactée par la mesure.
2. Nombre de locations affectées selon seuil et scope.
3. Fréquence des retards et impact sur la location suivante.
4. Nombre de cas problématiques (chevauchements) résolus selon le seuil.

Conteneurisé (Docker) et déployé sur HuggingFace Spaces.

## 5. Axe 2 — Modèle de pricing + tracking MLflow

Script `notebooks/01_train_pricing.py` :

- **Preprocessing** via `ColumnTransformer` :
  - `OneHotEncoder(handle_unknown="ignore")` sur les variables catégorielles
    (`model_key`, `fuel`, `paint_color`, `car_type`) ;
  - `StandardScaler` sur les variables numériques (`mileage`, `engine_power`) ;
  - `passthrough` sur les 7 variables booléennes.
- **Modèle** : `RandomForestRegressor` (n_estimators=200, max_depth=18,
  min_samples_leaf=2), assemblé avec le preprocessing dans un `Pipeline` unique.
- **Tracking MLflow** : `mlflow.sklearn.autolog(log_models=False)` pour les
  params/metrics, puis `log_model(..., registered_model_name="getaround_pricer",
  signature=...)` pour versionner le modèle dans le Model Registry.
- **Métriques holdout** (test 20 %) : **RMSE ≈ 17 €/jour**, **MAE ≈ 11 €/jour**.
- **Export** : le pipeline complet est sérialisé dans `api/model.joblib` pour
  être embarqué dans l'API.

## 6. Axe 2 — API de pricing (FastAPI)

`api/main.py` — application **FastAPI** servie par **uvicorn** :

- `GET /` — page d'accueil HTML ;
- `GET /docs` — documentation OpenAPI interactive (Swagger UI) ;
- `POST /predict` — prédiction du prix journalier pour une ou plusieurs voitures.

Format d'entrée imposé par l'énoncé :
`{"input": [[model_key, mileage, engine_power, fuel, paint_color, car_type,
private_parking_available, has_gps, has_air_conditioning, automatic_car,
has_getaround_connect, has_speed_regulator, winter_tires], ...]}`.
Sortie : `{"prediction": [120.15, ...]}`. Validation via Pydantic (nombre de
valeurs par ligne, conversion des booléens).

### Chargement du modèle — décision d'architecture

Le modèle (`api/model.joblib`) est **embarqué dans l'image Docker** et chargé
en **local** au démarrage (`joblib.load`). L'API est donc **autonome** :

> Auparavant, l'API chargeait le modèle depuis un serveur MLflow distant
> (`mlflow.pyfunc.load_model("runs:/<run_id>/...")`). Sur HF Spaces gratuit ce
> serveur est éphémère (pas de stockage persistant) : au moindre restart les
> runs disparaissaient et l'API **crashait au boot** (RUNTIME_ERROR). Embarquer
> le modèle supprime cette dépendance externe et fiabilise le déploiement.

## 7. Conteneurisation et déploiement

- Chaque service a son `Dockerfile` (dashboard, API, serveur MLflow optionnel).
- Images basées sur `python:3.11-slim`, exécutées en utilisateur non-root
  (uid 1000) comme l'exige HF Spaces, exposées sur le port 7860.
- Déploiement sur **HuggingFace Spaces** (SDK Docker) via `huggingface_hub`
  (`HfApi().upload_folder`).

## 8. Stack technique

| Composant | Technologie |
|---|---|
| Analyse / dashboard | Streamlit, pandas, plotly, openpyxl |
| ML | scikit-learn (Pipeline + RandomForest) |
| Tracking / registry | MLflow |
| API | FastAPI, uvicorn, Pydantic |
| Sérialisation modèle | joblib |
| Conteneurisation | Docker |
| Hébergement | HuggingFace Spaces |

## 9. Reproduire en local

```bash
cd Bloc_5_Getaround
pip install -r requirements.txt

python notebooks/01_train_pricing.py --n_estimators 200 --max_depth 18   # train + model.joblib
cd dashboard && streamlit run app.py            # http://localhost:8501
cd ../api && uvicorn main:app --reload          # http://localhost:8000/docs
```
