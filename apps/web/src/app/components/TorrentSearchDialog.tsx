import { AlertTriangle, DownloadCloud, ExternalLink, Info, Loader2, Magnet, X } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/app/components/ui/dialog';
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { useTorrentSearch } from '@/app/stores/torrent-search';
import type { SearchResultItem } from '@/app/lib/types';
import { useCreateDownload } from '@/app/lib/api';

function TorrentSearchDialog() {
  const {
    open,
    setOpen,
    isLoading,
    results,
    message,
    error,
    metaError,
    activeItem,
    query,
  } = useTorrentSearch();

  const description = activeItem?.title
    ? `Aggregated torrent results for "${activeItem.title}"`
    : 'Aggregated torrent results from configured providers.';

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-5xl">
        <DialogHeader className="relative">
          <DialogTitle className="flex items-center gap-2 text-2xl font-semibold">
            <DownloadCloud className="h-6 w-6 text-[color:var(--accent)]" /> Torrent results
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">{description}</DialogDescription>
          <DialogClose className="absolute right-6 top-6 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-background/80 text-muted-foreground transition hover:text-foreground">
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </DialogClose>
        </DialogHeader>
        <div className="space-y-4 px-8 pb-8">
          {query ? (
            <p className="text-xs text-muted-foreground">Search query: <span className="font-mono text-foreground/80">{query}</span></p>
          ) : null}
          {message ? <MessageBanner message={message} /> : null}
          {metaError ? <WarningBanner message={metaError} /> : null}
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} />
          ) : results.length ? (
            <ResultsList items={results} />
          ) : (
            <EmptyState />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-sm text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin text-[color:var(--accent)]" />
        <p>Fetching torrents…</p>
      </div>
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="animate-pulse space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm"
        >
          <div className="h-5 w-2/3 rounded bg-foreground/10" />
          <div className="h-3 w-full rounded bg-foreground/5" />
          <div className="h-3 w-3/4 rounded bg-foreground/5" />
        </div>
      ))}
    </div>
  );
}

function MessageBanner({ message }: { message: string }) {
  return (
    <div className="flex flex-wrap items-start gap-3 rounded-2xl border border-border/60 bg-muted/10 p-4 text-sm text-muted-foreground">
      <Info className="mt-0.5 h-5 w-5 text-[color:var(--accent)]" />
      <div className="space-y-2">
        <p>{message}</p>
      </div>
    </div>
  );
}

function WarningBanner({ message }: { message: string }) {
  return (
    <div className="flex flex-wrap items-start gap-3 rounded-2xl border border-orange-300/40 bg-orange-400/10 p-4 text-sm text-orange-200">
      <AlertTriangle className="mt-0.5 h-5 w-5" />
      <div className="space-y-2">
        <p>{message}</p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-destructive/40 bg-destructive/10 p-8 text-center text-sm text-destructive">
      <AlertTriangle className="h-8 w-8" />
      <p>{message}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground">
      <DownloadCloud className="h-8 w-8 text-muted-foreground" />
      <p>No torrents were returned for this query.</p>
    </div>
  );
}

function ResultsList({ items }: { items: SearchResultItem[] }) {
  return (
    <ScrollArea className="max-h-[60vh] pr-2">
      <div className="space-y-4">
        {items.map((item, index) => (
          <TorrentResultCard key={`${item.id}-${index}`} item={item} />
        ))}
      </div>
    </ScrollArea>
  );
}

