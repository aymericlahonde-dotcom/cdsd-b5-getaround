---
title: Getaround MLflow
emoji: 🪄
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Getaround MLflow Server

Serveur MLflow déployé sur HuggingFace Spaces pour le projet Bloc 5 Jedha.

**Setup A (par défaut)** — tout en local au container, pas de dépendance externe :
- **Backend store** : SQLite dans `/mlflow/mlflow.db`
- **Artifact root** : `/mlflow/artifacts` (filesystem du container)
- **`--serve-artifacts`** : le serveur proxie les artefacts → l'API et le training
  ne connaissent que `MLFLOW_TRACKING_URI`, pas besoin de credentials AWS
- **Port** : 7860 (standard HF Spaces)

## Aucun secret à configurer en Setup A

Tu peux push directement le Space, il tourne tel quel.

## Déploiement HF Spaces (3 commandes)

```bash
# 1. Créer le Space (UI HuggingFace) : Alh92500/getaround-mlflow, sdk Docker
#    https://huggingface.co/new-space

# 2. Push depuis ce dossier
cd Bloc_5_Getaround/mlflow-server
git init -b main
git remote add hf https://huggingface.co/spaces/Alh92500/getaround-mlflow
git add Dockerfile start.sh README.md
git commit -m "deploy mlflow server (setup A)"

# 3. Authentification HF + push (utilise ton HF_TOKEN regénéré)
git push hf main
# Username: Alh92500
# Password: <colle ton HF_TOKEN>
```

URL du serveur : **https://alh92500-getaround-mlflow.hf.space**

## Test local avant push

```bash
docker build -t getaround-mlflow .
docker run -p 7860:7860 getaround-mlflow
open http://localhost:7860
```

## ⚠️ Limites Setup A

- **Éphémère** : les runs et les artefacts sont perdus au restart du Space
  (HF Spaces gratuit n'a pas de Persistent Storage)
- Workaround pour le jury : re-train juste avant la démo, le Space reste warm
- Le tracking server lui-même reste up entre les restarts, c'est le contenu qui est perdu

## Upgrade vers Setup B (artefacts persistants sur S3)

Si tu veux passer à un setup pro avec persistance :

1. **Créer un bucket S3** :
   ```bash
   aws s3 mb s3://alh92500-mlflow-artifacts --region eu-west-3
   ```

2. **Créer un user IAM dédié** avec policy minimale (`s3:PutObject`, `s3:GetObject`,
   `s3:ListBucket` sur ce bucket uniquement)

3. **Décommenter** dans `Dockerfile` :
   ```dockerfile
   RUN pip install boto3 psycopg2-binary
   ```

4. **Remplacer `start.sh`** par :
   ```bash
   export AWS_ACCESS_KEY_ID=${AWSKEY}
   export AWS_SECRET_ACCESS_KEY=${AWSSECRET}
   export AWS_DEFAULT_REGION=${AWSREGION}

   mlflow server --host 0.0.0.0 --port 7860 \
     --backend-store-uri sqlite:///mlflow/mlflow.db \
     --default-artifact-root s3://alh92500-mlflow-artifacts \
     --serve-artifacts --disable-security-middleware
   ```

5. **Configurer 3 Secrets HF Spaces** (Settings → Variables and secrets) :
   `AWSKEY`, `AWSSECRET`, `AWSREGION=eu-west-3`

6. Push à nouveau.

Aligned sur le pattern Jedha `2026-04-01_Serve_Your_Model_with_API/exercices/mlflow-server/`.
