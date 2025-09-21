import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  CapabilitiesResponse,
  DetailResponse,
  DiscoverItem,
  DiscoverParams,
  DownloadItem,
  LibraryItemSummary,
  ListMutationInput,
  PaginatedResponse,
  SearchParams,
} from './types';

type QueryRecordValue = string | number | boolean | null | undefined;

interface RequestOptions extends Omit<RequestInit, 'body'> {
  query?: Record<string, QueryRecordValue>;
  json?: unknown;
}

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';

const API_BASE_WITH_SLASH = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;

const DEFAULT_JACKETT_URL = 'http://localhost:9117';

function buildUrl(path: string, query?: Record<string, QueryRecordValue>): string {
  const normalizedPath = path.replace(/^\//, '');
  const url = new URL(normalizedPath, API_BASE_WITH_SLASH);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      url.searchParams.set(key, String(value));
    });
  }

  return url.toString();
}

async function http<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { query, json, headers, method, ...rest } = options;
  const url = buildUrl(path, query);
  const finalHeaders = new Headers(headers);

  let body: BodyInit | undefined;
  let finalMethod = method ?? (json ? 'POST' : 'GET');

  if (json !== undefined) {
    if (!finalHeaders.has('Content-Type')) {
      finalHeaders.set('Content-Type', 'application/json');
    }
    body = JSON.stringify(json);
  }

  if (!finalHeaders.has('Accept')) {
    finalHeaders.set('Accept', 'application/json');
  }

  const response = await fetch(url, {
    ...rest,
    method: finalMethod,
    headers: finalHeaders,
    body,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData && typeof errorData.message === 'string') {
        message = errorData.message;
      }
    } catch {
      // ignore JSON parse errors and fall back to status text
      if (response.statusText) {
        message = response.statusText;
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

type SearchQueryKey = ['search', SearchParams];
type DiscoverQueryKey = ['discover', string, DiscoverParams | undefined];

function getNextPageParam<T>(lastPage: PaginatedResponse<T>): number | undefined {
  if (typeof lastPage.total_pages !== 'number' || typeof lastPage.page !== 'number') {
    return undefined;
  }
  return lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined;
}

export function useSearch(params: SearchParams) {
  const enabled = Boolean(params.q && params.q.trim().length > 1);

  return useInfiniteQuery({
    queryKey: ['search', params],
    queryFn: ({ pageParam = 1, queryKey }) => {
      const [, keyParams] = queryKey as SearchQueryKey;
      return http<PaginatedResponse<DiscoverItem>>('search', {
        query: { ...keyParams, page: pageParam },
      });
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPageParam(lastPage),
    enabled,
    staleTime: 60_000,
  });
}

export function useDiscover(kind: string, params?: DiscoverParams) {
  return useInfiniteQuery({
    queryKey: ['discover', kind, params],
    queryFn: ({ pageParam = 1, queryKey }) => {
      const [, keyKind, keyParams] = queryKey as DiscoverQueryKey;
      return http<PaginatedResponse<DiscoverItem>>(`discover/${keyKind}`, {
        query: { ...(keyParams ?? {}), page: pageParam },
      });
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPageParam(lastPage),
    staleTime: 5 * 60_000,
  });
}

export function useDetails(kind: string, id: string) {
  return useQuery<DetailResponse, Error>({
    queryKey: ['details', kind, id],
    queryFn: () => http<DetailResponse>(`details/${kind}/${id}`),
    staleTime: 5 * 60_000,
  });
}

export function useDownloads(enabled = true) {
  return useQuery<DownloadItem[], Error>({
    queryKey: ['downloads'],
    queryFn: () => http<DownloadItem[]>('downloads'),
    enabled,
    refetchInterval: enabled ? 5_000 : false,
  });
}

export function useLibrary() {
  return useQuery<LibraryItemSummary, Error>({
    queryKey: ['library'],
    queryFn: () => http<LibraryItemSummary>('library'),
    staleTime: 60_000,
  });
}

export function useCapabilities() {
  return useQuery<CapabilitiesResponse, Error>({
    queryKey: ['capabilities'],
    queryFn: () => http<CapabilitiesResponse>('capabilities'),
    staleTime: 10 * 60_000,
    select: (capabilities) => {
      if (capabilities.jackettUrl) {
        return capabilities;
      }

      const jackettLink = capabilities.links?.jackett;
      if (jackettLink) {
        return {
          ...capabilities,
          jackettUrl: jackettLink,
        };
      }

      if (capabilities.services['jackett']) {
        return {
          ...capabilities,
          jackettUrl: DEFAULT_JACKETT_URL,
        };
      }

      return capabilities;
    },
  });
}

export function useMutateList() {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean }, Error, ListMutationInput>({
    mutationFn: (input) => http<{ success: boolean }>('library/list', { method: 'POST', json: input }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
}
