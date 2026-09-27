# Spec — Volet prédiction dans le dashboard + fiabilisation de la démo API

Date : 2026-09-27
Contexte : rattrapage oral du Bloc 5 (CDSD Jedha) le mercredi 2026-09-30 à 19h30.
Grille précédente : « Insuffisant » sur la qualité des données retournées par
l'API, « Moyen » sur les 3 critères « interface web incluant l'utilisation de
l'API ». Commentaire jury : panne de partage d'écran, API non vérifiée.

## Objectif

1. Rendre l'API `/predict` **visible et utilisable depuis le dashboard
   Streamlit** (formulaire → appel HTTP → affichage de la réponse).
2. Rendre la démo **robuste** : plan de secours en cas de panne réseau ou de
   Space HuggingFace endormi.
3. Ne pas toucher au modèle ML ni à l'architecture de déploiement (Spaces
   Docker), qui fonctionnent.

## Hors périmètre (volontairement)

Refonte du modèle, comparaison d'algorithmes, CI/CD, monitoring, auth API,
linter exhaustif. Ces points restent dans la section « limites et pistes » de
l'oral.

## Composant 1 — Dashboard : onglet « Estimer un prix »

Fichier : `dashboard/app.py`.

- Le dashboard passe en **deux onglets** (`st.tabs`) :
  « 📊 Analyse des retards » (contenu actuel, inchangé) et
  « 💰 Estimer un prix (API) ».
- L'onglet prédiction contient :
  - un formulaire avec les **13 features** dans l'ordre imposé par l'énoncé.
    Catégorielles (`model_key`, `fuel`, `paint_color`, `car_type`) en listes
    déroulantes dont les valeurs sont **codées en dur** dans une constante
    (extraites une fois du dataset pricing), pour ne pas dépendre du CSV
    au runtime. Numériques (`mileage`, `engine_power`) en `number_input`.
    Les 7 booléens en cases à cocher. Valeurs par défaut = l'exemple Citroën
    de l'énoncé (140000 km, 100 ch, diesel, noir, convertible).
  - un bouton « Appeler l'API `/predict` ».
  - après appel : le **prix estimé** en `st.metric` (€/jour), puis un
    expander « Détails techniques » montrant (a) l'URL appelée, (b) le JSON
    envoyé, (c) le JSON brut reçu, (d) la commande `curl` équivalente,
    (e) la latence mesurée.
  - un encart « État de l'API » avec un bouton « Réveiller / vérifier l'API »
    qui appelle `GET /health` et affiche le statut (utile à T-5 min).
- **Configuration** : constante `API_URL` lue depuis la variable
  d'environnement `GETAROUND_API_URL`, défaut
  `https://alh92500-getaround-api.hf.space`. Un champ texte dans la sidebar
  permet de la changer en direct (bascule vers `http://127.0.0.1:8000` si le
  Space est injoignable pendant la démo).
- **Erreurs** : `requests.post` avec `timeout=60` (cold start HF ≈ 15 s).
  Trois cas distingués et affichés en `st.error` avec un message en clair :
  timeout / connexion refusée, code HTTP ≠ 200 (afficher le `detail`
  renvoyé par FastAPI), réponse sans clé `prediction`.
- `requests` ajouté explicitement dans `dashboard/requirements.txt`.

## Composant 2 — API : santé et lisibilité de la réponse

Fichier : `api/main.py`.

- `POST /predict` : **format inchangé** (`{"prediction": [...]}`, imposé par
  l'énoncé). Les prix sont arrondis à 2 décimales.
- Nouveau `GET /health` : `{"status": "ok", "model_loaded": true,
  "model_type": "<classe du regressor>", "n_features": 13,
  "features": [...]}`. Sert au bouton « Réveiller » du dashboard et donne au
  jury une réponse lisible sur « que retourne l'API ».
- Validation existante conservée (422 si mauvais nombre de valeurs).
  Ajout : 422 avec message clair si une valeur catégorielle est inconnue ?
  **Non** : le pipeline utilise `handle_unknown="ignore"`, on laisse passer,
  c'est un choix assumé et expliqué à l'oral.
- Docstring, description OpenAPI et page d'accueil mises à jour pour lister
  `/health`.

## Composant 3 — Tests API

Fichier : `api/test_main.py` (pytest + `fastapi.testclient`).

Trois tests : `/health` renvoie 200 et `model_loaded` vrai ; `/predict` avec
l'exemple Citroën renvoie 200, une liste d'un flottant positif ; `/predict`
avec une ligne de 12 valeurs renvoie 422. `pytest` ajouté au
`requirements.txt` racine (pas dans l'image Docker de l'API).

## Composant 4 — Déploiement

- Redéploiement des deux Spaces via `huggingface_hub.upload_folder` avec le
  token du `.env` (script `deploy.py` à la racine, lit `HF_TOKEN` et
  `HF_USERNAME`, pousse `api/` puis `dashboard/`).
- Vérification post-déploiement : `GET /health`, `POST /predict`, ouverture
  du dashboard et appel réel depuis l'onglet prédiction.
- Commit + push GitHub (`origin/main`).

## Composant 5 — Kit de soutenance

Fichier : `PREPARE_JURY.md` (mis à jour, reste gitignored) et nouveau
`DEMO_CHECKLIST.md` (gitignored aussi).

- **Déroulé minuté** (~10 min) : contexte 1 min → **démo API en premier**
  (dashboard onglet prédiction, puis Swagger `/docs` « Try it out », puis
  `curl`) 4 min → dashboard analyse retards 2 min → MLflow + Docker + choix
  d'architecture 2 min → limites 1 min.
- **Checklist T-30 min** : ouvrir les 5 onglets navigateur dans l'ordre,
  réveiller les deux Spaces (bouton « Réveiller » + curl), lancer l'API en
  local sur le port 8000 en secours, ouvrir un terminal avec la commande
  curl déjà tapée, préparer les captures d'écran.
- **Échelle de secours** si panne : Space API mort → basculer l'URL du
  dashboard vers `http://127.0.0.1:8000` ; partage d'écran mort → envoyer les
  URLs publiques dans le chat de la visio et demander au jury d'ouvrir
  `/docs` lui-même ; connexion morte → captures d'écran + vidéo enregistrée
  la veille.
- Réponses aux questions probables : « que retourne l'API ? », « pourquoi
  handle_unknown=ignore ? », « comment le dashboard appelle l'API ? ».

## Critères de réussite

- En local : `streamlit run dashboard/app.py` → onglet prédiction → clic →
  prix affiché, JSON brut visible, en < 2 s avec l'API locale.
- En ligne : même parcours sur le Space dashboard vers le Space API.
- `pytest api/` : 3 tests verts.
- Le déroulé de démo a été répété une fois de bout en bout avant mercredi.
