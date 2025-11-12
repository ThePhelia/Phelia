import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import HeroCarousel from '@/app/components/HeroCarousel';
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { useDiscover } from '@/app/lib/api';
function HomePage() {
    const movies = useDiscover('movie', { sort: 'trending' });
    const tv = useDiscover('tv', { sort: 'popular' });
    const music = useDiscover('album', { sort: 'new' });
    const heroItems = movies.data?.pages?.[0]?.items ?? [];
    return (_jsxs("div", { className: "space-y-12", children: [_jsx("section", { children: heroItems.length ? _jsx(HeroCarousel, { items: heroItems.slice(0, 6) }) : null }), _jsx(RecommendationsRail, { title: "Continue Watching", items: tv.data?.pages?.[0]?.items?.slice(0, 10) }), _jsx(RecommendationsRail, { title: "Trending Movies", items: movies.data?.pages?.[0]?.items?.slice(0, 12) }), _jsx(RecommendationsRail, { title: "New in Music", items: music.data?.pages?.[0]?.items?.slice(0, 12) })] }));
}
export default HomePage;
