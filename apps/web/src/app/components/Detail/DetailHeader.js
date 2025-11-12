import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { DownloadCloud, Loader2, Play } from 'lucide-react';
import { useTorrentSearch } from '@/app/stores/torrent-search';
function DetailHeader({ detail }) {
    const fetchTorrents = useTorrentSearch((state) => state.fetchForItem);
    const { isLoading, activeItem } = useTorrentSearch((state) => ({
        isLoading: state.isLoading,
        activeItem: state.activeItem,
    }));
    const isCurrentLoading = isLoading && activeItem?.id === detail.id;
    return (_jsxs("div", { className: "relative overflow-hidden rounded-3xl border border-border/60 bg-background/80", children: [detail.backdrop ? (_jsx("img", { src: detail.backdrop, alt: detail.title, className: "absolute inset-0 h-full w-full object-cover", loading: "lazy" })) : null, _jsx("div", { className: "absolute inset-0 bg-gradient-to-r from-black via-black/80 to-transparent" }), _jsxs("div", { className: "relative z-10 grid gap-6 px-10 py-12 sm:grid-cols-[200px_1fr] sm:items-center", children: [_jsx("div", { className: "mx-auto w-48", children: detail.poster ? (_jsx("img", { src: detail.poster, alt: detail.title, className: "rounded-3xl shadow-lg", loading: "lazy" })) : (_jsx("div", { className: "flex h-64 items-center justify-center rounded-3xl bg-foreground/10 text-muted-foreground", children: "No artwork" })) }), _jsxs("div", { className: "space-y-4 text-white", children: [_jsxs("div", { className: "space-y-2", children: [_jsx("h2", { className: "text-3xl font-bold sm:text-4xl", children: detail.title }), _jsx("p", { className: "text-sm text-white/70", children: [detail.year, detail.tagline].filter(Boolean).join(' • ') }), _jsx("div", { className: "flex flex-wrap gap-2", children: detail.genres?.map((genre) => (_jsx(Badge, { variant: "outline", className: "border-white/30 text-white", children: genre }, genre))) })] }), _jsx("p", { className: "max-w-2xl text-sm leading-relaxed text-white/80", children: detail.overview }), _jsxs("div", { className: "flex flex-wrap items-center gap-3", children: [_jsx(Button, { size: "lg", variant: "accent", className: "rounded-full", disabled: isCurrentLoading, onClick: () => void fetchTorrents({
                                            id: detail.id,
                                            title: detail.title,
                                            kind: detail.kind,
                                            year: detail.year,
                                            artist: detail.kind === 'album' ? detail.tagline : undefined,
                                            subtitle: detail.tagline,
                                        }), children: isCurrentLoading ? (_jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-5 w-5 animate-spin" }), " Fetching\u2026"] })) : (_jsxs(_Fragment, { children: [_jsx(DownloadCloud, { className: "mr-2 h-5 w-5" }), " Fetch Torrents"] })) }), _jsxs(Button, { variant: "secondary", size: "lg", className: "rounded-full bg-white/10 text-white hover:bg-white/20", children: [_jsx(Play, { className: "mr-2 h-5 w-5" }), " Play"] })] })] })] })] }));
}
export default DetailHeader;
