import { useEffect, useMemo, useState } from 'react';
import { Loader2, Clock3, Star, Search } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogFooter } from '@/app/components/ui/dialog';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Skeleton } from '@/app/components/ui/skeleton';
import DetailContent from '@/app/components/Detail/DetailContent';
import TorrentResults from '@/app/components/Detail/TorrentResults';
import { useDetails, useMetaDetail, startIndexing } from '@/app/lib/api';
import type { MediaKind } from '@/app/lib/types';
import type { JackettSearchItem, MetaDetail as MetaDetailType } from '@/app/types/meta';


interface DetailDialogProps {
  kind: MediaKind;
  id: string;
  provider?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-7 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="grid gap-4 md:grid-cols-[2fr_3fr]">
        <Skeleton className="aspect-[2/3] w-full rounded-3xl" />
        <div className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    </div>
  );
}

function ErrorState({ message = 'Failed to load details.' }: { message?: string }) {
  return (
    <div className="space-y-2 text-center">
      <p className="text-lg font-semibold text-foreground">{message}</p>
      <p className="text-sm text-muted-foreground">Please try again later.</p>
    </div>
  );
}

function DetailDialog({ kind, id, provider, open, onOpenChange }: DetailDialogProps) {
  const isMetaFlow = Boolean(provider);
  const {
    data: metaDetail,
    isLoading: isMetaLoading,
    isError: isMetaError,
  } = useMetaDetail(
    isMetaFlow ? { type: kind, id, provider: provider as string } : { type: 'movie', id: '', provider: '' }
  );
  const { data, isLoading, isError } = useDetails(kind, id);

  const [season, setSeason] = useState<number | ''>('');
  const [episode, setEpisode] = useState<number | ''>('');
  const [torrentResults, setTorrentResults] = useState<JackettSearchItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [lastQuery, setLastQuery] = useState('');

  useEffect(() => {
    if (!metaDetail) return;
    const canonicalTv = metaDetail.canonical.tv;
    setSeason(
      canonicalTv && typeof canonicalTv.season === 'number' && canonicalTv.season > 0 ? canonicalTv.season : ''
    );
    setEpisode(
      canonicalTv && typeof canonicalTv.episode === 'number' && canonicalTv.episode > 0 ? canonicalTv.episode : ''
    );
    setTorrentResults([]);
    setHasSearched(false);
    setLastQuery('');
  }, [metaDetail]);

  const handleFindTorrents = async () => {
    if (!metaDetail) return;
    const seasonNumber = season === '' ? null : Number(season);
    const episodeNumber = episode === '' ? null : Number(episode);
    const payload = {
      type: metaDetail.type,
      canonicalTitle: metaDetail.canonical.query || metaDetail.title,
      movie: metaDetail.canonical.movie ?? undefined,
      tv: metaDetail.canonical.tv
        ? { ...metaDetail.canonical.tv, season: seasonNumber, episode: episodeNumber }
        : metaDetail.type === 'tv'
        ? { title: metaDetail.title, season: seasonNumber, episode: episodeNumber }
        : undefined,
      album: metaDetail.canonical.album ?? undefined,
    };

    setIsIndexing(true);
    setHasSearched(true);
    try {
      const response = await startIndexing(payload);
      setTorrentResults(response.results);
      setLastQuery(response.query);
      if (response.results.length === 0) {
        toast('No torrents found. Try adjusting the season, episode or query.');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to search torrents';
      toast.error(message);
    } finally {
      setIsIndexing(false);
    }
  };

  const content = useMemo(() => {
    if (isMetaFlow) {
      if (isMetaLoading) return <LoadingState />;
      if (isMetaError || !metaDetail) return <ErrorState />;
      return (
        <MetaDetailContent
          detail={metaDetail}
          season={season}
          episode={episode}
          setSeason={setSeason}
          setEpisode={setEpisode}
          onFindTorrents={handleFindTorrents}
          isIndexing={isIndexing}
          results={torrentResults}
          hasSearched={hasSearched}
          lastQuery={lastQuery}
        />
      );
    }

    if (isLoading) return <LoadingState />;
    if (isError || !data) return <ErrorState />;
    return <DetailContent detail={data} />;
  }, [
    isMetaFlow,
    isMetaLoading,
    isMetaError,
    metaDetail,
    season,
    episode,
    handleFindTorrents,
    isIndexing,
    torrentResults,
    hasSearched,
    lastQuery,
    isLoading,
    isError,
    data,
  ]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        {content}
        <DialogFooter className="mt-6">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface MetaDetailContentProps {
  detail: MetaDetailType;
  season: number | '';
  episode: number | '';
  setSeason: (value: number | '') => void;
  setEpisode: (value: number | '') => void;
  onFindTorrents: () => void;
  isIndexing: boolean;
  results: JackettSearchItem[];
  hasSearched: boolean;
  lastQuery: string;
}

function MetaDetailContent({
  detail,
  season,
  episode,
  setSeason,
  setEpisode,
  onFindTorrents,
  isIndexing,
  results,
  hasSearched,
  lastQuery,
}: MetaDetailContentProps) {
  const cast = detail.cast.slice(0, 6);
  const tracklist = detail.album?.tracklist ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        <div className="overflow-hidden rounded-3xl border border-border/60 bg-muted/40">
          {detail.poster ? (
            <img src={detail.poster} alt={detail.title} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">No artwork</div>
          )}
        </div>
        <div className="space-y-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground">
              {detail.title}
              {detail.year ? <span className="text-muted-foreground"> ({detail.year})</span> : null}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {detail.runtime ? (
                <span className="flex items-center gap-1">
                  <Clock3 className="h-4 w-4" />
                  {detail.type === 'tv' ? `${detail.runtime} min / episode` : `${detail.runtime} min`}
                </span>
              ) : null}
              {typeof detail.rating === 'number' ? (
                <span className="flex items-center gap-1">
                  <Star className="h-4 w-4 text-yellow-400" />
                  {detail.rating.toFixed(1)}
                </span>
              ) : null}
              {detail.genres.map((genre) => (
                <span key={genre} className="rounded-full bg-foreground/10 px-2 py-1">
                  {genre}
                </span>
              ))}
            </div>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {detail.synopsis || 'No synopsis available yet.'}
          </p>
          {cast.length ? (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Top cast</h3>
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                {cast.map((member) => (
                  <span key={member.name} className="rounded-full bg-foreground/10 px-3 py-1">
                    {member.name}
                    {member.character ? <span className="text-muted-foreground/70"> as {member.character}</span> : null}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {detail.type === 'tv' ? (
            <div className="space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4">
              <h3 className="text-sm font-semibold text-foreground">Refine episode search</h3>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-muted-foreground">
                  Season
                  <Input
                    type="number"
                    min={1}
                    value={season}
                    onChange={(event) => {
                      const value = event.target.value;
                      setSeason(value === '' ? '' : Number(value));
                    }}
                    className="mt-1"
                  />
                </label>
                <label className="text-xs text-muted-foreground">
                  Episode
                  <Input
                    type="number"
                    min={1}
                    value={episode}
                    onChange={(event) => {
                      const value = event.target.value;
                      setEpisode(value === '' ? '' : Number(value));
                    }}
                    className="mt-1"
                  />
                </label>
              </div>
            </div>
          ) : null}
          {detail.type === 'album' && tracklist.length ? (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Tracklist</h3>
              <div className="max-h-48 space-y-1 overflow-y-auto rounded-2xl border border-border/60 bg-background/60 p-3 text-xs text-muted-foreground">
                {tracklist.map((track) => (
                  <div key={`${track.position}-${track.title}`} className="flex items-center justify-between gap-3">
                    <span>
                      {track.position ? `${track.position} ` : null}
                      {track.title}
                    </span>
                    {track.duration ? <span className="font-mono text-muted-foreground/80">{track.duration}</span> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {detail.album?.styles?.length ? (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {detail.album.styles.map((style) => (
                <span key={style} className="rounded-full bg-foreground/10 px-2 py-1">
                  {style}
                </span>
              ))}
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={onFindTorrents} disabled={isIndexing} className="flex items-center gap-2">
              {isIndexing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              {isIndexing ? 'Searching…' : 'Find Torrents'}
            </Button>
            {lastQuery ? (
              <span className="text-xs text-muted-foreground">
                Query: <span className="font-mono text-foreground/80">{lastQuery}</span>
              </span>
            ) : null}
          </div>
        </div>
      </div>
      {isIndexing ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-sm text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-[color:var(--accent)]" /> Searching Jackett…
        </div>
      ) : results.length ? (
        <TorrentResults results={results} />
      ) : hasSearched ? (
        <div className="rounded-2xl border border-dashed border-border/60 bg-background/60 p-6 text-center text-sm text-muted-foreground">
          No torrents were returned for this query.
        </div>
      ) : null}
    </div>
  );
}

export default DetailDialog;
