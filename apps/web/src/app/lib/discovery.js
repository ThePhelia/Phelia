function buildUrl(path, params) {
    const query = new URLSearchParams();
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                query.set(key, String(value));
            }
        });
    }
    const qs = query.toString();
    const rawBase = import.meta.env.VITE_API_BASE ?? '';
    const normalisedBase = rawBase.replace(/\/+$/, '');
    const normalisedPath = path.replace(/^\/+/, '');
    let url = normalisedPath;
    if (normalisedBase) {
        const baseWithSlash = `${normalisedBase}/`;
        url = normalisedPath ? `${baseWithSlash}${normalisedPath}` : baseWithSlash;
    }
    return `${url}${qs ? `?${qs}` : ''}`;
}
async function fetchJson(path, params) {
    const response = await fetch(buildUrl(path, params), { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`Failed to fetch ${path}: ${response.status}`);
    }
    return response.json();
}
function normaliseAlbumItem(entry) {
    if (!entry || typeof entry !== 'object') {
        return null;
    }
    const value = entry;
    const idSource = value.id ??
        value.mbid ??
        value.mbid ??
        value.slug ??
        value.key ??
        (typeof value.title === 'string' ? `${value.title}:${value.artist ?? ''}` : undefined);
    const id = String(idSource ?? Math.random().toString(36).slice(2));
    const title = String(value.title ?? value.name ?? 'Untitled');
    const artist = String(value.artist ?? value.artistName ?? value.creator ?? 'Unknown Artist');
    const coverCandidate = value.cover_url ??
        value.cover ??
        value.artwork ??
        value.image ??
        value.coverImage ??
        value.image_url;
    const releaseCandidate = value.release_date ??
        value.releaseDate ??
        value.year ??
        value.firstReleaseDate ??
        value.first_release_date;
    const sourceCandidate = value.source ?? value.provider ?? value.origin ?? value.storefront;
    return {
        id,
        title,
        artist,
        cover_url: typeof coverCandidate === 'string' ? coverCandidate : undefined,
        release_date: typeof releaseCandidate === 'number'
            ? String(releaseCandidate)
            : typeof releaseCandidate === 'string'
                ? releaseCandidate
                : undefined,
        source: typeof sourceCandidate === 'string' ? sourceCandidate : undefined,
    };
}
function extractItems(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (payload && typeof payload === 'object') {
        const value = payload;
        if (Array.isArray(value.items)) {
            return value.items;
        }
    }
    return [];
}
function normaliseGenres(payload) {
    const entries = extractItems(payload);
    return entries
        .map((entry) => {
        if (!entry || typeof entry !== 'object') {
            return null;
        }
        const value = entry;
        const key = value.key ?? value.slug ?? value.id ?? value.genre;
        if (typeof key !== 'string' || !key.trim()) {
            return null;
        }
        const label = typeof value.label === 'string'
            ? value.label
            : typeof value.name === 'string'
                ? value.name
                : key.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const appleGenreId = typeof value.appleGenreId === 'number'
            ? value.appleGenreId
            : typeof value.apple_genre_id === 'number'
                ? value.apple_genre_id
                : undefined;
        const genre = { key, label };
        if (appleGenreId !== undefined) {
            genre.appleGenreId = appleGenreId;
        }
        return genre;
    })
        .filter((genre) => genre !== null);
}
export async function fetchDiscoveryGenres() {
    try {
        const payload = await fetchJson('discovery/genres');
        const genres = normaliseGenres(payload);
        if (genres.length) {
            return genres;
        }
        if (payload && typeof payload === 'object') {
            const value = payload;
            if (Array.isArray(value.genres)) {
                return normaliseGenres(value.genres);
            }
        }
    }
    catch (error) {
        // swallow and fall back to defaults
    }
    return [];
}
export async function fetchDiscoveryNew(genre, limit = 24, days = 30) {
    const payload = await fetchJson('discovery/new', { genre, limit, days });
    return extractItems(payload)
        .map(normaliseAlbumItem)
        .filter((item) => Boolean(item));
}
export async function fetchDiscoveryCharts(genreId, genre, limit = 24) {
    const payload = await fetchJson('discovery/top', {
        genre_id: genreId,
        genre,
        kind: 'albums',
        feed: 'most-recent',
        limit,
    });
    return extractItems(payload)
        .map(normaliseAlbumItem)
        .filter((item) => Boolean(item));
}
export async function fetchDiscoveryTag(tag, limit = 24) {
    return fetchDiscoveryNew(tag, limit);
}
export async function fetchDiscoverySearch(query, limit = 25) {
    const payload = await fetchJson('discovery/search', { q: query, limit });
    return extractItems(payload)
        .map(normaliseAlbumItem)
        .filter((item) => Boolean(item));
}
export async function getSimilarArtists(artistMbid, limit = 20) {
    const response = await fetchJson('discovery/similar-artists', {
        artist_mbid: artistMbid,
        limit,
    });
    return response.items;
}
export async function fetchDiscoveryProviders() {
    return fetchJson('providers/status');
}
