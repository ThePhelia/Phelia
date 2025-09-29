import { SimilarArtist } from './types';

export type AlbumItem = {
  id: string;
  canonical_key: string;
  source: 'lastfm' | 'deezer' | 'itunes' | 'musicbrainz' | 'listenbrainz' | 'spotify';
  title: string;
  artist: string;
  release_date?: string;
  cover_url?: string;
  source_url?: string;
  tags: string[];
  market?: string;
  score?: number;
  preview_url?: string;
  extra?: Record<string, string>;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.set(key, String(value));
      }
    });
  }
  const qs = query.toString();
  const base = API_BASE?.replace(/\/$/, '') ?? '';
  if (base) {
    return `${base}${path}${qs ? `?${qs}` : ''}`;
  }
  return `${path}${qs ? `?${qs}` : ''}`;
}

async function fetchJson<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const response = await fetch(buildUrl(path, params), { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }
  return response.json();
}

export async function fetchDiscoveryNew(market?: string, limit = 50): Promise<AlbumItem[]> {
  return fetchJson('/discovery/new', { market, limit });
}

export async function fetchDiscoveryCharts(market?: string, limit = 50): Promise<AlbumItem[]> {
  return fetchJson('/discovery/charts', { market, limit });
}

export async function fetchDiscoveryTag(tag: string, limit = 50): Promise<AlbumItem[]> {
  return fetchJson('/discovery/tags', { tag, limit });
}

export async function fetchDiscoverySearch(query: string, limit = 25): Promise<AlbumItem[]> {
  return fetchJson('/discovery/search', { q: query, limit });
}

export async function getSimilarArtists(
  artistMbid: string,
  limit = 20,
): Promise<SimilarArtist[]> {
  const response = await fetchJson<{ items: SimilarArtist[] }>('/discovery/similar-artists', {
    artist_mbid: artistMbid,
    limit,
  });
  return response.items;
}

export type DiscoveryProvidersStatus = {
  lastfm: boolean;
  deezer: boolean;
  itunes: boolean;
  musicbrainz: boolean;
  listenbrainz: boolean;
  spotify: boolean;
};

export async function fetchDiscoveryProviders(): Promise<DiscoveryProvidersStatus> {
  return fetchJson('/discovery/providers/status');
}
