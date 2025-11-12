import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Skeleton } from '@/app/components/ui/skeleton';
import { fetchDiscoveryCharts, fetchDiscoveryGenres, fetchDiscoveryNew, fetchDiscoveryProviders, } from '@/app/lib/discovery';
const STATIC_TAGS = ['techno', 'shoegaze', 'hip-hop'];
const FALLBACK_GENRES = STATIC_TAGS.map((tag) => ({
    key: tag,
    label: tag.replace(/\b\w/g, (char) => char.toUpperCase()).replace(/-(\w)/g, (_, letter) => ` ${letter.toUpperCase()}`),
}));
function MusicPage() {
    const [newReleases, setNewReleases] = useState(null);
    const [charts, setCharts] = useState(null);
    const [providers, setProviders] = useState(null);
    const [genres, setGenres] = useState([]);
    const [genresLoading, setGenresLoading] = useState(true);
    const [selectedKey, setSelectedKey] = useState(null);
    const requestRef = useRef(0);
    const selectedGenre = useMemo(() => (selectedKey ? genres.find((genre) => genre.key === selectedKey) ?? null : null), [genres, selectedKey]);
    const loadGenre = useCallback((genre) => {
        const requestId = requestRef.current + 1;
        requestRef.current = requestId;
        if (!genre) {
            setSelectedKey(null);
            setNewReleases([]);
            setCharts([]);
            return;
        }
        setSelectedKey(genre.key);
        setNewReleases(null);
        setCharts(null);
        fetchDiscoveryNew(genre.key, 30)
            .then((items) => {
            if (requestRef.current === requestId) {
                setNewReleases(items);
            }
        })
            .catch(() => {
            if (requestRef.current === requestId) {
                setNewReleases([]);
            }
        });
        fetchDiscoveryCharts(genre.appleGenreId, genre.key, 30)
            .then((items) => {
            if (requestRef.current === requestId) {
                setCharts(items);
            }
        })
            .catch(() => {
            if (requestRef.current === requestId) {
                setCharts([]);
            }
        });
    }, []);
    useEffect(() => {
        fetchDiscoveryProviders()
            .then(setProviders)
            .catch(() => setProviders({
            lastfm: false,
            deezer: false,
            itunes: false,
            musicbrainz: false,
            listenbrainz: false,
            spotify: false,
        }));
    }, []);
    useEffect(() => {
        let cancelled = false;
        setGenresLoading(true);
        fetchDiscoveryGenres()
            .then((list) => {
            if (cancelled) {
                return;
            }
            const normalised = list.length ? list : FALLBACK_GENRES;
            setGenres(normalised);
            loadGenre(normalised[0] ?? null);
        })
            .catch(() => {
            if (cancelled) {
                return;
            }
            setGenres(FALLBACK_GENRES);
            loadGenre(FALLBACK_GENRES[0] ?? null);
        })
            .finally(() => {
            if (!cancelled) {
                setGenresLoading(false);
            }
        });
        return () => {
            cancelled = true;
        };
    }, [loadGenre]);
    return (_jsxs("div", { className: "space-y-12", children: [_jsxs("header", { className: "space-y-2", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "Music Discovery" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Fresh releases and genre shelves aggregated from Last.fm, Deezer, Spotify, iTunes, and MusicBrainz." }), providers ? (_jsxs("p", { className: "text-xs text-muted-foreground", children: ["Providers active:", ' ', Object.entries(providers)
                                .filter(([, enabled]) => enabled)
                                .map(([name]) => name)
                                .join(', ') || 'none'] })) : (_jsx(Skeleton, { className: "h-4 w-40" }))] }), _jsxs("section", { className: "space-y-3", children: [_jsx("div", { className: "flex items-baseline justify-between", children: _jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold text-foreground", children: "Curated Genres" }), _jsx("p", { className: "text-xs uppercase tracking-wide text-muted-foreground", children: "Select a genre to load rails" })] }) }), genresLoading ? (_jsx(Skeleton, { className: "h-10 w-full max-w-md" })) : genres.length ? (_jsx("div", { className: "flex flex-wrap gap-2", children: genres.map((genre) => {
                            const isSelected = genre.key === selectedGenre?.key;
                            return (_jsx(Button, { type: "button", variant: isSelected ? 'default' : 'outline', onClick: () => loadGenre(genre), "aria-pressed": isSelected, children: genre.label }, genre.key));
                        }) })) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "No genres available right now." }))] }), _jsx(DiscoverySection, { title: "New Releases", subtitle: selectedGenre ? selectedGenre.label : 'Select a genre', items: selectedGenre ? newReleases : [] }), _jsx(DiscoverySection, { title: "Top Albums", subtitle: selectedGenre ? `${selectedGenre.label} charts` : 'Select a genre', items: selectedGenre ? charts : [] })] }));
}
function DiscoverySection({ title, subtitle, items, }) {
    return (_jsxs("section", { className: "space-y-3", children: [_jsx("div", { className: "flex items-baseline justify-between", children: _jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold text-foreground", children: title }), _jsx("p", { className: "text-xs uppercase tracking-wide text-muted-foreground", children: subtitle })] }) }), items === null ? (_jsx(Skeleton, { className: "h-48 w-full rounded-3xl" })) : items && items.length ? (_jsx("div", { className: "flex gap-4 overflow-x-auto pb-4", children: items.map((item) => (_jsx(AlbumCard, { item: item }, item.id))) })) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "No results available right now." }))] }));
}
function AlbumCard({ item }) {
    const release = item.release_date;
    return (_jsxs("div", { className: "w-40 flex-shrink-0 space-y-2", children: [_jsx("div", { className: "h-40 w-40 overflow-hidden rounded-xl bg-muted", children: item.cover_url ? (_jsx("img", { src: item.cover_url, alt: item.title, className: "h-full w-full object-cover" })) : (_jsx("div", { className: "flex h-full w-full items-center justify-center text-xs text-muted-foreground", children: "No artwork" })) }), _jsxs("div", { className: "space-y-1", children: [_jsx("p", { className: "truncate text-sm font-semibold text-foreground", children: item.title }), _jsx("p", { className: "truncate text-xs text-muted-foreground", children: item.artist }), release ? (_jsx("p", { className: "text-[10px] uppercase tracking-wide text-muted-foreground", children: release })) : null, item.source ? (_jsx("p", { className: "text-[10px] uppercase tracking-wide text-muted-foreground", children: item.source })) : null] })] }));
}
export default MusicPage;
