---
title: Getaround Dashboard
emoji: 🚗
colorFrom: red
colorTo: red
sdk: docker
app_port: 8501
pinned: false
short_description: Analyse des retards Getaround et simulation de seuil minimum entre locations
---

# Getaround Delay Analysis Dashboard

Dashboard Streamlit qui aide l'équipe Product de Getaround à choisir un **seuil minimum entre deux locations** pour réduire les retards en checkout, sans pénaliser excessivement le revenu.

## Comment ça marche

1. Le dataset est téléchargé automatiquement depuis Jedha S3 au premier lancement (`get_around_delay_analysis.xlsx`).
2. L'utilisateur règle dans la sidebar :
   - Le **seuil minimum** entre 2 locations (en minutes)
   - Le **scope** : toutes les voitures, ou uniquement Connect
3. Le dashboard affiche les 4 questions clés du Product Manager :
   - Part du revenu impactée
   - Nombre de locations affectées
   - Fréquence et impact des retards
   - Cas problématiques résolus

## Stack

- **Streamlit** — UI dashboard
- **pandas** + **openpyxl** — manipulation données + lecture Excel
- **plotly** — visualisations interactives
- **Docker** — conteneurisation pour HF Spaces

## Lien repo source

<https://github.com/aymericlahonde-dotcom/cdsd-b5-getaround>

## Auteur

Aymeric Lahonde — promotion Jedha CDSD 2026.
