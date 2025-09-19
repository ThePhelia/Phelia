import { useMemo } from 'react';
import { ChevronDown, RotateCw } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';
import type { DiscoverParams } from '@/app/lib/types';

const SORT_OPTIONS = [
  { value: 'trending', label: 'Trending' },
  { value: 'popular', label: 'Popular' },
  { value: 'new', label: 'New' },
  { value: 'az', label: 'A-Z' },
];

interface FiltersBarProps {
  kind: 'movie' | 'tv' | 'music';
  filters: DiscoverParams & { search?: string };
  onChange: (next: Partial<DiscoverParams & { search?: string }>) => void;
}

const DEFAULT_GENRES: Record<string, string[]> = {
  movie: ['Action', 'Drama', 'Comedy', 'Sci-Fi', 'Thriller'],
  tv: ['Drama', 'Reality', 'Documentary', 'Animation'],
  music: ['Rock', 'Electronic', 'Hip-Hop', 'Jazz'],
};

function FiltersBar({ kind, filters, onChange }: FiltersBarProps) {
  const years = useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 21 }).map((_, index) => String(current - index));
  }, []);

  const genres = DEFAULT_GENRES[kind] ?? [];

  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-border/60 bg-background/50 p-4 shadow-sm md:flex-row md:items-center md:justify-between">
      <div className="flex flex-1 items-center gap-3">
        <Input
          value={filters.search ?? ''}
          onChange={(event) => onChange({ search: event.target.value })}
          placeholder={`Search ${kind === 'music' ? 'albums or artists' : kind}s`}
          className="h-11 rounded-full border-border/70 bg-background/70"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="rounded-full border border-border/60 px-4">
              Sort: {SORT_OPTIONS.find((option) => option.value === filters.sort)?.label ?? 'Trending'}
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[12rem]">
            <DropdownMenuLabel>Sort by</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {SORT_OPTIONS.map((option) => (
              <DropdownMenuItem key={option.value} onSelect={() => onChange({ sort: option.value as DiscoverParams['sort'] })}>
                {option.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="rounded-full border border-border/60 px-4">
              {filters.year ? `Year: ${filters.year}` : 'Year'}
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="max-h-72 min-w-[10rem] overflow-y-auto">
            <DropdownMenuItem onSelect={() => onChange({ year: undefined })}>Any year</DropdownMenuItem>
            {years.map((year) => (
              <DropdownMenuItem key={year} onSelect={() => onChange({ year })}>
                {year}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="rounded-full border border-border/60 px-4">
              {filters.genre ? `Genre: ${filters.genre}` : 'Genre'}
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="min-w-[12rem]">
            <DropdownMenuItem onSelect={() => onChange({ genre: undefined })}>All genres</DropdownMenuItem>
            {genres.map((genre) => (
              <DropdownMenuItem key={genre} onSelect={() => onChange({ genre })}>
                {genre}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {kind === 'music' ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="rounded-full border border-border/60 px-4">
                {filters.type ? `Type: ${filters.type}` : 'Type'}
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onSelect={() => onChange({ type: undefined })}>All types</DropdownMenuItem>
              {['album', 'ep', 'single'].map((type) => (
                <DropdownMenuItem key={type} onSelect={() => onChange({ type: type as DiscoverParams['type'] })}>
                  {type.toUpperCase()}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          className="rounded-full border border-border/60 px-4"
          onClick={() => onChange({ search: '', genre: undefined, year: undefined, sort: 'trending', type: undefined })}
        >
          <RotateCw className="mr-2 h-4 w-4" /> Reset
        </Button>
      </div>
    </div>
  );
}

export default FiltersBar;
