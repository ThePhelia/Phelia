import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';

import CatalogGrid from '@/app/components/CatalogGrid';
import FiltersBar from '@/app/components/FiltersBar';
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import { Badge } from '@/app/components/ui/badge';
import { Skeleton } from '@/app/components/ui/skeleton';
import { useQueryParams } from '@/app/hooks/useQueryParams';
import { useDiscover, useSearch } from '@/app/lib/api';
import { getGenres, getNew, getTop } from '@/app/lib/discovery';
import type { DiscoverParams, DiscoverItem } from '@/app/lib/types';
import type { DiscoveryGenre } from '@/app/lib/discovery';

const DEFAULT_DAYS = 30;
const DEFAULT_LIMIT = 50;

type MusicBrainzRelease = {
  mbid?: string;
  title?: string;
  artist?: string;
  firstReleaseDate?: string;
  primaryType?: string;
  secondaryTypes?: string[];
};

type AppleFeedItem = {
  id?: string;
  title?: string;
  artist?: string;
  url?: string;
  artwork?: string;
  releaseDate?: string;
};

function parseYear(value?: string | null): number | undefined {
  if (!value) return undefined;
  const year = Number.parseInt(value.slice(0, 4), 10);
  return Number.isFinite(year) ? year : undefined;
}

function mapMusicBrainzItem(item: MusicBrainzRelease, genreLabel: string): DiscoverItem {
  const badges: string[] = [];
  if (item.primaryType) {
    badges.push(item.primaryType);
  }
  if (Array.isArray(item.secondaryTypes) && item.secondaryTypes.length) {
    badges.push(...item.secondaryTypes);
  }
  return {
    kind: 'album',
    id: item.mbid || `mb:${item.title ?? 'unknown'}:${item.artist ?? 'various'}`,
    title: item.title ?? 'Untitled Release',
    subtitle: item.artist ?? genreLabel,
    year: parseYear(item.firstReleaseDate),
    badges,
    meta: {
      source: 'musicbrainz',
      mbid: item.mbid,
      firstReleaseDate: item.firstReleaseDate,
      primaryType: item.primaryType,
      secondaryTypes: item.secondaryTypes,
    },
  };
}

function mapAppleItem(item: AppleFeedItem): DiscoverItem {
  return {
    kind: 'album',
    id: item.id ?? `apple:${item.title ?? 'unknown'}:${item.artist ?? 'various'}`,
    title: item.title ?? 'Untitled Album',
    subtitle: item.artist ?? undefined,
    poster: item.artwork ?? undefined,
    year: parseYear(item.releaseDate),
    meta: {
      source: 'apple',
      url: item.url,
      releaseDate: item.releaseDate,
    },
  };
}

function GenreButton({ genre, active, onSelect }: { genre: DiscoveryGenre; active: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={`group flex flex-col justify-between rounded-3xl border p-4 text-left transition hover:border-[color:var(--accent)] hover:shadow-glow ${
        active ? 'border-[color:var(--accent)] bg-[color:var(--accent)]/10 text-foreground' : 'border-border/60 text-muted-foreground'
      }`}
    >
      <span className="text-lg font-semibold text-foreground">{genre.label}</span>
      <span className="mt-2 text-xs uppercase tracking-wide text-muted-foreground">{genre.key.replace(/-/g, ' ')}</span>
    </button>
  );
}

type FilterState = {
  sort: NonNullable<DiscoverParams['sort']>;
  year: string;
  genre: string;
  type: DiscoverParams['type'];
  search: string;
};

const defaults: FilterState = { sort: 'trending', year: '', genre: '', type: undefined, search: '' };

