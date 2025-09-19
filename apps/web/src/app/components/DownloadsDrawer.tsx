import { AlertTriangle, DownloadCloud, Pause } from 'lucide-react';
import { useEffect } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/app/components/ui/sheet';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { Progress } from '@/app/components/ui/progress';
import { Badge } from '@/app/components/ui/badge';
import { useDownloads } from '@/app/lib/api';
import type { DownloadItem } from '@/app/lib/types';
import { useUiState } from '@/app/stores/ui';

function formatProgress(item: DownloadItem) {
  const percent = Math.round((item.progress ?? 0) * 100);
  return `${percent}%`;
}

function DownloadsDrawer() {
  const { downloadsOpen, setDownloadsOpen } = useUiState();
  const { data, isLoading, isError, refetch } = useDownloads(downloadsOpen);

  useEffect(() => {
    if (downloadsOpen) {
      void refetch();
    }
  }, [downloadsOpen, refetch]);

  return (
    <Sheet open={downloadsOpen} onOpenChange={setDownloadsOpen}>
      <SheetContent side="right" className="w-full max-w-xl border-l border-border/60">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-lg font-semibold">
            <DownloadCloud className="h-5 w-5 text-[color:var(--accent)]" /> Downloads
          </SheetTitle>
          <SheetDescription className="text-sm text-muted-foreground">
            Monitor current and recent downloads. This view is read-only.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 flex-1">
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm">
                  <div className="h-4 w-3/4 rounded bg-foreground/10" />
                  <div className="mt-3 h-2 w-full rounded-full bg-foreground/5" />
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground">
              <AlertTriangle className="h-6 w-6 text-orange-400" />
              Failed to fetch downloads. The API may be offline.
            </div>
          ) : (data?.length ? <DownloadsList items={data} /> : <EmptyDownloads />)}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function EmptyDownloads() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground">
      <Pause className="h-8 w-8 text-muted-foreground" />
      <p>No active downloads right now.</p>
    </div>
  );
}

function DownloadsList({ items }: { items: DownloadItem[] }) {
  return (
    <ScrollArea className="h-full rounded-3xl border border-border/40 bg-background/40">
      <div className="space-y-4 p-6">
        {items.map((item) => {
          const percent = Math.round((item.progress ?? 0) * 100);
          return (
            <div key={item.id} className="space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
                  <p className="text-xs text-muted-foreground">
                    {item.provider ? `${item.provider} • ` : ''}
                    {item.size ?? ''}
                  </p>
                </div>
                <Badge variant="outline">{item.status ?? 'queued'}</Badge>
              </div>
              <Progress value={percent} />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{formatProgress(item)}</span>
                <span>{item.speed ? `${item.speed}/s` : null}</span>
                <span>{item.eta ? `ETA ${item.eta}` : null}</span>
              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}

export default DownloadsDrawer;