function TorrentResultCard({ item }: { item: SearchResultItem }) {
  const meta = item.meta ?? {};
  const providers = Array.isArray(meta.providers) ? meta.providers.filter((provider) => provider.used) : [];
  const sourceExtras = providers
    .map((provider) => provider.extra)
    .filter((extra): extra is Record<string, unknown> => extra != null && typeof extra === 'object');
  const sources = Array.isArray(meta.sources)
    ? meta.sources.filter((entry): entry is Record<string, unknown> => entry != null && typeof entry === 'object')
    : [];
  const mergedSources = [...sourceExtras, ...sources];
  const magnetLink = findFirstString(mergedSources, 'magnet');
  const downloadUrl = findFirstString(mergedSources, 'url');
  const tracker =
    findFirstString(mergedSources, 'tracker') ??
    findFirstString(mergedSources, 'provider') ??
    findFirstString(mergedSources, 'indexer');
  const category = findFirstString(mergedSources, 'category');
  const sizeLabel = formatSizeLabel(findFirstValue(mergedSources, 'size'));
  const seeders = findFirstNumber(mergedSources, 'seeders');
  const leechers = findFirstNumber(mergedSources, 'leechers');
  const confidence =
    typeof meta.confidence === 'number' ? Math.round(Math.max(0, Math.min(meta.confidence, 1)) * 100) : undefined;
  const reasons = Array.isArray(meta.reasons) ? meta.reasons : [];
  const needsConfirmation = meta.needs_confirmation === true;
  const sourceKind = typeof meta.source_kind === 'string' ? meta.source_kind : item.kind;

  const { mutateAsync, isPending, error, reset } = useCreateDownload();
  const hasDownloadSource = Boolean(magnetLink || downloadUrl);
  const errorMessage = error instanceof Error ? error.message : undefined;

  const handleAddDownload = async () => {
    if (!hasDownloadSource || isPending) return;
    const payload = magnetLink ? { magnet: magnetLink } : downloadUrl ? { url: downloadUrl } : undefined;
    if (!payload) return;

    reset();
    try {
      await mutateAsync(payload);
      toast.success(`Added "${item.title}" to the download queue.`);
    } catch {
      // Error is surfaced via mutation state for the user.
    }
  };

  return (
    <div className="space-y-4 rounded-2xl border border-border/60 bg-background/60 p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="uppercase tracking-wide text-foreground/80">
              {sourceKind}
            </Badge>
            {typeof confidence === 'number' ? <Badge variant="accent">{confidence}% match</Badge> : null}
            {needsConfirmation ? (
              <Badge variant="outline" className="border-orange-400 text-orange-300">
                Needs confirmation
              </Badge>
            ) : null}
            {tracker ? (
              <Badge variant="outline" className="text-foreground/70">
                {tracker}
              </Badge>
            ) : null}
          </div>
          {sizeLabel ? <p className="text-sm text-muted-foreground">{sizeLabel}</p> : null}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        {seeders !== undefined ? <span>Seeders: {seeders}</span> : null}
        {leechers !== undefined ? <span>Leechers: {leechers}</span> : null}
        {category ? <span>Category: {category}</span> : null}
      </div>
      {providers.length ? (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground/80">Providers:</span>
          {providers.map((provider) => (
            <Badge key={provider.name} variant="default" className="bg-foreground/10 text-foreground/80">
              {provider.name}
            </Badge>
          ))}
        </div>
      ) : null}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={handleAddDownload} disabled={!hasDownloadSource || isPending} variant="default">
            {isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <DownloadCloud className="mr-2 h-4 w-4" />
            )}
            {isPending ? 'Adding…' : 'Download'}
          </Button>
          {magnetLink ? (
            <Button size="sm" variant="secondary" onClick={() => void copyToClipboard(magnetLink)}>
              <Magnet className="mr-2 h-4 w-4" /> Copy magnet
            </Button>
          ) : null}
          {downloadUrl ? (
            <Button asChild size="sm" variant="outline">
              <a href={downloadUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" /> Open source
              </a>
            </Button>
          ) : null}
        </div>
        {errorMessage ? (
          <p className="text-xs text-destructive">Failed to add download: {errorMessage}</p>
        ) : null}
        {!hasDownloadSource ? (
          <p className="text-xs text-muted-foreground">No download sources are available for this torrent.</p>
        ) : null}
      </div>
      {reasons.length ? (
        <div className="text-xs text-muted-foreground">
          <span className="font-semibold text-foreground/80">Notes:</span> {reasons.join(', ')}
        </div>
      ) : null}
    </div>
  );
}

function findFirstString(objects: Record<string, unknown>[], key: string): string | undefined {
  for (const obj of objects) {
    const value = obj[key];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }
  return undefined;
}

function findFirstNumber(objects: Record<string, unknown>[], key: string): number | undefined {
  for (const obj of objects) {
    const value = obj[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }
  }
  return undefined;
}

function findFirstValue(objects: Record<string, unknown>[], key: string): unknown {
  for (const obj of objects) {
    if (key in obj) {
      return obj[key];
    }
  }
  return undefined;
}

function formatSizeLabel(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let num = value;
    let unitIndex = 0;
    while (num >= 1024 && unitIndex < units.length - 1) {
      num /= 1024;
      unitIndex += 1;
    }
    const precision = num >= 10 || Number.isInteger(num) ? 0 : 1;
    return `${num.toFixed(precision)} ${units[unitIndex]}`;
  }
  return undefined;
}

async function copyToClipboard(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    toast.success('Magnet link copied to clipboard.');
  } catch (error) {
    toast.error('Unable to copy magnet link.');
  }
}

export default TorrentSearchDialog;