function MusicPage() {
  const [filters, setFilters] = useQueryParams<FilterState>(defaults);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const genresQuery = useQuery({
    queryKey: ['discovery', 'genres'],
    queryFn: getGenres,
    staleTime: 12 * 60 * 60 * 1000,
  });

  const genres = genresQuery.data ?? [];

  useEffect(() => {
    if (!selectedKey && genres.length) {
      setSelectedKey(genres[0]?.key ?? null);
    }
  }, [genres, selectedKey]);

  const selectedGenre = useMemo<DiscoveryGenre | null>(
    () => genres.find((genre) => genre.key === selectedKey) ?? null,
    [genres, selectedKey],
  );

  const newReleasesQuery = useQuery({
    queryKey: ['discovery', 'new', selectedGenre?.key, DEFAULT_DAYS, DEFAULT_LIMIT],
    queryFn: () => getNew(selectedGenre!.key, DEFAULT_DAYS, DEFAULT_LIMIT),
    enabled: Boolean(selectedGenre?.key),
    select: (items: MusicBrainzRelease[]) => items.map((item) => mapMusicBrainzItem(item, selectedGenre?.label ?? '')),
    staleTime: 3 * 60 * 60 * 1000,
  });

  const mostRecentQuery = useQuery({
    queryKey: ['discovery', 'top', selectedGenre?.appleGenreId, DEFAULT_LIMIT],
    queryFn: () => getTop(selectedGenre!.appleGenreId, 'most-recent', 'albums', DEFAULT_LIMIT),
    enabled: Boolean(selectedGenre?.appleGenreId),
    select: (items: AppleFeedItem[]) => items.map((item) => mapAppleItem(item)),
    staleTime: 3 * 60 * 60 * 1000,
  });

  useEffect(() => {
    if (newReleasesQuery.error) {
      toast.error('Unable to load new releases.');
    }
  }, [newReleasesQuery.error]);

  useEffect(() => {
    if (mostRecentQuery.error) {
      toast.error('Unable to load most recent releases.');
    }
  }, [mostRecentQuery.error]);
  const discoverParams = {
    sort: filters.sort,
    year: filters.year || undefined,
    genre: filters.genre || undefined,
    type: filters.type,
  };

  const discoverQuery = useDiscover('album', discoverParams);
  const searchQuery = useSearch({ q: filters.search ?? '', kind: 'music' });

  const activeQuery = filters.search ? searchQuery : discoverQuery;
  const items = activeQuery.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="space-y-12">
      <section className="space-y-6">
        <h1 className="text-2xl font-semibold text-foreground">Music</h1>
        <FiltersBar
          kind="music"
          filters={filters}
          onChange={(next) => setFilters({ ...filters, ...next })}
        />
        <CatalogGrid
          items={items}
          loading={activeQuery.isLoading || activeQuery.isFetching}
          hasNextPage={Boolean(activeQuery.hasNextPage)}
          fetchNextPage={activeQuery.fetchNextPage}
        />
      </section>

      <section className="space-y-6">
        <header className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">Browse by Genre</h2>
          <p className="text-sm text-muted-foreground">Discover new releases and trending albums curated by genre.</p>
        </header>

        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Genres</h3>
          {selectedGenre ? (
            <Badge variant="outline" className="bg-background/60 text-xs uppercase tracking-wide">
              {selectedGenre.label}
            </Badge>
          ) : null}
        </div>

        {genresQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-24 rounded-3xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {genres.map((genre) => (
              <GenreButton
                key={genre.key}
                genre={genre}
                active={genre.key === selectedKey}
                onSelect={() => setSelectedKey(genre.key)}
              />
            ))}
          </div>
        )}
      </section>

      {selectedGenre ? (
        <div className="space-y-10">
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">New Releases</h3>
              <span className="text-xs text-muted-foreground">MusicBrainz • Last {DEFAULT_DAYS} days</span>
            </div>
            {newReleasesQuery.isLoading ? (
              <Skeleton className="h-52 w-full rounded-3xl" />
            ) : (
              <>
                <RecommendationsRail title="New Releases" items={newReleasesQuery.data ?? []} />
                {!newReleasesQuery.isLoading && !(newReleasesQuery.data?.length ?? 0) ? (
                  <p className="text-sm text-muted-foreground">No recent releases found for this genre.</p>
                ) : null}
              </>
            )}
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">Most Recent</h3>
              <span className="text-xs text-muted-foreground">Apple Music RSS</span>
            </div>
            {mostRecentQuery.isLoading ? (
              <Skeleton className="h-52 w-full rounded-3xl" />
            ) : (
              <>
                <RecommendationsRail title="Most Recent" items={mostRecentQuery.data ?? []} />
                {!mostRecentQuery.isLoading && !(mostRecentQuery.data?.length ?? 0) ? (
                  <p className="text-sm text-muted-foreground">No trending releases available.</p>
                ) : null}
              </>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

export default MusicPage;
