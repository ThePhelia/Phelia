import React, { useState } from "react";
import type { EnrichedCard } from "../api";

type Props = {
  card: EnrichedCard;
  onReclassify?: (hint: "music" | "movie" | "tv" | "other") => Promise<void> | void;
  onUseMagnet?: (magnet?: string) => void;
  busy?: boolean;
};

const mediaLabels: Record<EnrichedCard["media_type"], string> = {
  music: "Music",
  movie: "Movie",
  tv: "TV",
  other: "Other",
};

export function ResultCard({ card, onReclassify, onUseMagnet, busy }: Props) {
  const [selectedHint, setSelectedHint] = useState<"music" | "movie" | "tv" | "other">(
    card.media_type,
  );

  const imageUrl =
    card.details?.images?.poster || card.details?.images?.primary || card.details?.discogs?.cover_image;

  const jackettDetails = card.details?.jackett || {};

  async function handleReclassify() {
    if (!onReclassify) return;
    await onReclassify(selectedHint);
  }

  return (
    <div
      style={{
        border: "1px solid #d0d7de",
        borderRadius: 8,
        padding: 16,
        display: "flex",
        gap: 16,
        marginBottom: 16,
      }}
    >
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={card.title}
          style={{ width: 120, height: 180, objectFit: "cover", borderRadius: 4 }}
        />
      ) : (
        <div
          style={{
            width: 120,
            height: 180,
            borderRadius: 4,
            background: "#f6f8fa",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#57606a",
            fontSize: 12,
            textAlign: "center",
            padding: 8,
          }}
        >
          No artwork
        </div>
      )}

      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontWeight: 600,
            }}
          >
            <span
              style={{
                padding: "2px 6px",
                borderRadius: 4,
                background: "#ddf4ff",
                color: "#0550ae",
                fontSize: 12,
                textTransform: "uppercase",
              }}
            >
              {mediaLabels[card.media_type]}
            </span>
            Confidence: {(card.confidence * 100).toFixed(0)}%
          </span>
          {jackettDetails?.magnet && (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                style={{
                  background: "#1f883d",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  padding: "6px 10px",
                  cursor: "pointer",
                }}
                onClick={() => navigator.clipboard.writeText(String(jackettDetails.magnet))}
              >
                Copy magnet
              </button>
              {onUseMagnet && (
                <button
                  style={{
                    background: "#0969da",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    padding: "6px 10px",
                    cursor: "pointer",
                  }}
                  onClick={() => onUseMagnet(String(jackettDetails.magnet))}
                >
                  Use magnet
                </button>
              )}
            </div>
          )}
        </div>

        <h3 style={{ marginTop: 8, marginBottom: 8 }}>{card.title}</h3>
        {card.parsed?.year && (
          <p style={{ marginTop: 0, marginBottom: 4 }}>Year: {card.parsed.year}</p>
        )}
        {card.details?.tmdb?.overview && (
          <p style={{ marginTop: 0, marginBottom: 8, color: "#57606a" }}>{card.details.tmdb.overview}</p>
        )}
        {card.details?.lastfm?.summary && (
          <p style={{ marginTop: 0, marginBottom: 8, color: "#57606a" }}>{card.details.lastfm.summary}</p>
        )}

        <div style={{ marginBottom: 8, fontSize: 12, color: "#57606a" }}>
          Tracker: {jackettDetails?.indexer || jackettDetails?.tracker || "unknown"}
          {jackettDetails?.seeders != null && (
            <>
              {" "}• Seeders: {jackettDetails.seeders}
            </>
          )}
          {jackettDetails?.leechers != null && (
            <>
              {" "}• Leechers: {jackettDetails.leechers}
            </>
          )}
        </div>

        {card.reasons.length > 0 && (
          <div style={{ fontSize: 12, color: "#57606a", marginBottom: 8 }}>
            Reasons: {card.reasons.join(", ")}
          </div>
        )}

        {card.needs_confirmation && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontSize: 13 }}>Unsure? Choose a type:</span>
            <select
              value={selectedHint}
              onChange={(event) =>
                setSelectedHint(event.target.value as "music" | "movie" | "tv" | "other")
              }
            >
              <option value="music">Music</option>
              <option value="movie">Movie</option>
              <option value="tv">TV</option>
              <option value="other">Other</option>
            </select>
            <button
              onClick={handleReclassify}
              disabled={!onReclassify || busy}
              style={{
                background: "#8250df",
                color: "white",
                border: "none",
                borderRadius: 4,
                padding: "6px 10px",
                cursor: onReclassify && !busy ? "pointer" : "default",
                opacity: onReclassify && !busy ? 1 : 0.6,
              }}
            >
              Re-run lookup
            </button>
          </div>
        )}

        {card.providers.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <strong>Providers</strong>
            <ul style={{ marginTop: 6, marginBottom: 0, paddingLeft: 18, fontSize: 12 }}>
              {card.providers.map((provider) => (
                <li key={provider.name}>
                  {provider.name} – {provider.used ? "used" : "skipped"}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResultCard;

