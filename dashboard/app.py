"""Dashboard Streamlit Getaround — Bloc 5 Jedha CDSD.

Deux onglets :
1. Analyse des retards de checkout (4 questions du Product Manager).
2. Estimation de prix : formulaire qui appelle l'API FastAPI /predict.

Usage local :
    streamlit run app.py
    GETAROUND_API_URL=http://127.0.0.1:8000 streamlit run app.py   # API locale

Déploiement HuggingFace Spaces (Docker) : voir Dockerfile.
"""
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

import delay_analysis
import pricing_ui
from pricing_client import DEFAULT_API_URL

st.set_page_config(
    page_title="Getaround - Delay Analysis & Pricing",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Getaround — Analyse des retards & estimation de prix")
st.caption(
    "Dashboard interactif : aide au choix d'un seuil minimum entre 2 locations, "
    "et appel de l'API de pricing. Bloc 5 Jedha CDSD — Aymeric Lahonde."
)

# ============================================================
# Chargement dataset (cache + fallback URL si fichier local absent)
# ============================================================
DATASET_URL = "https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx"
HERE = Path(__file__).parent
LOCAL_CANDIDATES = [
    HERE / "get_around_delay_analysis.xlsx",                 # bundle Docker
    HERE.parent / "data" / "get_around_delay_analysis.xlsx", # repo dev local
]


@st.cache_data
def load_data() -> pd.DataFrame:
    for p in LOCAL_CANDIDATES:
        if p.exists():
            return pd.read_excel(p)
    target = HERE / "get_around_delay_analysis.xlsx"
    urllib.request.urlretrieve(DATASET_URL, str(target))
    return pd.read_excel(target)


try:
    df = load_data()
except Exception as e:
    st.error(f"Impossible de charger le dataset : {e}")
    st.stop()

# ============================================================
# Sidebar — URL de l'API (modifiable en direct, ex. secours local)
# ============================================================
st.sidebar.header("🔌 API de pricing")
api_url = st.sidebar.text_input(
    "URL de l'API", value=DEFAULT_API_URL,
    help="Secours pendant la démo : http://127.0.0.1:8000 (uvicorn en local)",
)
st.sidebar.markdown("---")

# ============================================================
# Onglets
# ============================================================
tab_delay, tab_price = st.tabs(["📊 Analyse des retards", "💰 Estimer un prix (API)"])
with tab_delay:
    delay_analysis.render(df)
with tab_price:
    pricing_ui.render(api_url)
