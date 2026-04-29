FROM python:3.11-slim

# HF Spaces — l'app tourne en utilisateur "user" (uid 1000), pas root
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# Installation des dépendances Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copie du code de l'app
COPY --chown=user:user app.py .

# Le dataset est téléchargé au runtime depuis Jedha S3 (cf. app.py)
# - pas besoin de l'embarquer dans l'image (plus léger + reproductible)

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
