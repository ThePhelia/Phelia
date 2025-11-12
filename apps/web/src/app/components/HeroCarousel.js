import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, DownloadCloud, Loader2 } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTorrentSearch } from '@/app/stores/torrent-search';
function HeroCarousel({ items }) {
    const [index, setIndex] = useState(0);
    const navigate = useNavigate();
    const location = useLocation();
    const slides = useMemo(() => items.slice(0, 6), [items]);
    useEffect(() => {
        if (slides.length <= 1)
            return;
        const interval = window.setInterval(() => {
            setIndex((prev) => (prev + 1) % slides.length);
        }, 6000);
        return () => window.clearInterval(interval);
    }, [slides.length]);
    useEffect(() => {
        setIndex(0);
    }, [slides.length]);
    const fetchTorrents = useTorrentSearch((state) => state.fetchForItem);
    const { isLoading, activeItem } = useTorrentSearch((state) => ({
        isLoading: state.isLoading,
        activeItem: state.activeItem,
    }));
    const current = slides[index];
    if (!current)
        return null;
    const imageSrc = current.backdrop ?? current.poster;
    const hasImage = Boolean(imageSrc);
    const isCurrentLoading = isLoading && activeItem?.id === current.id;
    const goTo = (next) => {
        const length = slides.length;
        setIndex((next + length) % length);
    };
    return (_jsxs("div", { className: "relative overflow-hidden rounded-[2.5rem] border border-border/60 bg-background/60 shadow-xl", children: [_jsx(AnimatePresence, { mode: "wait", children: _jsxs(motion.div, { initial: { opacity: 0, scale: 1.02 }, animate: { opacity: 1, scale: 1 }, exit: { opacity: 0, scale: 0.98 }, transition: { duration: 0.6 }, className: "relative h-[360px] md:h-[420px] w-full", children: [hasImage ? (_jsxs(_Fragment, { children: [_jsx("img", { src: imageSrc, alt: current.title, className: "absolute inset-0 h-full w-full object-cover", loading: "lazy" }), _jsx("div", { className: "absolute inset-0 bg-gradient-to-r from-black/80 via-black/60 to-transparent" })] })) : (_jsx("div", { className: "absolute inset-0 bg-gradient-to-br from-foreground/10 via-background/80 to-background" })), _jsxs("div", { className: "relative z-10 flex h-full flex-col justify-center gap-6 px-10 py-12 text-white md:max-w-xl", children: [_jsxs("div", { className: "space-y-3", children: [_jsx("p", { className: "text-xs uppercase tracking-[0.4em] text-white/60", children: "Featured" }), _jsx("h2", { className: "text-2xl font-bold md:text-3xl", children: current.title }), _jsx("p", { className: "text-sm text-white/80 line-clamp-3", children: current.subtitle ?? current.genres?.slice(0, 3).join(' • ') })] }), _jsxs("div", { className: "flex flex-wrap items-center gap-3 text-xs text-white/70", children: [current.year ? _jsx("span", { children: current.year }) : null, current.genres?.slice(0, 2).map((genre) => (_jsx("span", { className: "rounded-full bg-white/10 px-3 py-1", children: genre }, genre)))] }), _jsxs("div", { className: "flex items-center gap-3", children: [_jsx(Button, { size: "lg", variant: "accent", className: "rounded-full shadow-lg", disabled: isCurrentLoading, onClick: () => void fetchTorrents({
                                                id: current.id,
                                                title: current.title,
                                                kind: current.kind,
                                                year: current.year,
                                            }), children: isCurrentLoading ? (_jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-5 w-5 animate-spin" }), " Fetching\u2026"] })) : (_jsxs(_Fragment, { children: [_jsx(DownloadCloud, { className: "mr-2 h-5 w-5" }), " Fetch Torrents"] })) }), _jsx(Button, { variant: "ghost", size: "lg", className: "rounded-full border border-white/30 text-white hover:bg-white/10", onClick: () => navigate(`/details/${current.kind === 'album' ? 'music' : current.kind}/${current.id}`, {
                                                state: { backgroundLocation: location },
                                            }), children: "Learn More" })] })] })] }, current.id) }), slides.length > 1 ? (_jsxs(_Fragment, { children: [_jsx("button", { type: "button", className: "absolute left-6 top-1/2 z-20 -translate-y-1/2 rounded-full border border-white/30 bg-black/60 p-3 text-white transition hover:bg-black/80", onClick: () => goTo(index - 1), children: _jsx(ChevronLeft, { className: "h-5 w-5" }) }), _jsx("button", { type: "button", className: "absolute right-6 top-1/2 z-20 -translate-y-1/2 rounded-full border border-white/30 bg-black/60 p-3 text-white transition hover:bg-black/80", onClick: () => goTo(index + 1), children: _jsx(ChevronRight, { className: "h-5 w-5" }) }), _jsx("div", { className: "absolute bottom-6 left-0 right-0 flex justify-center gap-2", children: slides.map((slide, slideIndex) => (_jsx("button", { type: "button", className: `h-2 w-8 rounded-full transition ${slideIndex === index ? 'bg-white' : 'bg-white/30'}`, onClick: () => goTo(slideIndex), "aria-label": `Go to slide ${slideIndex + 1}` }, slide.id))) })] })) : null] }));
}
export default HeroCarousel;
