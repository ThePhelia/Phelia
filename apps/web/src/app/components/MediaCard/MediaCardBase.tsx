import { forwardRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Info, PlusCircle, Download } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import type { DiscoverItem } from '@/app/lib/types';
import { useMutateList } from '@/app/lib/api';
import { toast } from 'sonner';
import { Badge } from '@/app/components/ui/badge';
import { cn } from '@/app/utils/cn';
import { useTorrentSearch } from '@/app/stores/torrent-search';

interface MediaCardBaseProps {
  item: DiscoverItem;
  tabIndex?: number;
  onFocus?: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

const MediaCardBase = forwardRef<HTMLDivElement, MediaCardBaseProps>(({ item, tabIndex = -1, onFocus, onKeyDown }, ref) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [hovered, setHovered] = useState(false);
  const mutation = useMutateList();
  const fetchTorrentSearch = useTorrentSearch((state) => state.fetchForItem);

  const openTorrentSearch = () => {
    void fetchTorrentSearch({
      id: item.id,
      title: item.title,
      kind: item.kind,
      year: item.year,
    });
  };

  const openDetails = () => {
    navigate(`/details/${item.kind === 'album' ? 'music' : item.kind}/${item.id}`, {
      state: { backgroundLocation: location },
    });
  };

  const addToWatchlist = async () => {
    try {
      await mutation.mutateAsync({
        action: 'add',
        list: 'watchlist',
        item: { kind: item.kind, id: item.id },
      });
      toast.success(`Added ${item.title} to your watchlist.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update list');
    }
  };

  const poster = item.poster ?? item.backdrop;

  return (
    <div
      ref={ref}
      tabIndex={tabIndex}
      onFocus={onFocus}
      onKeyDown={onKeyDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="group relative flex h-full flex-col overflow-hidden rounded-3xl border border-border/60 bg-card/60 shadow-lg outline-none transition-transform duration-200 focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-background hover:-translate-y-1 hover:shadow-glow"
      role="button"
      onClick={openDetails}
    >
      <div className="relative aspect-[2/3] w-full overflow-hidden">
        {poster ? (
          <img
            src={poster}
            alt={item.title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-foreground/10 to-foreground/5">
            <span className="text-sm text-muted-foreground">No artwork</span>
          </div>
        )}
        {item.badges?.length ? (
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            {item.badges.slice(0, 3).map((badge) => (
              <Badge key={badge} variant="outline" className="bg-black/40 text-xs text-white">
                {badge}
              </Badge>
            ))}
          </div>
        ) : null}
        {typeof item.progress === 'number' && item.progress > 0 ? (
          <div className="absolute bottom-3 right-3 rounded-full bg-black/70 px-2 py-1 text-xs text-white">
            {Math.round(item.progress * 100)}%
          </div>
        ) : null}
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center gap-2 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 transition-opacity',
            hovered ? 'opacity-100' : 'opacity-0',
          )}
        >
          <Button
            variant="accent"
            size="icon"
            className="h-12 w-12 rounded-full"
            aria-label="Open torrent search"
            onClick={(event) => {
              event.stopPropagation();
              openTorrentSearch();
            }}
          >
            <Download className="h-5 w-5" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            className="h-12 w-12 rounded-full" aria-label="Add to watchlist"
            onClick={(event) => {
              event.stopPropagation();
              addToWatchlist();
            }}
          >
            <PlusCircle className="h-5 w-5" />
          </Button>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 px-4 py-4">
        <div className="space-y-1">
          <h3 className="line-clamp-2 text-sm font-semibold text-foreground">{item.title}</h3>
          {item.subtitle ? (
            <p className="text-xs text-muted-foreground">{item.subtitle}</p>
          ) : null}
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {[item.year, item.genres?.slice(0, 2).join(', ')].filter(Boolean).join(' • ')}
          </p>
        </div>
        <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
          <span className="rounded-full bg-foreground/10 px-2 py-1">
            {item.meta?.source ? String(item.meta.source).toUpperCase() : 'Phelia'}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 rounded-full px-3"
              onClick={(event) => {
                event.stopPropagation();
                openDetails();
              }}
            >
              <Info className="mr-2 h-4 w-4" /> Details
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 rounded-full px-3"
              aria-label="Open torrent search"
              onClick={(event) => {
                event.stopPropagation();
                openTorrentSearch();
              }}
            >
              <Download className="mr-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
});

MediaCardBase.displayName = 'MediaCardBase';

export default MediaCardBase;
