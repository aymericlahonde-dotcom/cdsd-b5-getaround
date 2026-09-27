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
IGNORE = ["__pycache__/*", "test_*.py", ".last_run_id", "*.pyc", ".pytest_cache/*", "*.xlsx"]

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
