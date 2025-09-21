import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, DownloadCloud, Loader2 } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import type { DiscoverItem } from '@/app/lib/types';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTorrentSearch } from '@/app/stores/torrent-search';

interface HeroCarouselProps {
  items: DiscoverItem[];
}

function HeroCarousel({ items }: HeroCarouselProps) {
  const [index, setIndex] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const slides = useMemo(() => items.slice(0, 6), [items]);

  useEffect(() => {
    if (slides.length <= 1) return;
    const interval = window.setInterval(() => {
      setIndex((prev) => (prev + 1) % slides.length);
    }, 6000);
    return () => window.clearInterval(interval);
  }, [slides.length]);

  useEffect(() => {
    setIndex(0);
  }, [slides.length]);

  const fetchTorrents = useTorrentSearch((state) => state.fetchForItem);
  const { isLoading, activeItem } = useTorrentSearch((state) => ({
    isLoading: state.isLoading,
    activeItem: state.activeItem,
  }));
  const current = slides[index];
  if (!current) return null;

  const imageSrc = current.backdrop ?? current.poster;
  const hasImage = Boolean(imageSrc);
  const isCurrentLoading = isLoading && activeItem?.id === current.id;

  const goTo = (next: number) => {
    const length = slides.length;
    setIndex((next + length) % length);
  };

  return (
    <div className="relative overflow-hidden rounded-[2.5rem] border border-border/60 bg-background/60 shadow-xl">
      <AnimatePresence mode="wait">
        <motion.div
          key={current.id}
          initial={{ opacity: 0, scale: 1.02 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.6 }}
          className="relative h-[440px] w-full"
        >
          {hasImage ? (
            <>
              <img
                src={imageSrc}
                alt={current.title}
                className="absolute inset-0 h-full w-full object-cover"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/60 to-transparent" />
            </>
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-foreground/10 via-background/80 to-background" />
          )}
          <div className="relative z-10 flex h-full flex-col justify-center gap-6 px-10 py-12 text-white md:max-w-xl">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.4em] text-white/60">Featured</p>
              <h2 className="text-3xl font-bold md:text-4xl">{current.title}</h2>
              <p className="text-sm text-white/80 line-clamp-3">
                {current.subtitle ?? current.genres?.slice(0, 3).join(' • ')}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-white/70">
              {current.year ? <span>{current.year}</span> : null}
              {current.genres?.slice(0, 2).map((genre) => (
                <span key={genre} className="rounded-full bg-white/10 px-3 py-1">
                  {genre}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <Button
                size="lg"
                variant="accent"
                className="rounded-full shadow-lg"
                disabled={isCurrentLoading}
                onClick={() =>
                  void fetchTorrents({
                    id: current.id,
                    title: current.title,
                    kind: current.kind,
                    year: current.year,
                  })
                }
              >
                {isCurrentLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Fetching…
                  </>
                ) : (
                  <>
                    <DownloadCloud className="mr-2 h-5 w-5" /> Fetch Torrents
                  </>
                )}
              </Button>
              <Button
                variant="ghost"
                size="lg"
                className="rounded-full border border-white/30 text-white hover:bg-white/10"
                onClick={() =>
                  navigate(`/details/${current.kind === 'album' ? 'music' : current.kind}/${current.id}`, {
                    state: { backgroundLocation: location },
                  })
                }
              >
                Learn More
              </Button>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
      {slides.length > 1 ? (
        <>
          <button
            type="button"
            className="absolute left-6 top-1/2 z-20 -translate-y-1/2 rounded-full border border-white/30 bg-black/60 p-3 text-white transition hover:bg-black/80"
            onClick={() => goTo(index - 1)}
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            type="button"
            className="absolute right-6 top-1/2 z-20 -translate-y-1/2 rounded-full border border-white/30 bg-black/60 p-3 text-white transition hover:bg-black/80"
            onClick={() => goTo(index + 1)}
          >
            <ChevronRight className="h-5 w-5" />
          </button>
          <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-2">
            {slides.map((slide, slideIndex) => (
              <button
                key={slide.id}
                type="button"
                className={`h-2 w-8 rounded-full transition ${slideIndex === index ? 'bg-white' : 'bg-white/30'}`}
                onClick={() => goTo(slideIndex)}
                aria-label={`Go to slide ${slideIndex + 1}`}
              />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

export default HeroCarousel;
