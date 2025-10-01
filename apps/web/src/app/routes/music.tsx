import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/app/components/ui/button';
import { Skeleton } from '@/app/components/ui/skeleton';
import type { AlbumItem, DiscoveryGenre, DiscoveryProvidersStatus } from '@/app/lib/discovery';
import {
  fetchDiscoveryCharts,
  fetchDiscoveryGenres,
  fetchDiscoveryNew,
  fetchDiscoveryProviders,
} from '@/app/lib/discovery';

const STATIC_TAGS = ['techno', 'shoegaze', 'hip-hop'];
const FALLBACK_GENRES: DiscoveryGenre[] = STATIC_TAGS.map((tag) => ({
  key: tag,
  label: tag.replace(/\b\w/g, (char) => char.toUpperCase()).replace(/-(\w)/g, (_, letter) => ` ${letter.toUpperCase()}`),
}));

function MusicPage() {
  const [newReleases, setNewReleases] = useState<AlbumItem[] | null>(null);
  const [charts, setCharts] = useState<AlbumItem[] | null>(null);
  const [providers, setProviders] = useState<DiscoveryProvidersStatus | null>(null);
  const [genres, setGenres] = useState<DiscoveryGenre[]>([]);
  const [genresLoading, setGenresLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const requestRef = useRef(0);

  const selectedGenre = useMemo(
    () => (selectedKey ? genres.find((genre) => genre.key === selectedKey) ?? null : null),
    [genres, selectedKey],
  );

  const loadGenre = useCallback((genre: Pick<DiscoveryGenre, 'key' | 'appleGenreId'> | null) => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;

    if (!genre) {
      setSelectedKey(null);
      setNewReleases([]);
      setCharts([]);
      return;
    }

    setSelectedKey(genre.key);
    setNewReleases(null);
    setCharts(null);

    fetchDiscoveryNew(genre.key, 30)
      .then((items) => {
        if (requestRef.current === requestId) {
          setNewReleases(items);
        }
      })
      .catch(() => {
        if (requestRef.current === requestId) {
          setNewReleases([]);
        }
      });

    fetchDiscoveryCharts(genre.appleGenreId, genre.key, 30)
      .then((items) => {
        if (requestRef.current === requestId) {
          setCharts(items);
        }
      })
      .catch(() => {
        if (requestRef.current === requestId) {
          setCharts([]);
        }
      });
  }, []);

  useEffect(() => {
    fetchDiscoveryProviders()
      .then(setProviders)
      .catch(() => setProviders({
        lastfm: false,
        deezer: false,
        itunes: false,
        musicbrainz: false,
        listenbrainz: false,
        spotify: false,
      }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setGenresLoading(true);
    fetchDiscoveryGenres()
      .then((list) => {
        if (cancelled) {
          return;
        }
        const normalised = list.length ? list : FALLBACK_GENRES;
        setGenres(normalised);
        loadGenre(normalised[0] ?? null);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setGenres(FALLBACK_GENRES);
        loadGenre(FALLBACK_GENRES[0] ?? null);
      })
      .finally(() => {
        if (!cancelled) {
          setGenresLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [loadGenre]);

  return (
    <div className="space-y-12">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Music Discovery</h1>
        <p className="text-sm text-muted-foreground">
          Fresh releases and genre shelves aggregated from Last.fm, Deezer, Spotify, iTunes, and MusicBrainz.
        </p>
        {providers ? (
          <p className="text-xs text-muted-foreground">
            Providers active:{' '}
            {Object.entries(providers)
              .filter(([, enabled]) => enabled)
              .map(([name]) => name)
              .join(', ') || 'none'}
          </p>
        ) : (
          <Skeleton className="h-4 w-40" />
        )}
      </header>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Curated Genres</h2>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Select a genre to load rails</p>
          </div>
        </div>
        {genresLoading ? (
          <Skeleton className="h-10 w-full max-w-md" />
        ) : genres.length ? (
          <div className="flex flex-wrap gap-2">
            {genres.map((genre) => {
              const isSelected = genre.key === selectedGenre?.key;
              return (
                <Button
                  key={genre.key}
                  type="button"
                  variant={isSelected ? 'default' : 'outline'}
                  onClick={() => loadGenre(genre)}
                  aria-pressed={isSelected}
                >
                  {genre.label}
                </Button>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No genres available right now.</p>
        )}
      </section>

      <DiscoverySection
        title="New Releases"
        subtitle={selectedGenre ? selectedGenre.label : 'Select a genre'}
        items={selectedGenre ? newReleases : []}
      />
      <DiscoverySection
        title="Top Albums"
        subtitle={selectedGenre ? `${selectedGenre.label} charts` : 'Select a genre'}
        items={selectedGenre ? charts : []}
      />

    </div>
  );
}

function DiscoverySection({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: AlbumItem[] | null | undefined;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <div>
          <h2 className="text-xl font-semibold text-foreground">{title}</h2>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {items === null ? (
        <Skeleton className="h-48 w-full rounded-3xl" />
      ) : items && items.length ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {items.map((item) => (
            <AlbumCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No results available right now.</p>
      )}
    </section>
  );
}

function AlbumCard({ item }: { item: AlbumItem }) {
  const release = item.release_date;
  return (
    <div className="w-40 flex-shrink-0 space-y-2">
      <div className="h-40 w-40 overflow-hidden rounded-xl bg-muted">
        {item.cover_url ? (
          <img src={item.cover_url} alt={item.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">No artwork</div>
        )}
      </div>
      <div className="space-y-1">
        <p className="truncate text-sm font-semibold text-foreground">{item.title}</p>
        <p className="truncate text-xs text-muted-foreground">{item.artist}</p>
        {release ? (
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{release}</p>
        ) : null}
        {item.source ? (
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.source}</p>
        ) : null}
      </div>
    </div>
  );
}

export default MusicPage;
