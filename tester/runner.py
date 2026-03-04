"""
tester/runner.py
Exécute tous les tests, calcule les métriques QoS et retourne un run complet.
"""
import datetime
import statistics
from tester.tests import ALL_TESTS


def run_all() -> dict:
    """
    Exécute tous les tests, calcule les métriques et retourne le run.
    Structure conforme au format demandé dans l'atelier.
    """
    results = []
    errors = []

    for test_fn in ALL_TESTS:
        try:
            result = test_fn()
            results.append(result)
        except Exception as exc:
            # Erreur inattendue (timeout réseau, connexion, etc.)
            results.append({
                "name": getattr(test_fn, "__name__", "unknown"),
                "status": "ERROR",
                "latency_ms": 0,
                "details": str(exc),
            })
            errors.append(str(exc))

    # ── Métriques QoS ──────────────────────────────────────────────────────
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    error_count = sum(1 for r in results if r["status"] == "ERROR")

    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    latency_avg = round(statistics.mean(latencies), 2) if latencies else 0
    latency_p95 = round(
        statistics.quantiles(latencies, n=20)[18], 2
    ) if len(latencies) >= 2 else (latencies[0] if latencies else 0)

    error_rate = round((failed + error_count) / total, 3) if total > 0 else 0
    availability = round(passed / total, 3) if total > 0 else 0

    return {
        "api": "Frankfurter",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": error_count,
            "error_rate": error_rate,
            "availability": availability,
            "latency_ms_avg": latency_avg,
            "latency_ms_p95": latency_p95,
        },
        "tests": results,
    }
