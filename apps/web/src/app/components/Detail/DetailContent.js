import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import DetailHeader from '@/app/components/Detail/DetailHeader';
import TracksList from '@/app/components/Detail/TracksList';
import SeasonsTabs from '@/app/components/Detail/SeasonsTabs';
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { Badge } from '@/app/components/ui/badge';
import { getSimilarArtists } from '@/app/lib/discovery';
function DetailContent({ detail }) {
    const tabs = useMemo(() => {
        const base = ['overview', 'cast', 'related'];
        if (detail.seasons?.length)
            base.splice(2, 0, 'seasons');
        if (detail.tracks?.length)
            base.splice(2, 0, 'tracks');
        return base;
    }, [detail]);
    const artistMbid = detail.musicbrainz?.artist_id ?? undefined;
    const similarArtistsQuery = useQuery({
        queryKey: ['similar-artists', artistMbid],
        queryFn: () => getSimilarArtists(artistMbid),
        enabled: Boolean(artistMbid),
        staleTime: 6 * 60 * 60 * 1000,
        select: (items) => items.filter((artist) => artist.mbid),
    });
    useEffect(() => {
        if (similarArtistsQuery.error) {
            toast.error('Unable to load similar artists.');
        }
    }, [similarArtistsQuery.error]);
    return (_jsxs("div", { className: "space-y-8", children: [_jsx(DetailHeader, { detail: detail }), _jsxs(Tabs, { defaultValue: tabs[0], className: "w-full", children: [_jsx(TabsList, { className: "flex flex-wrap gap-2", children: tabs.map((tab) => (_jsx(TabsTrigger, { value: tab, className: "capitalize", children: tab }, tab))) }), _jsxs(TabsContent, { value: "overview", className: "space-y-6", children: [_jsxs("section", { className: "grid gap-4 md:grid-cols-[3fr_2fr]", children: [_jsxs("div", { children: [_jsx("h3", { className: "text-lg font-semibold text-foreground", children: "Synopsis" }), _jsx("p", { className: "mt-2 text-sm leading-relaxed text-muted-foreground", children: detail.overview })] }), _jsxs("aside", { className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-4", children: [_jsx("h4", { className: "text-sm font-semibold text-foreground", children: "Availability" }), _jsxs("div", { className: "space-y-3 text-sm text-muted-foreground", children: [_jsxs("div", { children: [_jsx("p", { className: "font-medium text-foreground", children: "Streams" }), _jsx("ul", { className: "mt-1 space-y-1", children: detail.availability?.streams?.length ? (detail.availability.streams.map((stream, index) => (_jsxs("li", { children: [stream.provider, " \u2022 ", stream.quality] }, `${stream.provider}-${index}`)))) : (_jsx("li", { children: "No streams reported." })) })] }), _jsxs("div", { children: [_jsx("p", { className: "font-medium text-foreground", children: "Torrents" }), _jsx("ul", { className: "mt-1 space-y-1", children: detail.availability?.torrents?.length ? (detail.availability.torrents.map((torrent, index) => (_jsxs("li", { children: [torrent.provider, " \u2022 ", torrent.size, " \u2022 ", torrent.seeders, " seeders"] }, `${torrent.provider}-${index}`)))) : (_jsx("li", { children: "No torrents available." })) })] })] })] })] }), detail.links?.external?.length ? (_jsx("div", { className: "flex flex-wrap gap-2 text-xs text-muted-foreground", children: detail.links.external.map((link) => (_jsx("a", { href: link.url, target: "_blank", rel: "noreferrer", className: "rounded-full border border-border/60 px-3 py-1 hover:border-[color:var(--accent)] hover:text-foreground", children: link.label }, link.url))) })) : null] }), _jsx(TabsContent, { value: "cast", children: _jsx("div", { className: "grid gap-4 sm:grid-cols-2 md:grid-cols-3", children: detail.cast?.length ? (detail.cast.map((member) => (_jsxs("div", { className: "flex gap-3 rounded-2xl border border-border/60 bg-background/60 p-3", children: [_jsx("div", { className: "h-14 w-14 overflow-hidden rounded-xl bg-foreground/10", children: member.photo ? (_jsx("img", { src: member.photo, alt: member.name, className: "h-full w-full object-cover" })) : null }), _jsxs("div", { children: [_jsx("p", { className: "text-sm font-semibold text-foreground", children: member.name }), _jsx("p", { className: "text-xs text-muted-foreground", children: member.role })] })] }, member.name)))) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "No cast data." })) }) }), detail.tracks?.length ? (_jsx(TabsContent, { value: "tracks", children: _jsx(TracksList, { tracks: detail.tracks }) })) : null, detail.seasons?.length ? (_jsx(TabsContent, { value: "seasons", children: _jsx(SeasonsTabs, { seasons: detail.seasons }) })) : null, _jsxs(TabsContent, { value: "related", className: "space-y-6", children: [_jsx(RecommendationsRail, { title: "Similar", items: detail.similar }), _jsx(RecommendationsRail, { title: "Recommended", items: detail.recommended }), artistMbid ? (_jsxs("section", { className: "space-y-3", children: [_jsx("h4", { className: "text-sm font-semibold uppercase tracking-wide text-muted-foreground", children: "Similar Artists" }), similarArtistsQuery.isLoading ? (_jsx("p", { className: "text-sm text-muted-foreground", children: "Loading similar artists\u2026" })) : similarArtistsQuery.data?.length ? (_jsx("div", { className: "flex flex-wrap gap-2", children: similarArtistsQuery.data.map((artist) => (_jsxs(Badge, { variant: "outline", className: "rounded-full bg-background/60 px-3 py-1", children: [_jsx("span", { className: "font-medium text-foreground", children: artist.name ?? 'Unknown Artist' }), typeof artist.score === 'number' ? (_jsx("span", { className: "ml-2 text-xs text-muted-foreground", children: artist.score.toFixed(2) })) : null] }, artist.mbid))) })) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "No similar artists available." }))] })) : null] })] })] }));
}
export default DetailContent;
