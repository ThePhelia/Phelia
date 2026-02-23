import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { useLibrary } from '@/app/lib/api';
import { Skeleton } from '@/app/components/ui/skeleton';
import type { DiscoverItem, LibraryItemSummary } from '@/app/lib/types';
import { safeList } from '@/app/utils/safe';

const isDiscoverItem = (item: unknown): item is DiscoverItem => {
  return Boolean(item) && typeof item === 'object' && typeof (item as DiscoverItem).id === 'string';
};

const isPlaylist = (item: unknown): item is LibraryItemSummary['playlists'][number] => {
  return (
    Boolean(item) &&
    typeof item === 'object' &&
    typeof (item as LibraryItemSummary['playlists'][number]).id === 'string' &&
    typeof (item as LibraryItemSummary['playlists'][number]).title === 'string' &&
    Array.isArray((item as LibraryItemSummary['playlists'][number]).items)
  );
};

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

  const watchlist = safeList(data.watchlist, isDiscoverItem);
  const favorites = safeList(data.favorites, isDiscoverItem);
  const playlists = safeList(data.playlists, isPlaylist);

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold text-foreground">My Library</h1>
      <RecommendationsRail title="Watchlist" items={watchlist} />
      <RecommendationsRail title="Favorites" items={favorites} />
      {playlists.map((playlist) => (
        <RecommendationsRail key={playlist.id} title={playlist.title} items={safeList(playlist.items, isDiscoverItem)} />
      ))}
    </div>
  );
}

export default LibraryPage;
