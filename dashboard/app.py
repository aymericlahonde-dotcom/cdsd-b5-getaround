"""Dashboard Streamlit - Getaround Delay Analysis (Bloc 5 Jedha).

Repond aux 4 questions du Product Manager :
1. Quelle part du revenu owners serait impactee par un seuil minimum ?
2. Combien de rentals seraient bloques selon threshold + scope ?
3. Frequence des retards et impact sur le driver suivant
4. Combien de cas problematiques resolus par le seuil ?

Usage local :
    streamlit run app.py

Deploiement HuggingFace Spaces (Docker) :
    Push ce dossier vers un Space "Docker" - le Dockerfile s'occupe du reste.
"""
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Getaround - Delay Analysis",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Getaround - Analyse des retards de checkout")
st.caption(
    "Dashboard interactif pour aider le Product Manager à choisir un seuil minimum "
    "entre 2 locations consecutives. Bloc 5 Jedha CDSD."
)


# ============================================================
# Loading dataset (cache + fallback URL si fichier local absent)
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
# Sidebar - parametres simulation
# ============================================================
st.sidebar.header("⚙️ Parametres de la mesure")

threshold_min = st.sidebar.slider(
    "Seuil minimum entre 2 locations (minutes)",
    min_value=0, max_value=720, value=90, step=15,
    help="Une location est bloquee si elle commence < threshold min apres la fin de la precedente",
)

scope = st.sidebar.radio(
    "Scope d'application",
    options=["all", "connect"],
    format_func=lambda x: "Toutes les voitures" if x == "all" else "Connect uniquement",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Toggle d'analyse : le calcul s'effectue sur le sous-ensemble des rentals "
    "consecutifs (avec `previous_ended_rental_id` non vide)."
)


# ============================================================
# Sous-ensemble des rentals consecutifs
# ============================================================
# Pour analyser l'impact du seuil, on a besoin du delay du precedent + time_delta
prev = df.set_index("rental_id")["delay_at_checkout_in_minutes"]
consecutive = df.dropna(subset=["previous_ended_rental_id"]).copy()
consecutive["prev_delay"] = consecutive["previous_ended_rental_id"].map(prev)
# 1 rental "next-driver impacted" = previous a fini en retard ET ce retard a empiete
# sur la fenetre du current rental
consecutive["next_driver_impacted"] = (
    (consecutive["prev_delay"] > 0)
    & (consecutive["prev_delay"] > consecutive["time_delta_with_previous_rental_in_minutes"])
)


def filter_scope(d: pd.DataFrame, scope_choice: str) -> pd.DataFrame:
    return d if scope_choice == "all" else d[d["checkin_type"] == "connect"]


df_scope = filter_scope(df, scope)
cons_scope = filter_scope(consecutive, scope)


# ============================================================
# KPI principaux
# ============================================================
st.markdown("### 📊 Vue d'ensemble (selon le scope choisi)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Locations totales", f"{len(df_scope):,}".replace(",", " "))
c2.metric("Locations consecutives", f"{len(cons_scope):,}".replace(",", " "))
late_pct = (cons_scope["prev_delay"] > 0).mean() * 100 if len(cons_scope) else 0
c3.metric("% precedent en retard", f"{late_pct:.1f}%")
impacted_pct = cons_scope["next_driver_impacted"].mean() * 100 if len(cons_scope) else 0
c4.metric("% next-driver impacte", f"{impacted_pct:.1f}%")


# ============================================================
# Q1 - Part du revenu impactee
# ============================================================
st.markdown("---")
st.subheader("1️⃣ Part du revenu owners impactee par la mesure")

# Approximation : un rental est "bloque" par la mesure si son time_delta < threshold
blocked_mask = (
    cons_scope["time_delta_with_previous_rental_in_minutes"] < threshold_min
)
n_blocked = int(blocked_mask.sum())
total_consecutive = len(cons_scope)
pct_revenue = (n_blocked / total_consecutive * 100) if total_consecutive else 0
# Approximation revenue : meme proportion sur ALL rentals = upper bound car les
# locations isolees ne sont jamais bloquees par definition
n_blocked_total = n_blocked
pct_revenue_total = (n_blocked_total / len(df_scope) * 100) if len(df_scope) else 0

q1a, q1b = st.columns(2)
q1a.metric(
    "% rentals consecutifs bloques",
    f"{pct_revenue:.1f}%",
    delta=f"{n_blocked} rentals",
    delta_color="off",
)
q1b.metric(
    "% revenu total estime perdu",
    f"{pct_revenue_total:.2f}%",
    help="Hypothese : 1 rental bloque = revenue moyen perdu",
)

st.caption(
    f"Avec un seuil de **{threshold_min} min** sur le scope **{scope}**, "
    f"environ **{pct_revenue_total:.2f} %** du revenu owner total serait impacte."
)


# ============================================================
# Q2 - Distribution des time_delta (histogramme)
# ============================================================
st.markdown("---")
st.subheader("2️⃣ Distribution des time_delta entre 2 locations")

