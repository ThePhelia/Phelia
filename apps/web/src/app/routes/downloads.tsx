import { useDownloads } from '@/app/lib/api';
import { useUiState } from '@/app/stores/ui';
import { useEffect } from 'react';
import { Skeleton } from '@/app/components/ui/skeleton';
import type { DownloadItem } from '@/app/lib/types';

function DownloadsPage() {
  const { data, isLoading, isError, refetch } = useDownloads(true);
  const setDownloadsOpen = useUiState((state) => state.setDownloadsOpen);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3 rounded-full" />
        <Skeleton className="h-48 w-full rounded-3xl" />
      </div>
    );
  }

  if (isError) {
    return <p className="text-sm text-muted-foreground">Unable to load downloads.</p>;
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-foreground">Downloads</h1>
        <button
          type="button"
          onClick={() => setDownloadsOpen(true)}
          className="rounded-full border border-border/60 px-3 py-2 text-xs uppercase tracking-widest text-muted-foreground hover:border-[color:var(--accent)] hover:text-foreground"
        >
          Open drawer
        </button>
      </div>
      <div className="overflow-hidden rounded-3xl border border-border/60 bg-background/60">
        <table className="min-w-full divide-y divide-border/60 text-sm">
          <thead className="bg-background/70 text-muted-foreground">
            <tr>
              <th className="px-6 py-3 text-left font-semibold">Title</th>
              <th className="px-6 py-3 text-left font-semibold">Provider</th>
              <th className="px-6 py-3 text-left font-semibold">Progress</th>
              <th className="px-6 py-3 text-left font-semibold">Speed</th>
              <th className="px-6 py-3 text-left font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {data?.map((item) => (
              <DownloadRow key={item.id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DownloadRow({ item }: { item: DownloadItem }) {
  const percent = Math.round((item.progress ?? 0) * 100);
  return (
    <tr className="bg-background/40">
      <td className="px-6 py-3 font-medium text-foreground">{item.name}</td>
      <td className="px-6 py-3 text-muted-foreground">{item.provider ?? '—'}</td>
      <td className="px-6 py-3 text-muted-foreground">{percent}%</td>
      <td className="px-6 py-3 text-muted-foreground">{item.speed ?? '—'}</td>
      <td className="px-6 py-3 text-muted-foreground">{item.status ?? 'queued'}</td>
    </tr>
  );
}

export default DownloadsPage;
