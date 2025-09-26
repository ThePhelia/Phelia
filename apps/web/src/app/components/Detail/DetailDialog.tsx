import { useEffect, useMemo, useState } from 'react';
import { Loader2, Clock3, Star, Search, X } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogClose, DialogContent, DialogFooter } from '@/app/components/ui/dialog';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Skeleton } from '@/app/components/ui/skeleton';
import DetailContent from '@/app/components/Detail/DetailContent';
import { useDetails, useMetaDetail, startIndexing } from '@/app/lib/api';
import type { DetailResponse, MediaKind } from '@/app/lib/types';
import type { MetaDetail as MetaDetailType } from '@/app/types/meta';
import { useTorrentSearch } from '@/app/stores/torrent-search';


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
  const { data, isLoading, isError } = useDetails(kind, id);

  const fallbackMetaParams = useMemo(() => {
    if (isMetaFlow || !data) return undefined;

    const parsed = parseScopedIdentifier(data.title ?? data.id);
    if (!parsed) return undefined;

    const missingOverview = !data.overview || data.overview.trim().length === 0;
    const placeholderTitle = isPlaceholderTitle(data.title, data.id);

    if (!missingOverview && !placeholderTitle) {
      return undefined;
    }

    return parsed;
  }, [data, isMetaFlow]);

  const metaDetailParams = isMetaFlow
    ? { type: kind, id, provider: provider as string }
    : fallbackMetaParams
      ? { type: fallbackMetaParams.type, id: fallbackMetaParams.id, provider: fallbackMetaParams.provider }
      : { type: kind, id: '', provider: '' };

  const {
    data: metaDetail,
    isLoading: isMetaLoading,
    isError: isMetaError,
  } = useMetaDetail(metaDetailParams);

  const fallbackDetail = useMemo(() => {
    if (isMetaFlow || !fallbackMetaParams || !metaDetail) return undefined;
    return metaDetailToDetailResponse(metaDetail, id);
  }, [fallbackMetaParams, id, isMetaFlow, metaDetail]);

  const mergedDetail = useMemo(() => mergeDetailData(data, fallbackDetail), [data, fallbackDetail]);

  const [season, setSeason] = useState<number | ''>('');
  const [episode, setEpisode] = useState<number | ''>('');
  const [hasSearched, setHasSearched] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const fetchTorrentSearch = useTorrentSearch((state) => state.fetchForQuery);

  useEffect(() => {
    if (!isMetaFlow || !metaDetail) return;
    const canonicalTv = metaDetail.canonical.tv;
    setSeason(
      canonicalTv && typeof canonicalTv.season === 'number' && canonicalTv.season > 0 ? canonicalTv.season : ''
    );
    setEpisode(
      canonicalTv && typeof canonicalTv.episode === 'number' && canonicalTv.episode > 0 ? canonicalTv.episode : ''
    );
    setHasSearched(false);
    setLastQuery('');
  }, [isMetaFlow, metaDetail]);

  const handleFindTorrents = async () => {
    if (!isMetaFlow || !metaDetail) return;
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

    setHasSearched(false);
    setLastQuery('');
    setIsIndexing(true);
    try {
      const response = await startIndexing(payload);
      setLastQuery(response.query);
      setHasSearched(true);
      void fetchTorrentSearch(response.query, {
        id,
        title: metaDetail.title,
        kind: metaDetail.type,
        year: typeof metaDetail.year === 'number' ? metaDetail.year : undefined,
        artist: metaDetail.album?.artist,
        subtitle: metaDetail.album?.artist,
      });
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
          hasSearched={hasSearched}
          lastQuery={lastQuery}
        />
      );
    }

    const waitingForFallback = Boolean(fallbackMetaParams) && !fallbackDetail && isMetaLoading;
    if (isLoading || waitingForFallback) return <LoadingState />;

    const encounteredError =
      isError || (Boolean(fallbackMetaParams) && isMetaError);

    if (encounteredError || !mergedDetail) return <ErrorState />;

    return <DetailContent detail={mergedDetail} />;
  }, [
    isMetaFlow,
    isMetaLoading,
    isMetaError,
    metaDetail,
    season,
    episode,
    handleFindTorrents,
    isIndexing,
    hasSearched,
    lastQuery,
    fallbackMetaParams,
    fallbackDetail,
    isLoading,
    isMetaLoading,
    isError,
    mergedDetail,
  ]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="relative w-full max-w-4xl lg:max-w-5xl p-6 sm:p-10">
        <DialogClose className="absolute right-6 top-6 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-background/80 text-muted-foreground transition hover:text-foreground sm:right-8 sm:top-8">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogClose>
        {content}
        <DialogFooter className="mt-8 px-0 pb-0 pt-6 sm:mt-10 sm:px-0 sm:pt-8">
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
      ) : hasSearched ? (
        <div className="space-y-2 rounded-2xl border border-border/60 bg-background/60 p-6 text-sm text-muted-foreground">
          <p>Torrent results have been opened in the Torrent results window.</p>
          <p className="text-xs text-muted-foreground/80">
            Use the Download window to send a torrent to your client or copy its source.
          </p>
        </div>
      ) : null}
    </div>
  );
}

