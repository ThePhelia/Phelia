from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx

from app.core.config import settings
from app.schemas.media import Classification, EnrichedCard
from app.services.metadata import get_classifier, get_metadata_router
from app.services.metadata.classifier import Classifier
from app.services.metadata.router import MetadataRouter
from app.services.search.torznab import TorznabClient


logger = logging.getLogger(__name__)

PROVIDERS_FILE = Path(__file__).with_name("providers.json")

JACKETT_BASE = settings.JACKETT_BASE
JACKETT_API_KEY = settings.JACKETT_API_KEY or ""


class JackettAdapter:
    """Adapter around Jackett's administrative and search APIs."""

    def __init__(
        self,
        classifier: Classifier | None = None,
        router: MetadataRouter | None = None,
    ) -> None:
        self.base = JACKETT_BASE.rstrip("/")
        self.classifier = classifier or get_classifier()
        self.router = router or get_metadata_router()
        self._torznab = TorznabClient()

    def _auth_headers(self) -> Dict[str, str]:
        if JACKETT_API_KEY:
            return {"X-Api-Key": JACKETT_API_KEY}
        return {}

    # ------------ discovery ------------
    def _read_catalog(self) -> List[Dict[str, Any]]:
        try:
            if PROVIDERS_FILE.exists():
                return json.loads(PROVIDERS_FILE.read_text("utf-8"))
        except Exception as e:  # defensive log
            logger.warning("providers.json read failed: %s", e)
        return []

    def _fetch_indexers(self) -> List[Dict[str, Any]]:
        """Ask Jackett for indexers (configured & available)."""

        url = f"{self.base}/api/v2.0/indexers"
        try:
            r = httpx.get(url, timeout=10, headers=self._auth_headers())
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                return []
            return data
        except Exception as e:  # defensive log
            logger.warning("indexers fetch failed url=%s error=%s", url, e)
            return []

    def _get_schema(self, slug: str) -> Dict[str, Any]:
        url = f"{self.base}/api/v2.0/indexers/{slug}/schema"
        r = httpx.get(url, timeout=10, headers=self._auth_headers())
        r.raise_for_status()
        return r.json()

    def _normalise(self, it: Dict[str, Any]) -> Dict[str, Any]:
        slug = it.get("id") or it.get("slug") or it.get("name")
        name = it.get("name") or slug
        configured = bool(it.get("configured", False))
        needs: List[str] = []

        try:
            schema = self._get_schema(slug)
            fields = schema.get("fields") or []
            needs = [f["name"] for f in fields if f.get("required")]
        except Exception:
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
            seen, uniq = set(), []
            for p in out:
                if p["slug"] in seen:
                    continue
                seen.add(p["slug"])
                uniq.append(p)
            return uniq

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

            url = f"{self.base}/api/v2.0/indexers/{slug}/config"
            r = httpx.post(url, json=payload, timeout=15, headers=self._auth_headers())
            r.raise_for_status()
            return {"slug": slug, "configured": True}
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise PermissionError("auth_failed") from e
            raise
        except ValueError as ve:
            raise ve

    def get_torznab_url(self, slug: str) -> str:
        return f"{self.base}/api/v2.0/indexers/{slug}/results/torznab/"

    def fetch_caps(self, slug: str) -> Dict[str, Any]:
        url = f"{self.get_torznab_url(slug)}api"
        params = {"t": "caps"}
        if JACKETT_API_KEY:
            params["apikey"] = JACKETT_API_KEY
        r = httpx.get(url, params=params, timeout=10)
        r.raise_for_status()
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
        return None

    def remove(self, slug: str) -> None:
        return None

    # ------------ search + metadata ------------
    async def search_with_metadata(
        self,
        query: str,
        limit: int = 40,
        kind: Literal["all", "movie", "tv", "music"] = "all",
    ) -> tuple[list[EnrichedCard], dict[str, Any]]:
        """Run an aggregated Jackett search and enrich the results."""

        meta: dict[str, Any] = {}
        if not JACKETT_API_KEY:
            meta["jackett_ui_url"] = settings.jackett_public_url
            meta["message"] = "Open Jackett to configure trackers"

        torznab_url = f"{self.base}/api/v2.0/indexers/all/results/torznab/"
        try:
            raw_results = await asyncio.to_thread(self._torznab.search, torznab_url, query)
        except Exception as exc:  # defensive log
            logger.warning("jackett search failed query=%s error=%s", query, exc)
            meta["error"] = str(exc)
            return [], meta

        selected = raw_results[:limit]
        cards: list[Optional[EnrichedCard]] = [None] * len(selected)
        enrich_tasks: list[tuple[int, asyncio.Task[EnrichedCard], Classification]] = []

        for idx, item in enumerate(selected):
            title = item.get("title") or ""

            # normalize indexer (string or dict)
            idxr = item.get("indexer")
            if isinstance(idxr, dict):
                _indexer_name = idxr.get("name") or idxr.get("id") or ""
                _indexer_obj = idxr
            else:
                _indexer_name = idxr or ""
                _indexer_obj = None

            classification = self.classifier.classify_torrent(
                title=title,
                jackett_category_desc=item.get("category"),
                indexer_name=_indexer_name,
                indexer=_indexer_obj,
            )

            if title and classification.confidence >= self.classifier.threshold_low:
                enrich_tasks.append(
                    (
                        idx,
                        asyncio.create_task(self.router.enrich(classification, title)),
                        classification,
                    )
                )
            else:
                card = self._build_base_card(classification, title)
                card.reasons.append(
                    f"confidence_below_threshold:{classification.confidence:.2f}"
                )
                cards[idx] = card

        for idx, task, classification in enrich_tasks:
            try:
                card = await task
            except Exception as exc:  # defensive safety
                logger.warning(
                    "metadata enrichment failed title=%s error=%s",
                    selected[idx].get("title"),
                    exc,
                )
                fallback = self._build_base_card(classification, selected[idx].get("title") or "")
                fallback.reasons.append("enrichment_failed")
                fallback.needs_confirmation = True
                card = fallback
            cards[idx] = card

        output_cards: list[EnrichedCard] = []
        for idx, card in enumerate(cards):
            if card is None:
                continue
            item = selected[idx]
            card.details.setdefault("jackett", {}).update(
                {
                    "magnet": item.get("magnet"),
                    "url": item.get("url"),
                    "size": item.get("size"),
                    "seeders": item.get("seeders"),
                    "leechers": item.get("leechers"),
                    "tracker": item.get("tracker"),
                    "indexer": item.get("indexer"),
                    "category": item.get("category"),
                    "title": item.get("title"),
                }
            )
            output_cards.append(card)

        if kind != "all":
            output_cards = [card for card in output_cards if card.media_type == kind]

        return output_cards, meta

    def _build_base_card(self, classification: Classification, title: str) -> EnrichedCard:
        return EnrichedCard(
            media_type=classification.type,
            confidence=classification.confidence,
            title=title,
            ids={},
            details={},
            providers=[],
            reasons=list(classification.reasons),
            needs_confirmation=True,
        )

    def _normalize_basic_result(self, item: dict[str, Any]) -> dict[str, Any]:
        def _as_int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _as_str(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, str):
                trimmed = value.strip()
                return trimmed or None
            return str(value)

        title = _as_str(item.get("title")) or ""
        size_raw = item.get("size")
        size = None
        if size_raw is not None:
            size = str(size_raw)
        tracker_raw = item.get("tracker") or item.get("indexer")
        if isinstance(tracker_raw, dict):
            tracker = _as_str(tracker_raw.get("name") or tracker_raw.get("id"))
        else:
            tracker = _as_str(tracker_raw)
        link = _as_str(item.get("url"))
        return {
            "title": title,
            "size": size,
            "seeders": _as_int(item.get("seeders")),
            "leechers": _as_int(item.get("leechers")),
            "tracker": tracker,
            "magnet": _as_str(item.get("magnet")),
            "link": link,
        }

    async def search(self, query: str, categories: list[int] | None = None) -> list[dict[str, Any]]:
        """Run a lightweight Jackett query returning normalised rows."""

        torznab_url = f"{self.base}/api/v2.0/indexers/all/results/torznab/"
        try:
            raw_results = await asyncio.to_thread(
                self._torznab.search,
                torznab_url,
                query,
                categories,
            )
        except Exception as exc:
            logger.warning("jackett basic search failed query=%s error=%s", query, exc)
            raise

        normalised: list[dict[str, Any]] = []
        for item in raw_results:
            if isinstance(item, dict):
                normalised.append(self._normalize_basic_result(item))
        return normalised

