export interface DiscoveryGenre {
  key: string;
  label: string;
  appleGenreId: number;
}

async function parseJson(response: Response) {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

const CURATED_FALLBACK: DiscoveryGenre[] = [
  { key: 'techno', label: 'Techno', appleGenreId: 718 },
  { key: 'house', label: 'House', appleGenreId: 1250 },
  { key: 'dnb', label: 'Drum & Bass', appleGenreId: 1253 },
  { key: 'ambient', label: 'Ambient', appleGenreId: 502 },
  { key: 'rock', label: 'Rock', appleGenreId: 21 },
  { key: 'pop', label: 'Pop', appleGenreId: 14 },
  { key: 'hip-hop', label: 'Hip-Hop', appleGenreId: 18 },
  { key: 'jazz', label: 'Jazz', appleGenreId: 11 },
  { key: 'metal', label: 'Metal', appleGenreId: 1153 },
  { key: 'indie', label: 'Indie', appleGenreId: 20 },
  { key: 'classical', label: 'Classical', appleGenreId: 5 },
];

export async function getGenres(): Promise<DiscoveryGenre[]> {
  try {
    const response = await fetch('/api/v1/discovery/genres');
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    const data = await response.json();
    const genres = Array.isArray(data?.genres) ? data.genres : [];
    return genres.length ? genres : CURATED_FALLBACK;
  } catch (error) {
    console.warn('Falling back to curated genres', error);
    return CURATED_FALLBACK;
  }
}

export async function getNew(genre: string, days = 30, limit = 50) {
  const params = new URLSearchParams({
    genre,
    days: String(days),
    limit: String(limit),
  });
  const response = await fetch(`/api/v1/discovery/new?${params.toString()}`);
  const data = await parseJson(response);
  return Array.isArray(data?.items) ? data.items : [];
}

export async function getTop(
  genreId: number,
  feed = 'most-recent',
  kind = 'albums',
  limit = 50,
  storefront?: string,
) {
  const params = new URLSearchParams({
    feed,
    kind,
    limit: String(limit),
    genre_id: String(genreId),
  });
  if (storefront) {
    params.append('storefront', storefront);
  }
  const response = await fetch(`/api/v1/discovery/top?${params.toString()}`);
  const data = await parseJson(response);
  return Array.isArray(data?.items) ? data.items : [];
}

export async function getSimilarArtists(artistMbid: string, limit = 20) {
  const params = new URLSearchParams({
    artist_mbid: artistMbid,
    limit: String(limit),
  });
  const response = await fetch(`/api/v1/discovery/similar-artists?${params.toString()}`);
  const data = await parseJson(response);
  return Array.isArray(data?.items) ? data.items : [];
}
