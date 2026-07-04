FROM ghcr.io/mlflow/mlflow:v3.5.0

# Setup A : pas de S3 ni Postgres - tout en local au container.
# Si tu veux passer en Setup B (S3 + Postgres), decommente la ligne ci-dessous :
# RUN pip install boto3 psycopg2-binary

# Persistance locale du backend SQLite + artifacts (perdu au restart si pas de Persistent Storage HF)
RUN mkdir -p /mlflow/artifacts && chmod -R 777 /mlflow

# Port standard HF Spaces
EXPOSE 7860

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
