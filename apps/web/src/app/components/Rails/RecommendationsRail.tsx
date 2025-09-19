import type React from 'react';
import { useRef } from 'react';
import MovieCard from '@/app/components/MediaCard/MovieCard';
import TvCard from '@/app/components/MediaCard/TvCard';
import AlbumCard from '@/app/components/MediaCard/AlbumCard';
import type { DiscoverItem } from '@/app/lib/types';

interface RecommendationsRailProps {
  title: string;
  items?: DiscoverItem[];
}

function RecommendationsRail({ title, items = [] }: RecommendationsRailProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
    containerRef.current.scrollBy({ left: event.deltaY, behavior: 'smooth' });
  };

  if (!items.length) return null;

  return (
    <section className="space-y-3">
      <header className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      </header>
      <div
        ref={containerRef}
        onWheel={handleWheel}
        className="scrollbar-thin flex gap-4 overflow-x-auto pb-4"
      >
        {items.map((item) => {
          if (item.kind === 'movie') {
            return (
              <div key={`${item.kind}-${item.id}`} className='w-[200px] flex-shrink-0'>
                <MovieCard item={item} />
              </div>
            );
          }
          if (item.kind === 'tv') {
            return (
              <div key={`${item.kind}-${item.id}`} className='w-[200px] flex-shrink-0'>
                <TvCard item={item} />
              </div>
            );
          }
          return (
            <div key={`${item.kind}-${item.id}`} className='w-[200px] flex-shrink-0'>
              <AlbumCard item={item} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default RecommendationsRail;
