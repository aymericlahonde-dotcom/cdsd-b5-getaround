"""Onglet « Estimer un prix » : formulaire → POST /predict de l'API → résultat.

C'est ici que le dashboard UTILISE l'API (critères jury « interface web
incluant l'utilisation de l'API »).
"""
import json

import streamlit as st

import pricing_client as pc

# Valeurs vues dans get_around_pricing_project.csv (codées en dur pour ne pas
# dépendre du CSV au runtime sur HF Spaces).
MODEL_KEYS = [
    "Alfa Romeo", "Audi", "BMW", "Citroën", "Ferrari", "Fiat", "Ford", "Honda",
    "KIA Motors", "Lamborghini", "Lexus", "Maserati", "Mazda", "Mercedes",
    "Mini", "Mitsubishi", "Nissan", "Opel", "PGO", "Peugeot", "Porsche",
    "Renault", "SEAT", "Subaru", "Suzuki", "Toyota", "Volkswagen", "Yamaha",
]
FUELS = ["diesel", "petrol", "hybrid_petrol", "electro"]
COLORS = ["black", "grey", "white", "blue", "silver", "red", "brown",
          "beige", "green", "orange"]
CAR_TYPES = ["convertible", "coupe", "estate", "hatchback", "sedan",
             "subcompact", "suv", "van"]
BOOL_LABELS = {
    "private_parking_available": "Parking privé",
    "has_gps": "GPS",
    "has_air_conditioning": "Climatisation",
    "automatic_car": "Boîte automatique",
    "has_getaround_connect": "Getaround Connect",
    "has_speed_regulator": "Régulateur de vitesse",
    "winter_tires": "Pneus hiver",
}
# Exemple de l'énoncé : Citroën diesel noire convertible, 140 000 km, 100 ch
DEFAULT_BOOLS = {
    "private_parking_available": True, "has_gps": True,
    "has_air_conditioning": False, "automatic_car": False,
    "has_getaround_connect": True, "has_speed_regulator": True,
    "winter_tires": True,
}


def _health_panel(api_url: str) -> None:
    st.markdown("#### 🩺 État de l'API")
    st.code(api_url, language=None)
    if st.button("Réveiller / vérifier l'API (GET /health)"):
        with st.spinner("Appel de /health…"):
            try:
                info = pc.check_health(api_url)
            except pc.ApiError as e:
                st.error(str(e))
            else:
                st.success(
                    f"API en ligne — modèle chargé : {info.get('model_type')} "
                    f"({info.get('n_features')} features)"
                )
                st.json(info)


def _form() -> list | None:
    """Affiche le formulaire ; renvoie la ligne de 13 valeurs si soumis."""
    with st.form("predict_form"):
        c1, c2, c3 = st.columns(3)
        model_key = c1.selectbox("Marque (model_key)", MODEL_KEYS,
                                 index=MODEL_KEYS.index("Citroën"))
        fuel = c2.selectbox("Carburant (fuel)", FUELS, index=0)
        car_type = c3.selectbox("Type (car_type)", CAR_TYPES, index=0)
        c4, c5, c6 = st.columns(3)
        paint_color = c4.selectbox("Couleur (paint_color)", COLORS, index=0)
        mileage = c5.number_input("Kilométrage (mileage)", min_value=0,
                                  max_value=1_000_000, value=140_000, step=1_000)
        engine_power = c6.number_input("Puissance ch (engine_power)", min_value=0,
                                       max_value=500, value=100, step=5)
        st.markdown("**Options**")
        bools = {}
        cols = st.columns(4)
        for i, (key, label) in enumerate(BOOL_LABELS.items()):
            bools[key] = cols[i % 4].checkbox(label, value=DEFAULT_BOOLS[key],
                                              key=f"bool_{key}")
        submitted = st.form_submit_button("🚀 Appeler l'API /predict", type="primary")

    if not submitted:
        return None
    return [
        model_key, int(mileage), int(engine_power), fuel, paint_color, car_type,
        bools["private_parking_available"], bools["has_gps"],
        bools["has_air_conditioning"], bools["automatic_car"],
        bools["has_getaround_connect"], bools["has_speed_regulator"],
        bools["winter_tires"],
    ]


def _show_result(res: pc.PredictResult) -> None:
    st.metric("Prix journalier estimé", f"{res.price:.2f} € / jour",
              delta=f"réponse en {res.latency_s * 1000:.0f} ms", delta_color="off")
    with st.expander("🔍 Détails techniques (ce que le dashboard a envoyé / reçu)",
                     expanded=True):
        st.markdown(f"**URL appelée :** `POST {res.url}`")
        st.markdown("**JSON envoyé** (format imposé par l'énoncé) :")
        st.code(json.dumps(res.payload, ensure_ascii=False, indent=2), language="json")
        st.markdown("**JSON reçu** (réponse brute de l'API) :")
        st.code(json.dumps(res.response_json, indent=2), language="json")
        st.markdown("**Équivalent curl :**")
        base = res.url.rsplit("/predict", 1)[0]
        st.code(pc.curl_command(base, res.payload), language="bash")


def render(api_url: str) -> None:
    st.subheader("💰 Estimer le prix journalier d'une voiture via l'API")
    st.caption(
        "Le formulaire construit le JSON attendu par `POST /predict`, l'envoie à "
        "l'API FastAPI déployée sur HuggingFace Spaces et affiche la réponse brute."
    )
    left, right = st.columns([2, 1])
    with right:
        _health_panel(api_url)
    with left:
        row = _form()
        if row is not None:
            with st.spinner("Appel de l'API… (jusqu'à 15 s si le Space se réveille)"):
                try:
                    res = pc.predict(api_url, row)
                except pc.ApiError as e:
                    st.error(str(e))
                else:
                    _show_result(res)
