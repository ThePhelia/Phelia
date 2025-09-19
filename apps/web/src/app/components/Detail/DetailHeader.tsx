import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import type { DetailResponse } from '@/app/lib/types';
import { Play } from 'lucide-react';

interface DetailHeaderProps {
  detail: DetailResponse;
}

function DetailHeader({ detail }: DetailHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-border/60 bg-background/80">
      {detail.backdrop ? (
        <img
          src={detail.backdrop}
          alt={detail.title}
          className="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
        />
      ) : null}
      <div className="absolute inset-0 bg-gradient-to-r from-black via-black/80 to-transparent" />
      <div className="relative z-10 grid gap-6 px-10 py-12 sm:grid-cols-[200px_1fr] sm:items-center">
        <div className="mx-auto w-48">
          {detail.poster ? (
            <img
              src={detail.poster}
              alt={detail.title}
              className="rounded-3xl shadow-lg"
              loading="lazy"
            />
          ) : (
            <div className="flex h-64 items-center justify-center rounded-3xl bg-foreground/10 text-muted-foreground">
              No artwork
            </div>
          )}
        </div>
        <div className="space-y-4 text-white">
          <div className="space-y-2">
            <h2 className="text-3xl font-bold sm:text-4xl">{detail.title}</h2>
            <p className="text-sm text-white/70">
              {[detail.year, detail.tagline].filter(Boolean).join(' • ')}
            </p>
            <div className="flex flex-wrap gap-2">
              {detail.genres?.map((genre) => (
                <Badge key={genre} variant="outline" className="border-white/30 text-white">
                  {genre}
                </Badge>
              ))}
            </div>
          </div>
          <p className="max-w-2xl text-sm leading-relaxed text-white/80">{detail.overview}</p>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" className="rounded-full bg-[color:var(--accent)] text-black hover:bg-[color:var(--accent)]/90">
              <Play className="mr-2 h-5 w-5" /> Play
            </Button>
            <Button variant="secondary" size="lg" className="rounded-full bg-white/10 text-white hover:bg-white/20">
              Add to queue
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DetailHeader;
