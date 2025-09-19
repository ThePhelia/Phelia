import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Compass, Download, Home, Music2, Search, Settings, Tv, Film } from 'lucide-react';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/app/components/ui/command';
import { useUiState } from '@/app/stores/ui';
import { useDebounce } from '@/app/hooks/useDebounce';
import { useSearch } from '@/app/lib/api';

const NAV_ITEMS = [
  { label: 'Home', icon: Home, to: '/' },
  { label: 'Movies', icon: Film, to: '/movies' },
  { label: 'TV Shows', icon: Tv, to: '/tv' },
  { label: 'Music', icon: Music2, to: '/music' },
  { label: 'Settings', icon: Settings, to: '/settings' },
];

function CommandPalette() {
  const navigate = useNavigate();
  const { commandOpen, setCommandOpen, setDownloadsOpen } = useUiState();
  const location = useLocation();
  const [search, setSearch] = useState('');
  const debounced = useDebounce(search, 300);
  const { data, isFetching } = useSearch({ q: debounced, kind: 'all' });
  const results = useMemo(() => data?.pages.flatMap((page) => page.items) ?? [], [data]);

  useEffect(() => {
    function handler(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandOpen(!commandOpen);
      }
    }
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [commandOpen, setCommandOpen]);

  return (
    <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
      <Command className="max-w-2xl">
        <CommandInput
          placeholder="Jump to…"
          value={search}
          onValueChange={setSearch}
          icon={<Search className="h-4 w-4 text-muted-foreground" />}
        />
        <CommandList>
          <CommandEmpty>{isFetching ? 'Searching…' : 'Nothing found.'}</CommandEmpty>
          <CommandGroup heading="Navigate">
            {NAV_ITEMS.map((item) => (
              <CommandItem
                key={item.to}
                onSelect={() => {
                  navigate(item.to);
                  setCommandOpen(false);
                }}
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.label}
                <CommandShortcut>↵</CommandShortcut>
              </CommandItem>
            ))}
            <CommandItem
              onSelect={() => {
                setDownloadsOpen(true);
                setCommandOpen(false);
              }}
            >
              <Download className="mr-2 h-4 w-4" /> Downloads
            </CommandItem>
          </CommandGroup>
          {results.length ? <CommandSeparator /> : null}
          {results.length ? (
            <CommandGroup heading="Search results">
              {results.slice(0, 6).map((item) => (
                <CommandItem
                  key={`${item.kind}-${item.id}`}
                  onSelect={() => {
                    navigate(`/details/${item.kind === 'album' ? 'music' : item.kind}/${item.id}`, {
                      state: { backgroundLocation: location },
                    });
                    setCommandOpen(false);
                  }}
                >
                  <Compass className="mr-2 h-4 w-4" />
                  <span className="flex-1">
                    {item.title}
                    <span className="ml-2 text-xs text-muted-foreground">{item.kind}</span>
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          ) : null}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}

export default CommandPalette;
