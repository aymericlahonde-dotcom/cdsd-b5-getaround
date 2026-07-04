# Bloc 5 — Getaround (MLOps complet)

> Projet de la **Certification Jedha — Concepteur Développeur en Science des Données (CDSD)**
> [RNCP35288 — France Compétences](https://www.francecompetences.fr/recherche/rncp/35288/)
> **Bloc 5** : Industrialisation d'un algorithme et automatisation des processus — MLOps

## Livrables en ligne

| Livrable | URL |
|---|---|
| Dashboard Streamlit (analyse délais) | <https://huggingface.co/spaces/Alh92500/getaround-dashboard> |
| API FastAPI de pricing (`/predict` + `/docs`) | <https://huggingface.co/spaces/Alh92500/getaround-api> |
| Repository GitHub | <https://github.com/aymericlahonde-dotcom/cdsd-b5-getaround> |

## Objectif du projet

Getaround = "Airbnb pour les voitures" — 5M utilisateurs, 20K voitures dans le monde. Le projet a **2 axes** :

### Axe 1 — Dashboard Data Analysis

Les retours en retard de location génèrent des frictions pour le client suivant. Getaround envisage d'imposer un **délai minimum entre 2 locations** pour la même voiture. Mais ce délai a un coût (revenu perdu). On veut aider le Product Manager à choisir le bon trade-off en répondant à :

- Quelle part du revenu serait impactée par la mesure ?
- Combien de locations seraient affectées selon le seuil et le scope (toutes les voitures ? Connect uniquement ?) ?
- À quelle fréquence les drivers sont en retard ? Avec quel impact sur la location suivante ?
- Combien de cas problématiques résolus selon le seuil ?

→ Livrable : **dashboard Streamlit en ligne**.

### Axe 2 — API ML pour pricing

L'équipe Data Science travaille en parallèle sur l'optimisation du prix des locations. Ils ont préparé un dataset et veulent un modèle de prédiction de prix accessible via une API.

→ Livrable : **API FastAPI avec endpoint `/predict`** + documentation `/docs`, déployée en ligne (HuggingFace Spaces).

## Données

2 datasets à télécharger depuis Julie Jedha :
- **Delay Analysis** (Excel) → axe 1 dashboard
- **Pricing Optimization** (CSV) → axe 2 ML

Lien : <https://app.jedha.co/course/project-deployment-ft/getaround-analysis-ft>

À placer dans `data/` :
- `data/get_around_delay_analysis.xlsx`
- `data/get_around_pricing_project.csv`

## Stack technique

| Composant | Tech |
|---|---|
| Dashboard | Streamlit |
| ML tracking | MLflow (modèles + métriques + artifacts) |
| API | FastAPI + Uvicorn |
| Conteneurisation | Docker |
| Hosting | HuggingFace Spaces |

## Livrables

1. **Dashboard Streamlit** déployé en ligne (URL publique)
2. **Repository GitHub** (ce repo) avec tout le code
3. **API FastAPI** déployée avec endpoint `/predict` documenté

## Structure du projet

```
Bloc_5_Getaround/
├── notebooks/
│   └── 01_train_pricing.py                   (axe 2 — training ML + tracking MLflow, export model.joblib)
├── dashboard/                                (axe 1 — analyse des délais)
│   ├── app.py                                (app Streamlit + questions du Product Manager)
│   ├── Dockerfile                            (image Streamlit)
│   ├── README.md                             (card HF Space)
│   └── requirements.txt
├── api/                                       (axe 2 — API de pricing)
│   ├── main.py                               (FastAPI app, charge model.joblib en local)
│   ├── model.joblib                          (pipeline sklearn embarqué, ~28 Mo)
│   ├── Dockerfile                            (image API)
│   ├── README.md                             (card HF Space)
│   └── requirements.txt
├── mlflow-server/                            (image Docker d'un serveur MLflow pour HF Spaces)
│   ├── Dockerfile
│   ├── start.sh
│   └── README.md
├── data/                                     (datasets Jedha, gitignored)
├── mlruns/                                   (MLflow runs locaux, gitignored)
├── requirements.txt                          (env de dev complet)
└── README.md
```

> Note : l'analyse des délais (axe 1) vit directement dans `dashboard/app.py`
> (chargement de l'Excel + calculs + visualisations Streamlit), il n'y a donc
> pas de notebook `.ipynb` séparé pour cet axe. Le training ML (axe 2) est un
> script Python exécutable (`notebooks/01_train_pricing.py`) plutôt qu'un
> notebook, pour être rejouable en une commande.

## Comment rejouer le projet en local

```bash
cd Bloc_5_Getaround
pip install -r requirements.txt

# 1. Training + tracking MLflow (génère aussi api/model.joblib)
python notebooks/01_train_pricing.py --n_estimators 200 --max_depth 18
mlflow ui        # http://127.0.0.1:5000 pour visualiser runs/metrics

# 2. Dashboard Streamlit
cd dashboard
streamlit run app.py
# → http://localhost:8501

# 3. API FastAPI (charge api/model.joblib en local)
cd ../api
uvicorn main:app --reload
# → http://localhost:8000/docs
```

## Déploiement HuggingFace Spaces

Les deux livrables sont déployés en Spaces Docker :

- **Dashboard** : Space Docker à partir de `dashboard/`.
- **API** : Space Docker à partir de `api/`. Le modèle `model.joblib` est
  embarqué dans le dossier et chargé en local au démarrage — l'API est
  autonome, sans dépendance à un serveur MLflow distant.

Push via `huggingface_hub` :

```python
from huggingface_hub import HfApi
HfApi().upload_folder(folder_path="api", repo_id="Alh92500/getaround-api",
                      repo_type="space", token="<HF_TOKEN>")
```

## Auteur

[Aymeric Lahonde](https://github.com/aymericlahonde-dotcom) — promotion Jedha CDSD 2026.
