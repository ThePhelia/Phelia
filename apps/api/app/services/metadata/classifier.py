"""Deterministic torrent classifier using lightweight heuristics."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, Literal, Optional

from app.schemas.media import Classification

MediaType = Literal["music", "movie", "tv", "other"]


class Classifier:
    """Apply heuristic scoring to Torznab/Jackett search results.

    The classifier is intentionally deterministic and explainable.  Each
    heuristic contributes a weighted vote to one of the supported media
    types.  The final classification is selected via argmax with the
    reported confidence derived from the weight distribution.
    """

    category_weights: Dict[str, tuple[MediaType, float]]
    indexer_priors: Dict[str, tuple[MediaType, float]]
    threshold_low: float

    music_tokens: Iterable[tuple[re.Pattern[str], float, str]]
    tv_tokens: Iterable[tuple[re.Pattern[str], float, str]]
    movie_tokens: Iterable[tuple[re.Pattern[str], float, str]]

    def __init__(self, threshold_low: float = 0.55) -> None:
        self.threshold_low = threshold_low
        # Common Torznab category labels.  Mapping is substring based so
        # we normalise to lowercase before matching.
        self.category_weights = {
            "movies": ("movie", 0.9),
            "movie": ("movie", 0.9),
            "films": ("movie", 0.9),
            "tv": ("tv", 0.9),
            "television": ("tv", 0.9),
            "series": ("tv", 0.6),
            "audio": ("music", 0.9),
            "music": ("music", 0.9),
            "mp3": ("music", 0.8),
            "flac": ("music", 0.8),
        }

        # Prior knowledge about popular music indexers helps the model
        # converge quickly even when the torrent title is ambiguous.
        self.indexer_priors = {
            "redacted": ("music", 0.95),
            "orpheus": ("music", 0.95),
            "broadcasthenet": ("tv", 0.75),
        }

        self.music_tokens = [
            (re.compile(r"\bFLAC\b", re.I), 0.5, "FLAC token"),
            (re.compile(r"\bAPE\b", re.I), 0.5, "APE token"),
            (re.compile(r"\bALAC\b", re.I), 0.5, "ALAC token"),
            (re.compile(r"\bMP3\b", re.I), 0.45, "MP3 token"),
            (re.compile(r"\bV(?:0|2)\b", re.I), 0.4, "VBR token"),
            (re.compile(r"\b320kbps\b", re.I), 0.45, "320kbps token"),
            (re.compile(r"\bVinyl\b", re.I), 0.45, "Vinyl token"),
            (re.compile(r"\bSACD\b", re.I), 0.5, "SACD token"),
            (re.compile(r"\b24bit\b", re.I), 0.45, "24bit token"),
            (re.compile(r"\b16bit\b", re.I), 0.3, "16bit token"),
            (re.compile(r"\bCUE\b", re.I), 0.3, "CUE token"),
            (re.compile(r"\bLOG\b", re.I), 0.3, "LOG token"),
            (
                re.compile(r"^[\w .'-]+ - [\w .'-]+ \((19|20)\d{2}\)", re.I),
                0.55,
                "Artist - Album pattern",
            ),
        ]

        self.tv_tokens = [
            (re.compile(r"S\d{1,2}E\d{1,2}", re.I), 0.45, "SxxEyy pattern"),
            (re.compile(r"Season\s+\d+", re.I), 0.4, "Season pattern"),
            (re.compile(r"Episode\s+\d+", re.I), 0.35, "Episode pattern"),
            (re.compile(r"E\d{2}\b", re.I), 0.25, "Episode shorthand"),
            (re.compile(r"Complete Series", re.I), 0.4, "Complete series"),
        ]

        self.movie_tokens = [
            (re.compile(r"(19|20)\d{2}"), 0.3, "Year token"),
            (re.compile(r"\b2160p\b", re.I), 0.35, "2160p token"),
            (re.compile(r"\b1080p\b", re.I), 0.3, "1080p token"),
            (re.compile(r"\b720p\b", re.I), 0.25, "720p token"),
            (re.compile(r"x264", re.I), 0.3, "x264 token"),
            (re.compile(r"x265", re.I), 0.3, "x265 token"),
            (re.compile(r"HEVC", re.I), 0.3, "HEVC token"),
            (re.compile(r"BluRay", re.I), 0.3, "BluRay token"),
            (re.compile(r"WEB[- ]?DL", re.I), 0.3, "WEB-DL token"),
            (re.compile(r"REMUX", re.I), 0.35, "REMUX token"),
            (re.compile(r"HDR\b", re.I), 0.25, "HDR token"),
            (re.compile(r"\bDV\b", re.I), 0.25, "Dolby Vision token"),
        ]

    def classify_torrent(
        self,
        title: str,
        jackett_category_desc: Optional[str] = None,
        indexer_name: Optional[str] = None,
    ) -> Classification:
        """Return a :class:`Classification` for the provided torrent."""

        normalized_title = title or ""
        category = (jackett_category_desc or "").lower()
        indexer = (indexer_name or "").lower()

        scores: Dict[MediaType, float] = defaultdict(float)
        total_weight = 0.0
        reasons: list[str] = []

        # Category signals
        for needle, (media_type, weight) in self.category_weights.items():
            if needle in category:
                scores[media_type] += weight
                total_weight += weight
                reasons.append(f"category:{needle}")

        # Indexer priors
        if indexer and indexer in self.indexer_priors:
            media_type, weight = self.indexer_priors[indexer]
            scores[media_type] += weight
            total_weight += weight
            reasons.append(f"indexer_prior:{indexer}")

        def _apply(patterns: Iterable[tuple[re.Pattern[str], float, str]], media_type: MediaType) -> None:
            nonlocal total_weight
            for regex, weight, label in patterns:
                if regex.search(normalized_title):
                    scores[media_type] += weight
                    total_weight += weight
                    reasons.append(f"title:{label}")

        _apply(self.music_tokens, "music")
        _apply(self.tv_tokens, "tv")
        _apply(self.movie_tokens, "movie")

        if total_weight <= 0.0:
            reasons.append("no_signals")
            return Classification(type="other", confidence=0.0, reasons=reasons)

        # Pick the best scoring type; use deterministic order for ties.
        ordering = ["music", "movie", "tv", "other"]
        best_media = max(ordering, key=lambda m: (scores[m], -ordering.index(m)))
        best_score = scores[best_media]
        confidence = best_score / total_weight if total_weight else 0.0

        return Classification(type=best_media, confidence=min(confidence, 1.0), reasons=reasons)


__all__ = ["Classifier"]

