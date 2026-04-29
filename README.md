# Bloc 5 — Getaround (MLOps complet)

> Projet de la **Certification Jedha — Concepteur Développeur en Science des Données (CDSD)**
> [RNCP35288 — France Compétences](https://www.francecompetences.fr/recherche/rncp/35288/)
> **Bloc 5** : Industrialisation d'un algorithme et automatisation des processus — MLOps

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
│   ├── 01_getaround_delay_analysis.ipynb     (axe 1 — analyse délais)
│   └── 02_getaround_pricing_ml.ipynb         (axe 2 — training ML + MLflow)
├── dashboard/
│   ├── app.py                                (app Streamlit)
│   ├── Dockerfile                            (image Streamlit)
│   └── requirements.txt
├── api/
│   ├── main.py                               (FastAPI app)
│   ├── Dockerfile                            (image API)
│   └── requirements.txt
├── data/                                     (à télécharger depuis Julie Jedha, gitignored)
├── mlruns/                                   (MLflow runs, gitignored)
└── README.md
```

## Comment rejouer le projet en local

```bash
cd Bloc_5_Getaround
pip install -r requirements.txt

# 1. Training MLflow
jupyter lab notebooks/02_getaround_pricing_ml.ipynb

# 2. Dashboard Streamlit
cd dashboard
streamlit run app.py
# → http://localhost:8501

# 3. API FastAPI
cd ../api
uvicorn main:app --reload
# → http://localhost:8000/docs
```

## Déploiement HuggingFace Spaces

Pour le dashboard : créer un Space "Streamlit" et y pousser le contenu de `dashboard/`.
Pour l'API : créer un Space "Docker" et y pousser le contenu de `api/`.

## Auteur

[Aymeric Lahonde](https://github.com/aymericlahonde-dotcom) — promotion Jedha CDSD 2026.
