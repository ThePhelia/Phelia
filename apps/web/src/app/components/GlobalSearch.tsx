import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { useDebounce } from '@/app/hooks/useDebounce';
import { useMetaSearch } from '@/app/lib/api';
import type { MetaSearchItem } from '@/app/types/meta';
import { cn } from '@/app/utils/cn';

const RECENT_KEY = 'phelia:recent-searches';
const SEARCH_KINDS = ['all', 'movie', 'tv', 'music'] as const;

type SearchKind = (typeof SEARCH_KINDS)[number];

function loadRecent(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed.slice(0, 8) as string[]) : [];
  } catch {
    return [];
  }
}

function saveRecent(values: string[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(values.slice(0, 8)));
}

function GlobalSearch() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<SearchKind>('all');
  const [highlight, setHighlight] = useState(0);
  const [recent, setRecent] = useState<string[]>(loadRecent);
  const debounced = useDebounce(query, 350);
  const [open, setOpen] = useState(false);

  const { data, isFetching } = useMetaSearch(debounced);
  const results = useMemo(() => data?.items ?? [], [data]);
  const filteredResults = useMemo(() => {
    if (kind === 'all') return results;
    if (kind === 'music') return results.filter((item) => item.type === 'album');
    return results.filter((item) => item.type === kind);
  }, [results, kind]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === '/' && (event.target as HTMLElement).tagName !== 'INPUT') {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  useEffect(() => {
    setHighlight(0);
  }, [kind, debounced]);

  const visible = open && (debounced.length > 1 || recent.length > 0);

  const handleSubmit = (item?: MetaSearchItem) => {
    const list = filteredResults;
    const next = item ?? list[highlight];
    if (!next) return;
    const dest = `/details/${next.type === 'album' ? 'music' : next.type}/${next.id}?provider=${next.provider}`;
    navigate(dest, { state: { backgroundLocation: location } });
    const updated = [query, ...recent.filter((value) => value !== query && value.trim())]
      .filter(Boolean)
      .slice(0, 8);
    setRecent(updated);
    saveRecent(updated);
    setOpen(false);
  };

  return (
    <div className="relative w-full max-w-2xl">
      <div className="group relative flex items-center rounded-full border border-border/60 bg-background/80 px-4 py-2 shadow-sm focus-within:border-[color:var(--accent)]/80 focus-within:shadow-glow">
        <Search className="mr-2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          value={query}
          placeholder={t('common.searchPlaceholder')}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setHighlight((prev) => Math.min(prev + 1, Math.max(results.length - 1, 0)));
            } else if (event.key === 'ArrowUp') {
              event.preventDefault();
              setHighlight((prev) => Math.max(prev - 1, 0));
            } else if (event.key === 'Enter') {
              event.preventDefault();
              handleSubmit();
            }
          }}
          className="h-9 border-none bg-transparent px-0 text-sm focus-visible:ring-0"
        />
        {query ? (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setOpen(false);
            }}
            className="rounded-full bg-muted/60 p-1 text-muted-foreground transition hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : (
          <span className="ml-auto hidden rounded-full border border-border/70 px-2 py-0.5 text-[10px] uppercase text-muted-foreground sm:block">
            /
          </span>
        )}
      </div>
      {visible ? (
        <div className="absolute left-0 right-0 z-40 mt-2 rounded-2xl border border-border/60 bg-background/95 shadow-2xl backdrop-blur-xl">
          <Tabs
            defaultValue="all"
            value={kind}
            onValueChange={(value) => setKind(value as SearchKind)}
          >
            <TabsList className="mx-auto mt-3 flex w-fit">
              {SEARCH_KINDS.map((option) => (
                <TabsTrigger key={option} value={option} className="capitalize">
                  {option}
                </TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value={kind} className="px-4 pb-3 pt-2">
              {debounced.length <= 1 ? (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p className="text-xs uppercase tracking-widest">Recent</p>
                  {recent.length ? (
                    <ul className="space-y-1">
                      {recent.map((item) => (
                        <li key={item}>
                          <button
                            type="button"
                            className="w-full rounded-lg px-3 py-2 text-left text-foreground transition hover:bg-foreground/10"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => {
                              setQuery(item);
                              setOpen(true);
                            }}
                          >
                            {item}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-muted-foreground">No recent searches yet.</p>
                  )}
                </div>
              ) : filteredResults.length ? (
                <ul className="max-h-80 space-y-1 overflow-y-auto pr-2">
                  {filteredResults.map((item, index) => (
                    <li key={`${item.type}-${item.id}`}>
                      <button
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => handleSubmit(item)}
                        onMouseEnter={() => setHighlight(index)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition',
                          highlight === index ? 'bg-foreground/10' : 'hover:bg-foreground/5',
                        )}
                      >
                        <div className="relative h-14 w-10 overflow-hidden rounded-lg bg-muted">
                          {item.poster ? (
                            <img
                              src={item.poster}
                              alt={item.title}
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : null}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-foreground">{item.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {[item.subtitle, item.year].filter(Boolean).join(' • ')}
                          </p>
                        </div>
                        <span className="rounded-full bg-foreground/10 px-2 py-1 text-[10px] uppercase text-muted-foreground">
                          {item.type}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </div>
              )}
              {filteredResults.length > 0 ? (
                <div className="flex justify-end pt-2">
                  <Button size="sm" variant="ghost" onMouseDown={(event) => event.preventDefault()} onClick={() => handleSubmit()}>
                    {isFetching ? 'Searching…' : t('common.viewDetails')}
                  </Button>
                </div>
              ) : null}
            </TabsContent>
          </Tabs>
        </div>
      ) : null}
    </div>
  );
}

export default GlobalSearch;