interface ScopedIdentifier {
  provider: string;
  type: MediaKind;
  id: string;
}

function parseScopedIdentifier(value?: string): ScopedIdentifier | undefined {
  if (!value) return undefined;

  const parts = value.split(':');
  if (parts.length < 3) return undefined;

  const [provider, rawType, ...rest] = parts;
  const identifier = rest.join(':');

  if (!provider || !rawType || !identifier) return undefined;

  const normalizedType = rawType.toLowerCase() === 'music' ? 'album' : rawType.toLowerCase();

  if (normalizedType !== 'movie' && normalizedType !== 'tv' && normalizedType !== 'album') {
    return undefined;
  }

  return { provider, type: normalizedType as MediaKind, id: identifier };
}

function isPlaceholderTitle(title?: string, id?: string): boolean {
  if (!title) return true;
  if (id && title === id) return true;

  const parts = title.split(':');
  return parts.length >= 3 && parts[0].length <= 10 && parts[1].length <= 10;
}

function mergeDetailData(primary?: DetailResponse, fallback?: DetailResponse): DetailResponse | undefined {
  if (!primary && !fallback) return undefined;
  if (!fallback) return primary;
  if (!primary) return fallback;

  const merged: DetailResponse = {
    ...fallback,
    ...primary,
    id: primary.id ?? fallback.id,
    kind: primary.kind ?? fallback.kind,
    title: isPlaceholderTitle(primary.title, primary.id) ? fallback.title : primary.title,
    year: primary.year ?? fallback.year,
    tagline: primary.tagline || fallback.tagline,
    overview: primary.overview || fallback.overview,
    poster: primary.poster || fallback.poster,
    backdrop: primary.backdrop || fallback.backdrop,
    rating: primary.rating ?? fallback.rating,
    genres:
      primary.genres && primary.genres.length > 0
        ? primary.genres
        : fallback.genres,
    cast: primary.cast && primary.cast.length > 0 ? primary.cast : fallback.cast,
    crew: primary.crew && primary.crew.length > 0 ? primary.crew : fallback.crew,
    tracks:
      primary.tracks && primary.tracks.length > 0 ? primary.tracks : fallback.tracks,
    seasons:
      primary.seasons && primary.seasons.length > 0 ? primary.seasons : fallback.seasons,
    similar:
      primary.similar && primary.similar.length > 0 ? primary.similar : fallback.similar,
    recommended:
      primary.recommended && primary.recommended.length > 0
        ? primary.recommended
        : fallback.recommended,
    links: primary.links ?? fallback.links,
    availability: primary.availability ?? fallback.availability,
  };

  if (!merged.genres) {
    merged.genres = [];
  }

  return merged;
}

function metaDetailToDetailResponse(metaDetail: MetaDetailType, fallbackId: string): DetailResponse {
  const kind: MediaKind = metaDetail.type === 'album' ? 'album' : metaDetail.type;
  const genres = [...(metaDetail.genres ?? [])];
  if (metaDetail.album?.styles?.length) {
    for (const style of metaDetail.album.styles) {
      if (!genres.includes(style)) {
        genres.push(style);
      }
    }
  }

  const tracks = metaDetail.album?.tracklist?.map((track, index) => ({
    index: index + 1,
    title: track.title,
  }));

  return {
    id: fallbackId,
    kind,
    title: metaDetail.title,
    year: typeof metaDetail.year === 'number' ? metaDetail.year : undefined,
    tagline: metaDetail.album?.artist ?? undefined,
    overview: metaDetail.synopsis ?? undefined,
    poster: metaDetail.poster ?? undefined,
    backdrop: metaDetail.backdrop ?? undefined,
    rating: typeof metaDetail.rating === 'number' ? metaDetail.rating : undefined,
    genres,
    cast: metaDetail.cast.map((member) => ({
      name: member.name,
      role: member.character ?? undefined,
    })),
    crew: [],
    tracks: tracks && tracks.length > 0 ? tracks : undefined,
    seasons: undefined,
    similar: [],
    recommended: [],
    links: undefined,
    availability: undefined,
  };
}

export default DetailDialog;
