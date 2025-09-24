import { useCallback } from 'react';
import { ExternalLink, Copy } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import type { JackettSearchItem } from '@/app/types/meta';

interface TorrentResultsProps {
  results: JackettSearchItem[];
}

function TorrentResults({ results }: TorrentResultsProps) {
  const copyToClipboard = useCallback(async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
    } catch (error) {
      console.error('Failed to copy magnet link', error);
    }
  }, []);

  if (!results.length) return null;

  return (
    <ScrollArea className="max-h-72 pr-2">
      <div className="space-y-3">
        {results.map((item, index) => (
          <div
            key={`${item.title}-${index}`}
            className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-background/60 p-4 text-sm text-muted-foreground"
          >
            <div>
              <h4 className="text-base font-semibold text-foreground">{item.title}</h4>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                {item.size ? <span className="rounded-full bg-foreground/10 px-2 py-1">{item.size}</span> : null}
                {typeof item.seeders === 'number' ? (
                  <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-400">
                    {item.seeders} seeders
                  </span>
                ) : null}
                {typeof item.leechers === 'number' ? (
                  <span className="rounded-full bg-orange-500/10 px-2 py-1 text-orange-300">
                    {item.leechers} leechers
                  </span>
                ) : null}
                {item.tracker ? (
                  <span className="rounded-full bg-foreground/10 px-2 py-1">{item.tracker}</span>
                ) : null}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {item.magnet ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => copyToClipboard(item.magnet as string)}
                  className="flex items-center gap-2"
                >
                  <Copy className="h-4 w-4" /> Copy magnet
                </Button>
              ) : null}
              {item.link ? (
                <Button asChild size="sm" variant="outline" className="flex items-center gap-2">
                  <a href={item.link} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-4 w-4" /> Open link
                  </a>
                </Button>
              ) : null}
              {!item.magnet && !item.link ? (
                <span className="text-xs text-muted-foreground">No download sources provided.</span>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}

export default TorrentResults;
