"""Captures d'écran des livrables en ligne (pour le PPT et le plan de secours).

Run : python captures/take_screenshots.py
Out : captures/*.png
"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
DASH = "https://alh92500-getaround-dashboard.hf.space"
API = "https://alh92500-getaround-api.hf.space"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=1.5)

    # --- health (réveil + capture JSON) ---
    page.goto(API + "/health", wait_until="networkidle", timeout=120000)
    page.set_viewport_size({"width": 1100, "height": 260})
    page.screenshot(path=str(OUT / "api_health.png"))
    page.set_viewport_size({"width": 1500, "height": 1000})

    # --- Swagger /docs : /predict → Try it out → Execute ---
    page.goto(API + "/docs", wait_until="networkidle", timeout=120000)
    op = page.locator("#operations-Predictions-predict_predict_post")
    op.locator(".opblock-summary").click()
    op.get_by_role("button", name="Try it out").click()
    op.get_by_role("button", name="Execute").click()
    op.locator(".responses-table .response-col_status", has_text="200").first.wait_for(timeout=120000)
    time.sleep(1)
    op.screenshot(path=str(OUT / "swagger_predict_200.png"))
    page.screenshot(path=str(OUT / "swagger_docs_full.png"), full_page=True)

    # --- Dashboard : onglet analyse ---
    page.goto(DASH, wait_until="networkidle", timeout=180000)
    page.get_by_role("tab", name="Analyse des retards").wait_for(timeout=180000)
    time.sleep(4)
    page.screenshot(path=str(OUT / "dashboard_analyse.png"))

    # --- Dashboard : onglet prédiction → appel API ---
    page.get_by_role("tab", name="Estimer un prix").click()
    time.sleep(2)
    page.get_by_role("button", name="Appeler l'API").click()
    page.get_by_text("€ / jour").wait_for(timeout=120000)
    time.sleep(2)
    page.screenshot(path=str(OUT / "dashboard_prediction.png"))
    page.screenshot(path=str(OUT / "dashboard_prediction_full.png"), full_page=True)

    browser.close()
    print("OK ->", sorted(f.name for f in OUT.glob("*.png")))
