import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)

PROVIDERS_FILE = Path(__file__).with_name("providers.json")


class JackettAdapter:
    """Minimal Jackett adapter used for tests.

    The implementation purposely keeps the logic lightweight.  Network calls are
    best-effort and may return empty data if Jackett is unreachable.  This
    behaviour is sufficient for unit tests which typically monkeypatch the
    methods.
    """

    def __init__(self, base_url: str = "http://jackett:9117"):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Provider catalogue
    # ------------------------------------------------------------------
    def _read_catalog(self) -> List[Dict[str, Any]]:
        if PROVIDERS_FILE.exists():
            try:
                return json.loads(PROVIDERS_FILE.read_text())
            except Exception:  # pragma: no cover - defensive
                logger.warning("failed to read providers catalog")
        return []

    def _fetch_indexers(self) -> List[Dict[str, Any]]:
        """Best-effort fetch of Jackett's indexer catalogue."""

        url = f"{self.base_url}/api/v2.0/server/indexers"
        try:
            r = httpx.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:  # pragma: no cover - network best effort
            logger.warning("indexers fetch failed url=%s error=%s", url, e)
            return []

    def _normalise(self, it: Dict[str, Any]) -> Dict[str, Any]:
        slug = it.get("id") or it.get("slug") or it.get("name")
        name = it.get("name") or slug
        cfg = it.get("config") or {}
        needs: List[str] = []
        if cfg.get("requiresCredentials") or it.get("requires_auth"):
            needs = ["username", "password"]
        type_ = "private" if needs else (it.get("type") or "public")
        return {
            "slug": slug,
            "name": name,
            "type": type_,
            "needs": needs,
            "configured": bool(it.get("configured")),
        }

    def list_configured(self) -> List[Dict[str, Any]]:
        """Return providers already configured in Jackett."""

        items = [self._normalise(p) for p in self._fetch_indexers()]
        return [p for p in items if p.get("configured")]

    def list_available(self) -> List[Dict[str, Any]]:
        """Return providers available for installation.

        Attempts to query Jackett for the complete catalogue; falls back to
        a bundled static JSON list if Jackett is unreachable.
        """

        items = [self._normalise(p) for p in self._fetch_indexers()]
        avail = [p for p in items if not p.get("configured")]
        return avail if avail else self._read_catalog()

    # ------------------------------------------------------------------
    # Installation and configuration
    # ------------------------------------------------------------------
    def ensure_installed(self, slug: str, creds: Dict[str, Any] | None) -> Dict[str, Any]:
        """Ensure that the given provider is installed and configured.

        Real Jackett integration would POST to Jackett's admin API.  For the
        purposes of the tests we simply validate the slug and return provider
        metadata.
        """

        providers = {p["slug"]: p for p in self.list_available()}
        if slug not in providers:
            raise ValueError("provider_not_found")
        prov = providers[slug]
        return prov

    def get_torznab_url(self, slug: str) -> str:
        return f"{self.base_url}/api/v2.0/indexers/{slug}/results/torznab/"

    # ------------------------------------------------------------------
    # Capability / health checks
    # ------------------------------------------------------------------
    def fetch_caps(self, torznab_url: str) -> Dict[str, Any]:
        url = torznab_url.rstrip("/") + "?t=caps"
        try:
            r = httpx.get(url, timeout=10)
            r.raise_for_status()
            return r.json() if "application/json" in r.headers.get("content-type", "") else {}
        except Exception as e:  # pragma: no cover - network best effort
            logger.warning("fetch_caps failed url=%s error=%s", url, e)
            return {}

    def test_search(self, torznab_url: str, q: str = "test") -> Tuple[bool, int | None]:
        url = torznab_url.rstrip("/") + f"?t=search&q={q}"
        try:
            r = httpx.get(url, timeout=10)
            ok = r.status_code == 200
            latency = int(r.elapsed.total_seconds() * 1000)
            return ok, latency
        except Exception as e:  # pragma: no cover - network best effort
            logger.warning("test_search failed url=%s error=%s", url, e)
            return False, None

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def enable(self, slug: str, enabled: bool) -> None:
        """Enable or disable a provider in Jackett.

        The stub implementation does nothing; behaviour can be overridden in
        tests.
        """

        return None

    def remove(self, slug: str) -> None:
        """Remove a provider from Jackett.

        Stub implementation; tests may monkeypatch if required.
        """

        return None
