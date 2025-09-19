import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { useLibrary } from '@/app/lib/api';
import { Skeleton } from '@/app/components/ui/skeleton';

function LibraryPage() {
  const { data, isLoading, isError } = useLibrary();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3 rounded-full" />
        <Skeleton className="h-48 w-full rounded-3xl" />
      </div>
    );
  }

  if (isError || !data) {
    return <p className="text-sm text-muted-foreground">Unable to load your library.</p>;
  }

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold text-foreground">My Library</h1>
      <RecommendationsRail title="Watchlist" items={data.watchlist} />
      <RecommendationsRail title="Favorites" items={data.favorites} />
      {data.playlists?.map((playlist) => (
        <RecommendationsRail key={playlist.id} title={playlist.title} items={playlist.items} />
      ))}
    </div>
  );
}

export default LibraryPage;
