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

export async function getGenres(): Promise<DiscoveryGenre[]> {
  const response = await fetch('/api/v1/discovery/genres');
  const data = await parseJson(response);
  return Array.isArray(data?.genres) ? data.genres : [];
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
