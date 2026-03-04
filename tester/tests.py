"""
tester/tests.py
Tests "as code" pour l'API Frankfurter (taux de change).
Chaque test retourne un dict {"name", "status", "latency_ms", "details"}.
Couverture : ≥ 6 tests (contrat + robustesse + cas invalides).
"""
import re
from tester.client import APIClient

client = APIClient()


def _result(name: str, passed: bool, latency_ms: float, details: str = "") -> dict:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "latency_ms": round(latency_ms, 2),
        "details": details,
    }


# ─────────────────────────────────────────────
# A. Tests Contrat (fonctionnels)
# ─────────────────────────────────────────────

def test_latest_status_200():
    """GET /latest → HTTP 200."""
    name = "GET /latest → HTTP 200"
    resp = client.get("/latest?from=EUR")
    ok = resp.status_code == 200
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"HTTP {resp.status_code}")


def test_latest_content_type_json():
    """GET /latest → Content-Type JSON."""
    name = "GET /latest → Content-Type JSON"
    resp = client.get("/latest?from=EUR")
    ct = resp.response.headers.get("Content-Type", "")
    ok = "application/json" in ct
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Content-Type: {ct}")


def test_latest_required_fields():
    """GET /latest → champs 'amount', 'base', 'date', 'rates' présents."""
    name = "GET /latest → champs obligatoires"
    resp = client.get("/latest?from=EUR")
    if not resp.ok:
        return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")
    data = resp.json()
    required = {"amount", "base", "date", "rates"}
    missing = required - set(data.keys())
    ok = len(missing) == 0
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Champs manquants: {missing}")


def test_latest_field_types():
    """GET /latest → types des champs (float, str, str, dict)."""
    name = "GET /latest → types des champs"
    resp = client.get("/latest?from=EUR")
    if not resp.ok:
        return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")
    data = resp.json()
    errors = []
    if not isinstance(data.get("amount"), (int, float)):
        errors.append(f"amount: attendu float, obtenu {type(data.get('amount')).__name__}")
    if not isinstance(data.get("base"), str):
        errors.append(f"base: attendu str, obtenu {type(data.get('base')).__name__}")
    if not isinstance(data.get("date"), str):
        errors.append(f"date: attendu str, obtenu {type(data.get('date')).__name__}")
    if not isinstance(data.get("rates"), dict):
        errors.append(f"rates: attendu dict, obtenu {type(data.get('rates')).__name__}")
    # Vérifier format date YYYY-MM-DD
    if data.get("date") and not re.match(r"^\d{4}-\d{2}-\d{2}$", data["date"]):
        errors.append(f"date format invalide: {data['date']}")
    ok = len(errors) == 0
    return _result(name, ok, resp.latency_ms, "; ".join(errors))


def test_latest_target_currencies():
    """GET /latest?from=EUR&to=USD,GBP → rates contient USD et GBP."""
    name = "GET /latest?from=EUR&to=USD,GBP → USD et GBP présents"
    resp = client.get("/latest", params={"from": "EUR", "to": "USD,GBP"})
    if not resp.ok:
        return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")
    data = resp.json()
    rates = data.get("rates", {})
    missing = [c for c in ["USD", "GBP"] if c not in rates]
    ok = len(missing) == 0
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Devises absentes: {missing}")


def test_currencies_endpoint():
    """GET /currencies → liste de devises valide (dict non vide de strings)."""
    name = "GET /currencies → liste de devises"
    resp = client.get("/currencies")
    if resp.status_code != 200:
        return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")
    data = resp.json()
    ok = (isinstance(data, dict) and len(data) > 10
          and all(isinstance(v, str) for v in data.values()))
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Réponse inattendue: {str(data)[:100]}")


def test_historical_date():
    """GET /2024-01-02?from=EUR&to=USD → taux historique valide."""
    name = "GET /2024-01-02 → taux historique EUR→USD"
    resp = client.get("/2024-01-02", params={"from": "EUR", "to": "USD"})
    if not resp.ok:
        return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")
    data = resp.json()
    rates = data.get("rates", {})
    ok = "USD" in rates and isinstance(rates["USD"], (int, float)) and rates["USD"] > 0
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"rates USD absent ou nul: {rates}")


# ─────────────────────────────────────────────
# B. Tests Robustesse / Cas Invalides
# ─────────────────────────────────────────────

def test_invalid_currency_returns_error():
    """GET /latest?from=INVALID → code d'erreur (4xx)."""
    name = "GET /latest?from=INVALID → 4xx attendu"
    resp = client.get("/latest", params={"from": "INVALID"})
    ok = 400 <= resp.status_code < 500
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Attendu 4xx, obtenu HTTP {resp.status_code}")


def test_invalid_date_returns_error():
    """GET /9999-99-99 → code d'erreur (4xx)."""
    name = "GET /9999-99-99 → 4xx attendu"
    resp = client.get("/9999-99-99")
    ok = 400 <= resp.status_code < 500
    return _result(name, ok, resp.latency_ms,
                   "" if ok else f"Attendu 4xx, obtenu HTTP {resp.status_code}")


def test_base_equals_target_not_in_rates():
    """GET /latest?from=EUR&to=EUR → EUR ne devrait pas être dans rates (ou rates vide)."""
    name = "GET /latest?from=EUR&to=EUR → cohérence devise base=cible"
    resp = client.get("/latest", params={"from": "EUR", "to": "EUR"})
    # Soit 4xx, soit rates vide/absent
    if 400 <= resp.status_code < 500:
        return _result(name, True, resp.latency_ms, f"HTTP {resp.status_code} (correct)")
    if resp.ok:
        data = resp.json()
        rates = data.get("rates", {})
        ok = "EUR" not in rates or len(rates) == 0
        return _result(name, ok, resp.latency_ms,
                       "" if ok else f"EUR dans rates: {rates}")
    return _result(name, False, resp.latency_ms, f"HTTP {resp.status_code}")


# Registre de tous les tests
ALL_TESTS = [
    test_latest_status_200,
    test_latest_content_type_json,
    test_latest_required_fields,
    test_latest_field_types,
    test_latest_target_currencies,
    test_currencies_endpoint,
    test_historical_date,
    test_invalid_currency_returns_error,
    test_invalid_date_returns_error,
    test_base_equals_target_not_in_rates,
]
