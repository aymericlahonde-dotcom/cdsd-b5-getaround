"""Dashboard Streamlit — Getaround Delay Analysis (axe 1).

Exploration des retours en retard de location et simulation de l'impact
d'un seuil minimum entre deux locations sur le revenu et le nombre de
problèmes résolus.

Usage local :
    streamlit run app.py

Déploiement :
    HuggingFace Spaces (Streamlit) ou autre.
"""
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Getaround — Delay Analysis", layout="wide")

st.title("🚗 Getaround — Analyse des retards")
st.caption("Dashboard Streamlit pour aider le Product Manager à choisir un seuil minimum entre 2 locations.")

# ─── Chargement des données ─────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_excel("../data/get_around_delay_analysis.xlsx")

try:
    df = load_data()
    st.success(f"Dataset chargé : {df.shape[0]} locations, {df.shape[1]} colonnes")
except FileNotFoundError:
    st.error("Le dataset `data/get_around_delay_analysis.xlsx` n'a pas été trouvé.\n"
             "Télécharge-le depuis Julie Jedha et place-le dans le dossier `data/`.")
    st.stop()

# ─── Sidebar — paramètres simulation ────────────────────────────────────
st.sidebar.header("Paramètres de la mesure")
threshold_min = st.sidebar.slider(
    "Seuil minimum (en minutes) entre 2 locations",
    min_value=0, max_value=720, value=60, step=15,
)
scope = st.sidebar.radio(
    "Scope d'application",
    options=["all", "connect"],
    format_func=lambda x: "Toutes les voitures" if x == "all" else "Connect uniquement",
)

# ─── KPI principaux ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Locations totales", f"{len(df):,}")
col2.metric("Seuil testé", f"{threshold_min} min")
col3.metric("Scope", scope)

# ─── TODO : implémenter les 4 analyses ─────────────────────────────────
st.header("Questions du Product Manager")

st.subheader("1. Part du revenu impactée par la mesure")
st.info("TODO : calculer la part des locations qui seraient bloquées par le seuil.")

st.subheader("2. Nombre de locations affectées")
st.info("TODO : croiser threshold + scope + dataset délais.")

st.subheader("3. Fréquence et impact des retards")
st.info("TODO : visualiser distribution des delay_at_checkout_in_minutes.")

st.subheader("4. Cas problématiques résolus")
st.info("TODO : compter les cas (next driver impacted) qui seraient évités.")

st.markdown("---")
st.caption("Aymeric Lahonde — Jedha CDSD Bloc 5")
