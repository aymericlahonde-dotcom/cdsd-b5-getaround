FROM python:3.11-slim

# HF Spaces — l'app tourne en utilisateur "user" (uid 1000), pas root
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# Installation des dépendances Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copie du code et du modèle
# NB : model.pkl doit être présent dans ce dossier avant le build.
#      Il est généré par notebooks/02_getaround_pricing_ml.ipynb (training MLflow).
COPY --chown=user:user main.py .
COPY --chown=user:user model.pkl .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
