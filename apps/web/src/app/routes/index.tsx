import HeroCarousel from '@/app/components/HeroCarousel';
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { useDiscover } from '@/app/lib/api';

function HomePage() {
  const movies = useDiscover('movie', { sort: 'trending' });
  const tv = useDiscover('tv', { sort: 'popular' });
  const music = useDiscover('album', { sort: 'new' });

  const heroItems = movies.data?.pages?.[0]?.items ?? [];

  return (
    <div className="space-y-12">
      <section>{heroItems.length ? <HeroCarousel items={heroItems.slice(0, 6)} /> : null}</section>
      <RecommendationsRail title="Continue Watching" items={tv.data?.pages?.[0]?.items?.slice(0, 10)} />
      <RecommendationsRail title="Trending Movies" items={movies.data?.pages?.[0]?.items?.slice(0, 12)} />
      <RecommendationsRail title="New in Music" items={music.data?.pages?.[0]?.items?.slice(0, 12)} />
    </div>
  );
}

export default HomePage;
