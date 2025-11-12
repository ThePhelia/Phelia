import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useRef } from 'react';
import MovieCard from '@/app/components/MediaCard/MovieCard';
import TvCard from '@/app/components/MediaCard/TvCard';
import AlbumCard from '@/app/components/MediaCard/AlbumCard';
function RecommendationsRail({ title, items = [] }) {
    const containerRef = useRef(null);
    const handleWheel = (event) => {
        if (!containerRef.current)
            return;
        if (Math.abs(event.deltaX) > Math.abs(event.deltaY))
            return;
        containerRef.current.scrollBy({ left: event.deltaY, behavior: 'smooth' });
    };
    if (!items.length)
        return null;
    return (_jsxs("section", { className: "space-y-3", children: [_jsx("header", { className: "flex items-center justify-between", children: _jsx("h3", { className: "text-lg font-semibold text-foreground", children: title }) }), _jsx("div", { ref: containerRef, onWheel: handleWheel, className: "scrollbar-thin flex gap-4 overflow-x-auto pb-4", children: items.map((item) => {
                    if (item.kind === 'movie') {
                        return (_jsx("div", { className: 'w-[200px] flex-shrink-0', children: _jsx(MovieCard, { item: item }) }, `${item.kind}-${item.id}`));
                    }
                    if (item.kind === 'tv') {
                        return (_jsx("div", { className: 'w-[200px] flex-shrink-0', children: _jsx(TvCard, { item: item }) }, `${item.kind}-${item.id}`));
                    }
                    return (_jsx("div", { className: 'w-[200px] flex-shrink-0', children: _jsx(AlbumCard, { item: item }) }, `${item.kind}-${item.id}`));
                }) })] }));
}
export default RecommendationsRail;
