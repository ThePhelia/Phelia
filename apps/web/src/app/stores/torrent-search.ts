import { create } from 'zustand';
import { fetchTorrentSearch } from '@/app/lib/api';
import type { MediaKind, SearchResultItem } from '@/app/lib/types';

interface TorrentSearchItemContext {
  id?: string;
  title: string;
  kind?: MediaKind;
  year?: number;
  artist?: string;
  subtitle?: string;
}

interface TorrentSearchState {
  open: boolean;
  isLoading: boolean;
  results: SearchResultItem[];
  message?: string;
  error?: string;
  metaError?: string;
  activeItem?: TorrentSearchItemContext;
  query?: string;
  fetchForItem: (item: TorrentSearchItemContext) => Promise<void>;
  fetchForQuery: (query: string, context?: TorrentSearchItemContext) => Promise<void>;
  setOpen: (open: boolean) => void;
}

function buildQuery(item: TorrentSearchItemContext): string {
  const title = item.title?.trim() ?? '';
  const artist = (item.artist ?? item.subtitle ?? '').trim();
  const isAlbum = item.kind === 'album';

  const base = isAlbum && artist
    ? `${artist} - ${title}`.trim()
    : title;

  const parts = [base];
  if (item.year) {
    parts.push(String(item.year));
  }

  return parts
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .join(' ');
}

export const useTorrentSearch = create<TorrentSearchState>((set) => {
  const executeSearch = async (query: string, context?: TorrentSearchItemContext) => {
    const trimmed = query.trim();

    if (!trimmed) {
      set({
        open: true,
        isLoading: false,
        results: [],
        error: 'Unable to fetch torrents without a title.',
        metaError: undefined,
        message: undefined,
        activeItem: context,
        query: undefined,
      });
      return;
    }

    set({
      open: true,
      isLoading: true,
      results: [],
      error: undefined,
      metaError: undefined,
      message: undefined,
      activeItem: context,
      query: trimmed,
    });

    try {
      const response = await fetchTorrentSearch(trimmed);
      set({
        isLoading: false,
        results: response.items ?? [],
        message: typeof response.message === 'string' ? response.message : undefined,
        metaError: typeof response.error === 'string' ? response.error : undefined,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to fetch torrent results.';
      set({
        isLoading: false,
        results: [],
        error: message,
      });
    }
  };

  return {
    open: false,
    isLoading: false,
    results: [],
    message: undefined,
    error: undefined,
    metaError: undefined,
    activeItem: undefined,
    query: undefined,
    async fetchForItem(item) {
      const query = buildQuery(item);
      await executeSearch(query, item);
    },
    async fetchForQuery(query, context) {
      await executeSearch(query, context);
    },
    setOpen(open) {
      set((state) => ({
        open,
        isLoading: open ? state.isLoading : false,
      }));
    },
  };
});
