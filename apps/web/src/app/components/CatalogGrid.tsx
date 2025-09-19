import { useEffect, useMemo, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import MovieCard from '@/app/components/MediaCard/MovieCard';
import TvCard from '@/app/components/MediaCard/TvCard';
import AlbumCard from '@/app/components/MediaCard/AlbumCard';
import { useKeyboardGridNav } from '@/app/hooks/useKeyboardGridNav';
import type { DiscoverItem } from '@/app/lib/types';
import { Skeleton } from '@/app/components/ui/skeleton';

interface CatalogGridProps {
  items: DiscoverItem[];
  loading?: boolean;
  hasNextPage?: boolean;
  fetchNextPage?: () => void;
}

function CatalogGrid({ items, loading, hasNextPage, fetchNextPage }: CatalogGridProps) {
  const { getItemProps } = useKeyboardGridNav(items.length, { columns: 6 });
  const loaderRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!fetchNextPage || !hasNextPage) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          void fetchNextPage();
        }
      });
    }, { rootMargin: '400px' });
    const node = loaderRef.current;
    if (node) observer.observe(node);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage]);

  const cards = useMemo(() => {
    return items.map((item, index) => {
      const { ref, ...keyboardProps } = getItemProps(index);
      const card = (() => {
        if (item.kind === 'movie') return <MovieCard item={item} />;
        if (item.kind === 'tv') return <TvCard item={item} />;
        return <AlbumCard item={item} />;
      })();
      return (
        <div
          key={`${item.kind}-${item.id}`}
          ref={ref}
          {...keyboardProps}
          className="focus-visible:outline-none"
        >
          {card}
        </div>
      );
    });
  }, [getItemProps, items]);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
        {cards}
        {loading && items.length === 0
          ? Array.from({ length: 12 }).map((_, index) => (
              <div key={`skeleton-${index}`} className="flex flex-col gap-3">
                <Skeleton className="aspect-[2/3] w-full rounded-3xl" />
                <Skeleton className="h-4 w-3/4 rounded-full" />
                <Skeleton className="h-3 w-1/2 rounded-full" />
              </div>
            ))
          : null}
      </div>
      {hasNextPage ? (
        <div ref={loaderRef} className="flex items-center justify-center py-6 text-sm text-muted-foreground">
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading more
            </>
          ) : (
            'Scroll to load more'
          )}
        </div>
      ) : null}
    </div>
  );
}

export default CatalogGrid;
