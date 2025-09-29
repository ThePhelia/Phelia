import { useEffect, useState } from 'react';

import { Skeleton } from '@/app/components/ui/skeleton';
import type { AlbumItem, DiscoveryProvidersStatus } from '@/app/lib/discovery';
import {
  fetchDiscoveryCharts,
  fetchDiscoveryNew,
  fetchDiscoveryProviders,
  fetchDiscoveryTag,
} from '@/app/lib/discovery';

const TAGS = ['techno', 'ambient', 'shoegaze', 'hip-hop'];

function MusicPage() {
  const [newReleases, setNewReleases] = useState<AlbumItem[] | null>(null);
  const [charts, setCharts] = useState<AlbumItem[] | null>(null);
  const [tagShelves, setTagShelves] = useState<Record<string, AlbumItem[]>>({});
  const [providers, setProviders] = useState<DiscoveryProvidersStatus | null>(null);

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
    fetchDiscoveryNew(undefined, 30)
      .then(setNewReleases)
      .catch(() => setNewReleases([]));
    fetchDiscoveryCharts(undefined, 30)
      .then(setCharts)
      .catch(() => setCharts([]));
    Promise.all(TAGS.map((tag) => fetchDiscoveryTag(tag, 24).then((items) => [tag, items] as const)))
      .then((entries) => setTagShelves(Object.fromEntries(entries)))
      .catch(() => setTagShelves({}));
  }, []);

  return (
    <div className="space-y-12">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Music Discovery</h1>
        <p className="text-sm text-muted-foreground">
          Fresh releases and genre shelves aggregated from Last.fm, Deezer, Spotify, iTunes, and MusicBrainz.
        </p>
        {providers ? (
          <p className="text-xs text-muted-foreground">
            Providers active: {Object.entries(providers).filter(([, enabled]) => enabled).map(([name]) => name).join(', ') || 'none'}
          </p>
        ) : (
          <Skeleton className="h-4 w-40" />
        )}
      </header>

      <DiscoverySection title="New Releases" subtitle="Cross-provider" items={newReleases} />
      <DiscoverySection title="Top Albums" subtitle="Charts" items={charts} />

      {TAGS.map((tag) => (
        <DiscoverySection
          key={tag}
          title={tag.toUpperCase()}
          subtitle="Tag shelf"
          items={tagShelves[tag]}
        />
      ))}
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
            <AlbumCard key={item.canonical_key} item={item} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No results available right now.</p>
      )}
    </section>
  );
}

function AlbumCard({ item }: { item: AlbumItem }) {
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
        {item.release_date ? (
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.release_date}</p>
        ) : null}
        <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.source}</p>
      </div>
    </div>
  );
}

export default MusicPage;
