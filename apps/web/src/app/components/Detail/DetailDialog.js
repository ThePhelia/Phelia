import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { Loader2, Clock3, Star, Search, X } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogClose, DialogContent, DialogFooter } from '@/app/components/ui/dialog';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Skeleton } from '@/app/components/ui/skeleton';
import DetailContent from '@/app/components/Detail/DetailContent';
import { useDetails, useMetaDetail } from '@/app/lib/api';
import { useTorrentSearch } from '@/app/stores/torrent-search';
function LoadingState() {
    return (_jsxs("div", { className: "space-y-6", children: [_jsxs("div", { className: "space-y-3", children: [_jsx(Skeleton, { className: "h-7 w-3/4" }), _jsx(Skeleton, { className: "h-4 w-1/2" })] }), _jsxs("div", { className: "grid gap-4 md:grid-cols-[2fr_3fr]", children: [_jsx(Skeleton, { className: "aspect-[2/3] w-full rounded-3xl" }), _jsxs("div", { className: "space-y-3", children: [_jsx(Skeleton, { className: "h-4 w-full" }), _jsx(Skeleton, { className: "h-4 w-5/6" }), _jsx(Skeleton, { className: "h-4 w-2/3" })] })] })] }));
}
function ErrorState({ message = 'Failed to load details.' }) {
    return (_jsxs("div", { className: "space-y-2 text-center", children: [_jsx("p", { className: "text-lg font-semibold text-foreground", children: message }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Please try again later." })] }));
}
function DetailDialog({ kind, id, provider, open, onOpenChange }) {
    const isMetaFlow = Boolean(provider);
    const { data, isLoading, isError } = useDetails(kind, id);
    const fallbackMetaParams = useMemo(() => {
        if (isMetaFlow || !data)
            return undefined;
        const parsed = parseScopedIdentifier(data.title ?? data.id);
        if (!parsed)
            return undefined;
        const missingOverview = !data.overview || data.overview.trim().length === 0;
        const placeholderTitle = isPlaceholderTitle(data.title, data.id);
        if (!missingOverview && !placeholderTitle) {
            return undefined;
        }
        return parsed;
    }, [data, isMetaFlow]);
    const metaDetailParams = isMetaFlow
        ? { type: kind, id, provider: provider }
        : fallbackMetaParams
            ? { type: fallbackMetaParams.type, id: fallbackMetaParams.id, provider: fallbackMetaParams.provider }
            : { type: kind, id: '', provider: '' };
    const { data: metaDetail, isLoading: isMetaLoading, isError: isMetaError, } = useMetaDetail(metaDetailParams);
    const fallbackDetail = useMemo(() => {
        if (isMetaFlow || !fallbackMetaParams || !metaDetail)
            return undefined;
        return metaDetailToDetailResponse(metaDetail, id);
    }, [fallbackMetaParams, id, isMetaFlow, metaDetail]);
    const mergedDetail = useMemo(() => mergeDetailData(data, fallbackDetail), [data, fallbackDetail]);
    const [season, setSeason] = useState('');
    const [episode, setEpisode] = useState('');
    const [hasSearched, setHasSearched] = useState(false);
    const [isIndexing, setIsIndexing] = useState(false);
    const [lastQuery, setLastQuery] = useState('');
    const fetchTorrentSearch = useTorrentSearch((state) => state.fetchForQuery);
    useEffect(() => {
        if (!isMetaFlow || !metaDetail)
            return;
        const canonicalTv = metaDetail.canonical.tv;
        setSeason(canonicalTv && typeof canonicalTv.season === 'number' && canonicalTv.season > 0 ? canonicalTv.season : '');
        setEpisode(canonicalTv && typeof canonicalTv.episode === 'number' && canonicalTv.episode > 0 ? canonicalTv.episode : '');
        setHasSearched(false);
        setLastQuery('');
    }, [isMetaFlow, metaDetail]);
    const handleFindTorrents = async () => {
        if (!isMetaFlow || !metaDetail)
            return;
        const seasonNumber = season === '' ? null : Number(season);
        const episodeNumber = episode === '' ? null : Number(episode);
        setHasSearched(false);
        setLastQuery('');
        setIsIndexing(true);
        try {
            const baseTitle = metaDetail.title.trim();
            const context = {
                id,
                title: baseTitle,
                kind: metaDetail.type,
                year: typeof metaDetail.year === 'number' ? metaDetail.year : undefined,
                artist: metaDetail.album?.artist,
                subtitle: metaDetail.album?.artist,
            };
            const queryParts = [];
            if (metaDetail.type === 'album') {
                const artist = context.artist ?? '';
                const normalized = artist ? `${artist} - ${baseTitle}` : baseTitle;
                if (normalized) {
                    queryParts.push(normalized);
                }
            }
            else if (baseTitle) {
                queryParts.push(baseTitle);
            }
            if (typeof metaDetail.year === 'number') {
                queryParts.push(String(metaDetail.year));
            }
            if (metaDetail.type === 'tv') {
                const seasonLabel = seasonNumber ? `S${String(seasonNumber).padStart(2, '0')}` : '';
                const episodeLabel = episodeNumber ? `E${String(episodeNumber).padStart(2, '0')}` : '';
                const combined = `${seasonLabel}${episodeLabel}`.trim();
                if (combined) {
                    queryParts.push(combined);
                }
            }
            const query = queryParts.filter(Boolean).join(' ').trim();
            setLastQuery(query);
            setHasSearched(true);
            await fetchTorrentSearch(query, context);
        }
        catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to search torrents';
            toast.error(message);
        }
        finally {
            setIsIndexing(false);
        }
    };
    const content = useMemo(() => {
        if (isMetaFlow) {
            if (isMetaLoading)
                return _jsx(LoadingState, {});
            if (isMetaError || !metaDetail)
                return _jsx(ErrorState, {});
            return (_jsx(MetaDetailContent, { detail: metaDetail, season: season, episode: episode, setSeason: setSeason, setEpisode: setEpisode, onFindTorrents: handleFindTorrents, isIndexing: isIndexing, hasSearched: hasSearched, lastQuery: lastQuery }));
        }
        const waitingForFallback = Boolean(fallbackMetaParams) && !fallbackDetail && isMetaLoading;
        if (isLoading || waitingForFallback)
            return _jsx(LoadingState, {});
        const encounteredError = isError || (Boolean(fallbackMetaParams) && isMetaError);
        if (encounteredError || !mergedDetail)
            return _jsx(ErrorState, {});
        return _jsx(DetailContent, { detail: mergedDetail });
    }, [
        isMetaFlow,
        isMetaLoading,
        isMetaError,
        metaDetail,
        season,
        episode,
        handleFindTorrents,
        isIndexing,
        hasSearched,
        lastQuery,
        fallbackMetaParams,
        fallbackDetail,
        isLoading,
        isMetaLoading,
        isError,
        mergedDetail,
    ]);
    return (_jsx(Dialog, { open: open, onOpenChange: onOpenChange, children: _jsxs(DialogContent, { className: "relative w-full max-w-4xl lg:max-w-5xl p-6 sm:p-10", children: [_jsxs(DialogClose, { className: "absolute right-6 top-6 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-background/80 text-muted-foreground transition hover:text-foreground sm:right-8 sm:top-8", children: [_jsx(X, { className: "h-4 w-4" }), _jsx("span", { className: "sr-only", children: "Close" })] }), content, _jsx(DialogFooter, { className: "mt-8 px-0 pb-0 pt-6 sm:mt-10 sm:px-0 sm:pt-8", children: _jsx(Button, { variant: "secondary", onClick: () => onOpenChange(false), children: "Close" }) })] }) }));
}
function MetaDetailContent({ detail, season, episode, setSeason, setEpisode, onFindTorrents, isIndexing, hasSearched, lastQuery, }) {
    const cast = detail.cast.slice(0, 6);
    const tracklist = detail.album?.tracklist ?? [];
    return (_jsxs("div", { className: "space-y-6", children: [_jsxs("div", { className: "grid gap-6 md:grid-cols-[200px_1fr]", children: [_jsx("div", { className: "overflow-hidden rounded-3xl border border-border/60 bg-muted/40", children: detail.poster ? (_jsx("img", { src: detail.poster, alt: detail.title, className: "h-full w-full object-cover" })) : (_jsx("div", { className: "flex h-full items-center justify-center p-6 text-sm text-muted-foreground", children: "No artwork" })) }), _jsxs("div", { className: "space-y-4", children: [_jsxs("div", { children: [_jsxs("h2", { className: "text-2xl font-semibold text-foreground", children: [detail.title, detail.year ? _jsxs("span", { className: "text-muted-foreground", children: [" (", detail.year, ")"] }) : null] }), _jsxs("div", { className: "mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground", children: [detail.runtime ? (_jsxs("span", { className: "flex items-center gap-1", children: [_jsx(Clock3, { className: "h-4 w-4" }), detail.type === 'tv' ? `${detail.runtime} min / episode` : `${detail.runtime} min`] })) : null, typeof detail.rating === 'number' ? (_jsxs("span", { className: "flex items-center gap-1", children: [_jsx(Star, { className: "h-4 w-4 text-yellow-400" }), detail.rating.toFixed(1)] })) : null, detail.genres.map((genre) => (_jsx("span", { className: "rounded-full bg-foreground/10 px-2 py-1", children: genre }, genre)))] })] }), _jsx("p", { className: "text-sm leading-relaxed text-muted-foreground", children: detail.synopsis || 'No synopsis available yet.' }), cast.length ? (_jsxs("div", { className: "space-y-2", children: [_jsx("h3", { className: "text-sm font-semibold text-foreground", children: "Top cast" }), _jsx("div", { className: "flex flex-wrap gap-3 text-xs text-muted-foreground", children: cast.map((member) => (_jsxs("span", { className: "rounded-full bg-foreground/10 px-3 py-1", children: [member.name, member.character ? _jsxs("span", { className: "text-muted-foreground/70", children: [" as ", member.character] }) : null] }, member.name))) })] })) : null, detail.type === 'tv' ? (_jsxs("div", { className: "space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4", children: [_jsx("h3", { className: "text-sm font-semibold text-foreground", children: "Refine episode search" }), _jsxs("div", { className: "grid grid-cols-2 gap-3", children: [_jsxs("label", { className: "text-xs text-muted-foreground", children: ["Season", _jsx(Input, { type: "number", min: 1, value: season, onChange: (event) => {
                                                            const value = event.target.value;
                                                            setSeason(value === '' ? '' : Number(value));
                                                        }, className: "mt-1" })] }), _jsxs("label", { className: "text-xs text-muted-foreground", children: ["Episode", _jsx(Input, { type: "number", min: 1, value: episode, onChange: (event) => {
                                                            const value = event.target.value;
                                                            setEpisode(value === '' ? '' : Number(value));
                                                        }, className: "mt-1" })] })] })] })) : null, detail.type === 'album' && tracklist.length ? (_jsxs("div", { className: "space-y-2", children: [_jsx("h3", { className: "text-sm font-semibold text-foreground", children: "Tracklist" }), _jsx("div", { className: "max-h-48 space-y-1 overflow-y-auto rounded-2xl border border-border/60 bg-background/60 p-3 text-xs text-muted-foreground", children: tracklist.map((track) => (_jsxs("div", { className: "flex items-center justify-between gap-3", children: [_jsxs("span", { children: [track.position ? `${track.position} ` : null, track.title] }), track.duration ? _jsx("span", { className: "font-mono text-muted-foreground/80", children: track.duration }) : null] }, `${track.position}-${track.title}`))) })] })) : null, detail.album?.styles?.length ? (_jsx("div", { className: "flex flex-wrap gap-2 text-xs text-muted-foreground", children: detail.album.styles.map((style) => (_jsx("span", { className: "rounded-full bg-foreground/10 px-2 py-1", children: style }, style))) })) : null, _jsxs("div", { className: "flex flex-wrap items-center gap-3", children: [_jsxs(Button, { onClick: onFindTorrents, disabled: isIndexing, className: "flex items-center gap-2", children: [isIndexing ? _jsx(Loader2, { className: "h-4 w-4 animate-spin" }) : _jsx(Search, { className: "h-4 w-4" }), isIndexing ? 'Searching…' : 'Find Torrents'] }), lastQuery ? (_jsxs("span", { className: "text-xs text-muted-foreground", children: ["Query: ", _jsx("span", { className: "font-mono text-foreground/80", children: lastQuery })] })) : null] })] })] }), isIndexing ? (_jsxs("div", { className: "flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-sm text-muted-foreground", children: [_jsx(Loader2, { className: "h-6 w-6 animate-spin text-[color:var(--accent)]" }), " Searching torrents\u2026"] })) : hasSearched ? (_jsxs("div", { className: "space-y-2 rounded-2xl border border-border/60 bg-background/60 p-6 text-sm text-muted-foreground", children: [_jsx("p", { children: "Torrent results have been opened in the Torrent results window." }), _jsx("p", { className: "text-xs text-muted-foreground/80", children: "Use the Download window to send a torrent to your client or copy its source." })] })) : null] }));
}
function parseScopedIdentifier(value) {
    if (!value)
        return undefined;
    const parts = value.split(':');
    if (parts.length < 3)
        return undefined;
    const [provider, rawType, ...rest] = parts;
    const identifier = rest.join(':');
    if (!provider || !rawType || !identifier)
        return undefined;
    const normalizedType = rawType.toLowerCase() === 'music' ? 'album' : rawType.toLowerCase();
    if (normalizedType !== 'movie' && normalizedType !== 'tv' && normalizedType !== 'album') {
        return undefined;
    }
    return { provider, type: normalizedType, id: identifier };
}
function isPlaceholderTitle(title, id) {
    if (!title)
        return true;
    if (id && title === id)
        return true;
    const parts = title.split(':');
    return parts.length >= 3 && parts[0].length <= 10 && parts[1].length <= 10;
}
function mergeDetailData(primary, fallback) {
    if (!primary && !fallback)
        return undefined;
    if (!fallback)
        return primary;
    if (!primary)
        return fallback;
    const merged = {
        ...fallback,
        ...primary,
        id: primary.id ?? fallback.id,
        kind: primary.kind ?? fallback.kind,
        title: isPlaceholderTitle(primary.title, primary.id) ? fallback.title : primary.title,
        year: primary.year ?? fallback.year,
        tagline: primary.tagline || fallback.tagline,
        overview: primary.overview || fallback.overview,
        poster: primary.poster || fallback.poster,
        backdrop: primary.backdrop || fallback.backdrop,
        rating: primary.rating ?? fallback.rating,
        genres: primary.genres && primary.genres.length > 0
            ? primary.genres
            : fallback.genres,
        cast: primary.cast && primary.cast.length > 0 ? primary.cast : fallback.cast,
        crew: primary.crew && primary.crew.length > 0 ? primary.crew : fallback.crew,
        tracks: primary.tracks && primary.tracks.length > 0 ? primary.tracks : fallback.tracks,
        seasons: primary.seasons && primary.seasons.length > 0 ? primary.seasons : fallback.seasons,
        similar: primary.similar && primary.similar.length > 0 ? primary.similar : fallback.similar,
        recommended: primary.recommended && primary.recommended.length > 0
            ? primary.recommended
            : fallback.recommended,
        links: primary.links ?? fallback.links,
        availability: primary.availability ?? fallback.availability,
    };
    if (!merged.genres) {
        merged.genres = [];
    }
    return merged;
}
function metaDetailToDetailResponse(metaDetail, fallbackId) {
    const kind = metaDetail.type === 'album' ? 'album' : metaDetail.type;
    const genres = [...(metaDetail.genres ?? [])];
    if (metaDetail.album?.styles?.length) {
        for (const style of metaDetail.album.styles) {
            if (!genres.includes(style)) {
                genres.push(style);
            }
        }
    }
    const tracks = metaDetail.album?.tracklist?.map((track, index) => ({
        index: index + 1,
        title: track.title,
    }));
    return {
        id: fallbackId,
        kind,
        title: metaDetail.title,
        year: typeof metaDetail.year === 'number' ? metaDetail.year : undefined,
        tagline: metaDetail.album?.artist ?? undefined,
        overview: metaDetail.synopsis ?? undefined,
        poster: metaDetail.poster ?? undefined,
        backdrop: metaDetail.backdrop ?? undefined,
        rating: typeof metaDetail.rating === 'number' ? metaDetail.rating : undefined,
        genres,
        cast: metaDetail.cast.map((member) => ({
            name: member.name,
            role: member.character ?? undefined,
        })),
        crew: [],
        tracks: tracks && tracks.length > 0 ? tracks : undefined,
        seasons: undefined,
        similar: [],
        recommended: [],
        links: undefined,
        availability: undefined,
    };
}
export default DetailDialog;
