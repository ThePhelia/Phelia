import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  CapabilitiesResponse,
  DetailResponse,
  DiscoverItem,
  DiscoverParams,
  DownloadItem,
  LibraryItemSummary,
  ListMutationInput,
  MetadataProviderSlug,
  PaginatedResponse,
  ProviderSettingMutationVariables,
  ProviderSettingStatus,
  ProviderSettingsApiResponse,
  ProviderSettingUpdateRequest,
  SearchParams,
  SearchResponse,
} from './types';
import type {
  JackettSearchResponse,
  MetaDetail,
  MetaSearchResponse,
  StartIndexingPayload as MetaStartIndexingPayload,
} from '@/app/types/meta';

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
      return http<SearchResponse>('search', {
        query: { ...keyParams, page: pageParam },
      });
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPageParam(lastPage),
    enabled,
    staleTime: 60_000,
  });
}

export function metaSearch(q: string, limit = 20): Promise<MetaSearchResponse> {
  return http<MetaSearchResponse>('meta/search', { query: { q, limit } });
}

export function metaDetail(params: { type: 'movie' | 'tv' | 'album'; id: string; provider: string }) {
  return http<MetaDetail>('meta/detail', { query: params });
}

export function startIndexing(payload: MetaStartIndexingPayload) {
  return http<JackettSearchResponse>('index/start', { json: payload });
}

export function useMetaSearch(query: string, limit = 20) {
  const enabled = query.trim().length > 1;

  return useQuery<MetaSearchResponse, Error>({
    queryKey: ['meta-search', query, limit],
    queryFn: () => metaSearch(query, limit),
    enabled,
    staleTime: 60_000,
  });
}

export function useMetaDetail(params: { type: 'movie' | 'tv' | 'album'; id: string; provider: string }) {
  return useQuery<MetaDetail, Error>({
    queryKey: ['meta-detail', params],
    queryFn: () => metaDetail(params),
    enabled: Boolean(params.id && params.provider && params.type),
    staleTime: 5 * 60_000,
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
    refetchInterval: enabled ? 500 : false,
  });
}

export interface CreateDownloadInput {
  magnet?: string;
  url?: string;
}

interface CreateDownloadResponse {
  id: number;
}

export function useCreateDownload() {
  const queryClient = useQueryClient();

  return useMutation<CreateDownloadResponse, Error, CreateDownloadInput>({
    mutationFn: (input) =>
      http<CreateDownloadResponse>('downloads', {
        method: 'POST',
        json: input,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['downloads'] });
    },
  });
}

export function usePauseDownload() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (id) =>
      http<void>(`downloads/${id}/pause`, {
        method: 'POST',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['downloads'] });
    },
  });
}

export function useResumeDownload() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (id) =>
      http<void>(`downloads/${id}/resume`, {
        method: 'POST',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['downloads'] });
    },
  });
}

interface DeleteDownloadInput {
  id: number;
  withFiles?: boolean;
}

export function useDeleteDownload() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, DeleteDownloadInput>({
    mutationFn: ({ id, withFiles }) =>
      http<void>(`downloads/${id}`, {
        method: 'DELETE',
        query: { withFiles },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['downloads'] });
    },
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

function normalizeProviderSettings(response: ProviderSettingsApiResponse): ProviderSettingStatus[] {
  const payload = 'providers' in response ? response.providers : response;

  if (Array.isArray(payload)) {
    return payload.map((item) => ({
      provider: item.provider,
      configured: Boolean(item.configured),
      preview: item.preview ?? undefined,
    }));
  }

  return Object.entries(payload).map(([provider, value]) => {
    const entry = value as ProviderSettingStatus;
    return {
      provider: (entry.provider ?? provider) as MetadataProviderSlug,
      configured: Boolean(entry.configured),
      preview: entry.preview ?? undefined,
    };
  });
}

export function useProviderSettings() {
  return useQuery<ProviderSettingStatus[], Error>({
    queryKey: ['settings', 'providers'],
    queryFn: async () => {
      const response = await http<ProviderSettingsApiResponse>('settings/providers');
      return normalizeProviderSettings(response);
    },
    staleTime: 60_000,
  });
}

export function useUpdateProviderSetting() {
  const queryClient = useQueryClient();

  return useMutation<ProviderSettingStatus, Error, ProviderSettingMutationVariables>({
    mutationFn: ({ provider, api_key }) => {
      const payload: ProviderSettingUpdateRequest = { api_key };
      return http<ProviderSettingStatus>(`settings/providers/${provider}`, {
        method: 'PUT',
        json: payload,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings', 'providers'] });
    },
  });
}

export function fetchJackettSearch(query: string, options?: { limit?: number }) {
  const limit = options?.limit;
  return http<SearchResponse>('search', {
    query: {
      q: query,
      ...(typeof limit === 'number' ? { limit } : {}),
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
