import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import MovieCard from '@/app/components/MediaCard/MovieCard';
import TvCard from '@/app/components/MediaCard/TvCard';
import AlbumCard from '@/app/components/MediaCard/AlbumCard';
import { useKeyboardGridNav } from '@/app/hooks/useKeyboardGridNav';
import { Skeleton } from '@/app/components/ui/skeleton';
function CatalogGrid({ items, loading, hasNextPage, fetchNextPage }) {
    const { getItemProps } = useKeyboardGridNav(items.length, { columns: 6 });
    const loaderRef = useRef(null);
    useEffect(() => {
        if (!fetchNextPage || !hasNextPage)
            return;
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    void fetchNextPage();
                }
            });
        }, { rootMargin: '400px' });
        const node = loaderRef.current;
        if (node)
            observer.observe(node);
        return () => observer.disconnect();
    }, [fetchNextPage, hasNextPage]);
    const cards = useMemo(() => {
        return items.map((item, index) => {
            const { ref, ...keyboardProps } = getItemProps(index);
            const card = (() => {
                if (item.kind === 'movie')
                    return _jsx(MovieCard, { item: item });
                if (item.kind === 'tv')
                    return _jsx(TvCard, { item: item });
                return _jsx(AlbumCard, { item: item });
            })();
            return (_jsx("div", { ref: ref, ...keyboardProps, className: "focus-visible:outline-none", children: card }, `${item.kind}-${item.id}`));
        });
    }, [getItemProps, items]);
    return (_jsxs("div", { className: "space-y-6", children: [_jsxs("div", { className: "grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6", children: [cards, loading && items.length === 0
                        ? Array.from({ length: 12 }).map((_, index) => (_jsxs("div", { className: "flex flex-col gap-3", children: [_jsx(Skeleton, { className: "aspect-[2/3] w-full rounded-3xl" }), _jsx(Skeleton, { className: "h-4 w-3/4 rounded-full" }), _jsx(Skeleton, { className: "h-3 w-1/2 rounded-full" })] }, `skeleton-${index}`)))
                        : null] }), hasNextPage ? (_jsx("div", { ref: loaderRef, className: "flex items-center justify-center py-6 text-sm text-muted-foreground", children: loading ? (_jsxs(_Fragment, { children: [_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), " Loading more"] })) : ('Scroll to load more') })) : null] }));
}
export default CatalogGrid;
