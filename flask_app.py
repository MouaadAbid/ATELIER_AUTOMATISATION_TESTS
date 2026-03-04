"""
flask_app.py
Application Flask — Automatisation des tests Frankfurter API.

Routes :
  GET  /             → Redirect vers /dashboard
  GET  /run          → Exécute un run de tests + sauvegarde + redirect dashboard
  GET  /dashboard    → Tableau de bord (résultats + historique)
  GET  /health       → État de santé (JSON) [Bonus]
  GET  /export       → Export JSON du dernier run [Bonus]
"""

import json
import sys
import os

from flask import Flask, render_template, redirect, url_for, jsonify

# Permet d'importer les modules depuis le même répertoire
sys.path.insert(0, os.path.dirname(__file__))

from tester.runner import run_all
from storage import init_db, save_run, list_runs, get_run

app = Flask(__name__)
init_db()


# ─────────────────────────────────────────────
#  / → /dashboard
# ─────────────────────────────────────────────
@app.get("/")
def index():
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
#  /run  — Déclenche un run de tests
# ─────────────────────────────────────────────
@app.get("/run")
def run_tests():
    try:
        run = run_all()
        save_run(run)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
#  /dashboard  — Tableau de bord
# ─────────────────────────────────────────────
@app.get("/dashboard")
def dashboard():
    runs = list_runs(limit=50)
    latest = None
    latest_tests = []

    if runs:
        full = get_run(runs[0]["id"])
        if full:
            latest = runs[0]
            latest_tests = full.get("tests", [])

    return render_template(
        "dashboard.html",
        latest=latest,
        latest_tests=latest_tests,
        history=runs[1:],   # tous sauf le plus récent
        all_runs=runs,
    )


# ─────────────────────────────────────────────
#  /health  — Bonus : état de santé
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    runs = list_runs(limit=1)
    if not runs:
        return jsonify({
            "status": "no_data",
            "message": "Aucun run effectué. Visitez /run pour démarrer.",
        })

    last = runs[0]
    avail = last.get("availability", 1.0)
    status = "healthy" if avail >= 0.8 else ("degraded" if avail >= 0.5 else "unhealthy")

    return jsonify({
        "status": status,
        "last_run_timestamp": last["timestamp"],
        "passed": last["passed"],
        "failed": last["failed"],
        "error_rate": last["error_rate"],
        "availability": avail,
        "latency_avg_ms": last["latency_avg"],
        "latency_p95_ms": last["latency_p95"],
    })


# ─────────────────────────────────────────────
#  /export  — Bonus : export JSON du dernier run
# ─────────────────────────────────────────────
@app.get("/export")
def export_json():
    runs = list_runs(limit=1)
    if not runs:
        return jsonify({"error": "Aucun run disponible"}), 404
    full = get_run(runs[0]["id"])
    response = app.response_class(
        response=json.dumps(full, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=last_run.json"},
    )
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
