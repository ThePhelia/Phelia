import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { useLibrary } from '@/app/lib/api';
import { Skeleton } from '@/app/components/ui/skeleton';
function LibraryPage() {
    const { data, isLoading, isError } = useLibrary();
    if (isLoading) {
        return (_jsxs("div", { className: "space-y-4", children: [_jsx(Skeleton, { className: "h-8 w-1/3 rounded-full" }), _jsx(Skeleton, { className: "h-48 w-full rounded-3xl" })] }));
    }
    if (isError || !data) {
        return _jsx("p", { className: "text-sm text-muted-foreground", children: "Unable to load your library." });
    }
    return (_jsxs("div", { className: "space-y-10", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "My Library" }), _jsx(RecommendationsRail, { title: "Watchlist", items: data.watchlist }), _jsx(RecommendationsRail, { title: "Favorites", items: data.favorites }), data.playlists?.map((playlist) => (_jsx(RecommendationsRail, { title: playlist.title, items: playlist.items }, playlist.id)))] }));
}
export default LibraryPage;
