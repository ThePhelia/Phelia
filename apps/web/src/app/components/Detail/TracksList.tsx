import type { TrackInfo } from '@/app/lib/types';

interface TracksListProps {
  tracks?: TrackInfo[];
}

function formatDuration(seconds?: number) {
  if (!seconds) return '';
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, '0')}`;
}

function TracksList({ tracks = [] }: TracksListProps) {
  if (!tracks.length) {
    return <p className="text-sm text-muted-foreground">Tracklist unavailable.</p>;
  }

  return (
    <ol className="space-y-2">
      {tracks.map((track) => (
        <li key={track.index} className="flex items-center justify-between rounded-2xl border border-border/40 bg-background/50 px-4 py-3 text-sm">
          <span className="flex items-center gap-3 text-foreground">
            <span className="text-xs text-muted-foreground">{track.index}</span>
            {track.title}
          </span>
          <span className="text-xs text-muted-foreground">{formatDuration(track.length)}</span>
        </li>
      ))}
    </ol>
  );
}

export default TracksList;
