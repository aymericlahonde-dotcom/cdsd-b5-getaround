FROM python:3.11-slim

# HF Spaces - l'app tourne en utilisateur "user" (uid 1000), pas root
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# Installation des dependances Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copie du code de l'API + du modele embarque
COPY --chown=user:user main.py .
COPY --chown=user:user model.joblib .

# Le modele est charge en LOCAL au demarrage (joblib.load).
# Aucune dependance a un serveur MLflow distant -> l'API ne crashe plus au boot.

# HF Spaces standard : port 7860 (pas 8000 comme en local)
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