if len(cons_scope) > 0:
    capped = cons_scope.copy()
    capped["time_delta_capped"] = capped["time_delta_with_previous_rental_in_minutes"].clip(0, 720)
    fig = px.histogram(
        capped, x="time_delta_capped", nbins=24,
        color_discrete_sequence=["#6A1B9A"],
        labels={"time_delta_capped": "Time delta entre 2 locations (min, cappe a 720)"},
    )
    fig.add_vline(
        x=threshold_min, line_dash="dash", line_color="#00BFA5",
        annotation_text=f"Seuil = {threshold_min} min",
        annotation_position="top",
    )
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"La barre turquoise represente le seuil teste. Tout ce qui est a sa GAUCHE "
        f"sera bloque par la mesure ({n_blocked} rentals)."
    )
else:
    st.info("Aucun rental consecutif dans le scope choisi.")


# ============================================================
# Q3 - Frequence et amplitude des retards
# ============================================================
st.markdown("---")
st.subheader("3️⃣ Frequence et amplitude des retards de checkout")

late_only = df_scope[df_scope["delay_at_checkout_in_minutes"] > 0]
q3a, q3b, q3c = st.columns(3)
q3a.metric(
    "Locations avec retard",
    f"{len(late_only):,}".replace(",", " "),
    delta=f"{len(late_only) / max(len(df_scope), 1) * 100:.1f}% du scope",
    delta_color="off",
)
q3b.metric("Retard median", f"{late_only['delay_at_checkout_in_minutes'].median():.0f} min")
q3c.metric("Retard moyen", f"{late_only['delay_at_checkout_in_minutes'].mean():.0f} min")

# Histogramme des retards (cappes a 240 min pour la lisibilite)
if len(late_only) > 0:
    capped_delay = late_only["delay_at_checkout_in_minutes"].clip(0, 240)
    fig2 = px.histogram(
        capped_delay, nbins=24,
        color_discrete_sequence=["#FE3C72"],
        labels={"value": "Retard de checkout (min, cappe a 240)"},
    )
    fig2.update_layout(height=320, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# Q4 - Cas problematiques resolus par le seuil
# ============================================================
st.markdown("---")
st.subheader("4️⃣ Cas problematiques resolus par le seuil")

# Cas problematiques actuels = next_driver_impacted
total_problems = int(cons_scope["next_driver_impacted"].sum())

# Cas resolus = ceux ou le seuil bloque le rental probleme avant qu'il ait lieu
# (ie. ceux qui auraient ete impactes mais qui sont desormais bloques)
solved_mask = cons_scope["next_driver_impacted"] & blocked_mask
n_solved = int(solved_mask.sum())
pct_solved = (n_solved / total_problems * 100) if total_problems else 0

q4a, q4b, q4c = st.columns(3)
q4a.metric("Cas problematiques actuels", f"{total_problems}")
q4b.metric("Cas resolus par le seuil", f"{n_solved}", delta=f"{pct_solved:.0f}%")
q4c.metric("Cas restants", f"{total_problems - n_solved}")

# Sweep : pct resolu en fonction du threshold (pour aider le PM)
thresholds_sweep = np.arange(0, 721, 30)
sweep = []
for t in thresholds_sweep:
    blk = cons_scope["time_delta_with_previous_rental_in_minutes"] < t
    solved_t = (cons_scope["next_driver_impacted"] & blk).sum()
    blocked_t = blk.sum()
    sweep.append({
        "threshold": int(t),
        "pct_problems_solved": (solved_t / total_problems * 100) if total_problems else 0,
        "pct_revenue_lost": (blocked_t / max(len(df_scope), 1) * 100),
    })
sweep_df = pd.DataFrame(sweep)

fig3 = px.line(
    sweep_df, x="threshold", y=["pct_problems_solved", "pct_revenue_lost"],
    labels={"value": "%", "threshold": "Seuil (minutes)", "variable": "Indicateur"},
    color_discrete_map={
        "pct_problems_solved": "#00BFA5",
        "pct_revenue_lost": "#FE3C72",
    },
)
fig3.add_vline(
    x=threshold_min, line_dash="dash", line_color="#6A1B9A",
    annotation_text=f"Seuil actuel = {threshold_min}",
    annotation_position="top",
)
fig3.update_layout(height=380, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig3, use_container_width=True)

st.caption(
    "Trade-off PM : la courbe **turquoise** monte avec le seuil (plus de cas resolus), "
    "la courbe **rose** monte aussi (plus de revenu impacte). "
    "Le sweet spot est typiquement entre 60 et 120 min sur les Connect cars."
)


# ============================================================
# Recommandation finale
# ============================================================
st.markdown("---")
st.markdown("### 💡 Recommandation")
st.success(
    f"Avec le seuil **{threshold_min} min** sur **{scope}** : "
    f"{pct_solved:.0f}% des cas problematiques sont resolus, "
    f"pour {pct_revenue_total:.2f}% du revenu impacte. "
    "La recommandation par defaut est 60-90 min sur Connect uniquement."
)

st.markdown("---")
st.caption("🎓 Aymeric Lahonde - Jedha CDSD Bloc 5 Getaround")
