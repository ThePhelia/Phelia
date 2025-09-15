# apps/api/app/services/jackett_adapter.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import httpx
import os

logger = logging.getLogger(__name__)

PROVIDERS_FILE = Path(__file__).with_name("providers.json")

JACKETT_BASE = os.getenv("JACKETT_BASE", "http://jackett:9117")
# Torznab ключ берём из переменных окружения или из bootstrap'а, если ты его туда пишешь
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY", "")

class JackettAdapter:
    """
    Adapter around Jackett. Prefers live discovery via /api/v2.0/indexers,
    falls back to providers.json when Jackett discovery fails.
    """

    def __init__(self) -> None:
        self.base = JACKETT_BASE.rstrip("/")

    # ------------ discovery ------------
    def _read_catalog(self) -> List[Dict[str, Any]]:
        try:
            if PROVIDERS_FILE.exists():
                return json.loads(PROVIDERS_FILE.read_text("utf-8"))
        except Exception as e:
            logger.warning("providers.json read failed: %s", e)
        return []

    def _ensure_no_redirect(self, response: httpx.Response, url: str, action: str) -> None:
        if response.is_redirect or any(prev.is_redirect for prev in response.history):
            raise RuntimeError(
                "Jackett returned a redirect while "
                f"{action} (url={url}). This likely means authentication is missing or the Jackett base path is incorrect."
            )

    def _fetch_indexers(self) -> List[Dict[str, Any]]:
        """
        Ask Jackett for indexers (configured & available). Depending on Jackett version,
        GET /api/v2.0/indexers returns either rich objects or minimal list.
        We normalize into: slug, name, configured, needs
        """
        url = f"{self.base}/api/v2.0/indexers/"
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            self._ensure_no_redirect(r, url, "fetching indexers")
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                return []
            return data
        except RuntimeError:
            raise
        except Exception as e:
            logger.warning("indexers fetch failed url=%s error=%s", url, e)
            return []

    def _get_schema(self, slug: str) -> Dict[str, Any]:
        url = f"{self.base}/api/v2.0/indexers/{slug}/schema/"
        r = httpx.get(url, timeout=10, follow_redirects=True)
        self._ensure_no_redirect(r, url, f"fetching schema for '{slug}'")
        r.raise_for_status()
        return r.json()

    def _normalise(self, it: Dict[str, Any]) -> Dict[str, Any]:
        # Jackett often exposes "id"/"name"
        slug = it.get("id") or it.get("slug") or it.get("name")
        name = it.get("name") or slug
        configured = bool(it.get("configured", False))
        needs: List[str] = []

        # Try to infer required fields from schema (best-effort)
        try:
            schema = self._get_schema(slug)
            fields = schema.get("fields") or []
            needs = [f["name"] for f in fields if f.get("required")]
        except Exception:
            # Fallback: check hints on the object
            cfg = it.get("config") or {}
            if cfg.get("requiresCredentials") or it.get("requires_auth"):
                needs = ["username", "password"]

        type_ = "private" if needs else "public"
        return {"slug": slug, "name": name, "type": type_, "configured": configured, "needs": needs}

    def list_available(self) -> List[Dict[str, Any]]:
        live = self._fetch_indexers()
        if live:
            out = []
            for it in live:
                try:
                    out.append(self._normalise(it))
                except Exception as e:
                    logger.debug("normalize failed for %s: %s", it, e)
            # de-dup by slug
            seen, uniq = set(), []
            for p in out:
                if p["slug"] in seen:
                    continue
                seen.add(p["slug"])
                uniq.append(p)
            return uniq

        # fallback to static catalog
        cat = self._read_catalog()
        out = []
        for it in cat:
            slug = it.get("slug") or it.get("id")
            name = it.get("name") or slug
            needs = it.get("needs") or []
            type_ = it.get("type") or ("private" if needs else "public")
            out.append({"slug": slug, "name": name, "type": type_, "configured": False, "needs": needs})
        return out

    def list_configured(self) -> List[str]:
        """
        Return slugs of configured/installed indexers in Jackett.
        """
        live = self._fetch_indexers()
        slugs: List[str] = []
        for it in live:
            slug = it.get("id") or it.get("slug") or it.get("name")
            if not slug:
                continue
            if it.get("configured") is True:
                slugs.append(slug)
        return slugs

    # ------------ connect / control ------------
    def ensure_installed(self, slug: str, creds: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Configure indexer by slug. On Jackett, POSTing config usually installs/enables.
        We try schema->POST config; if no fields required, send empty dict.
        """
        try:
            schema = self._get_schema(slug)
            fields = schema.get("fields") or []
            required = [f["name"] for f in fields if f.get("required")]
            payload = {}

            if required:
                if not creds:
                    raise ValueError(f"missing_credentials:{required}")
                for f in required:
                    v = (creds or {}).get(f)
                    if not v:
                        raise ValueError(f"missing_credentials:{required}")
                    payload[f] = v

            url = f"{self.base}/api/v2.0/indexers/{slug}/config/"
            r = httpx.post(url, json=payload, timeout=15, follow_redirects=True)
            self._ensure_no_redirect(r, url, f"configuring '{slug}'")
            r.raise_for_status()
            return {"slug": slug, "configured": True}
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise PermissionError("auth_failed") from e
            raise
        except ValueError as ve:
            # propagate our missing credentials marker
            raise ve

    def get_torznab_url(self, slug: str) -> str:
        return f"{self.base}/api/v2.0/indexers/{slug}/results/torznab/"

    def fetch_caps(self, slug: str) -> Dict[str, Any]:
        """
        Torznab /api?t=caps. Requires apikey.
        """
        url = f"{self.get_torznab_url(slug)}api"
        params = {"t": "caps"}
        if JACKETT_API_KEY:
            params["apikey"] = JACKETT_API_KEY
        r = httpx.get(url, params=params, timeout=10, follow_redirects=True)
        self._ensure_no_redirect(r, url, f"fetching caps for '{slug}'")
        r.raise_for_status()
        # feedparser expects XML, но нам хватает JSON если Jackett так отдаёт; иначе вернём текст
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}

    def test_search(self, torznab_url: str, q: str = "test") -> Tuple[bool, Optional[int]]:
        url = f"{torznab_url}api"
        params = {"t": "search", "q": q}
        if JACKETT_API_KEY:
            params["apikey"] = JACKETT_API_KEY
        r = httpx.get(url, params=params, timeout=10)
        ok = r.status_code == 200
        return ok, r.elapsed.total_seconds() * 1000 if ok else None

    def enable(self, slug: str, enabled: bool) -> None:
        # Jackett не имеет явного toggle API для indexer; держим включение на нашей стороне.
        return None

    def remove(self, slug: str) -> None:
        # При желании можно дернуть DELETE /api/v2.0/indexers/{slug}, если версия поддерживает.
        return None

