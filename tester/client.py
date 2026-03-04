"""
tester/client.py
HTTP client wrapper with timeout, retry, and latency measurement.
"""
import time
import requests


BASE_URL = "https://api.frankfurter.app"
TIMEOUT = 3          # secondes
MAX_RETRIES = 1      # 1 retry max (robustesse)
RETRY_WAIT = 1.0     # attente entre tentatives (secondes)


class APIResponse:
    """Résultat d'un appel HTTP enrichi avec la mesure de latence."""

    def __init__(self, response: requests.Response, latency_ms: float):
        self.response = response
        self.status_code = response.status_code
        self.latency_ms = latency_ms
        self._json = None

    def json(self):
        if self._json is None:
            self._json = self.response.json()
        return self._json

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class APIClient:
    """
    Wrapper HTTP avec :
    - timeout configurable
    - 1 retry en cas de 5xx ou timeout réseau
    - gestion 429 (rate-limit) : attente et réessai
    - mesure de la latence en ms
    """

    def __init__(self, base_url: str = BASE_URL,
                 timeout: float = TIMEOUT,
                 max_retries: int = MAX_RETRIES):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def get(self, path: str, **kwargs) -> APIResponse:
        """
        Effectue un GET sur `base_url + path`.
        Gère les retries sur erreurs 5xx / timeouts / 429.
        """
        url = self.base_url + path
        attempts = 0
        last_exc = None

        while attempts <= self.max_retries:
            try:
                start = time.perf_counter()
                resp = self.session.get(url, timeout=self.timeout, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                # Gestion 429 Rate-Limit
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", RETRY_WAIT))
                    time.sleep(retry_after)
                    attempts += 1
                    continue

                # Retry sur erreurs serveur (5xx)
                if resp.status_code >= 500 and attempts < self.max_retries:
                    time.sleep(RETRY_WAIT)
                    attempts += 1
                    continue

                return APIResponse(resp, elapsed_ms)

            except requests.exceptions.Timeout as exc:
                last_exc = exc
                if attempts < self.max_retries:
                    time.sleep(RETRY_WAIT)
                    attempts += 1
                    continue
                raise TimeoutError(
                    f"Timeout après {self.timeout}s sur {url}"
                ) from exc

            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                if attempts < self.max_retries:
                    time.sleep(RETRY_WAIT)
                    attempts += 1
                    continue
                raise ConnectionError(
                    f"Erreur réseau sur {url}: {exc}"
                ) from exc

        # Échec définitif après tous les retries
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Échec de la requête sur {url} après {attempts} tentatives")
