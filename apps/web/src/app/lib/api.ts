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
  PluginSettingsListResponse,
  PluginSettingsSummary,
  PluginSettingsUpdateRequest,
  PluginSettingsValuesResponse,
  SearchParams,
  SearchResponse,
} from './types';
import type { MetaDetail, MetaSearchResponse } from '@/app/types/meta';

type QueryRecordValue = string | number | boolean | null | undefined;

interface RequestOptions extends Omit<RequestInit, 'body'> {
  query?: Record<string, QueryRecordValue>;
  json?: unknown;
  body?: BodyInit | null;
}

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';

const API_BASE_WITH_SLASH = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;

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
  const { query, json, headers, method, body: rawBody, ...rest } = options;
  const url = buildUrl(path, query);
  const finalHeaders = new Headers(headers);

  let body: BodyInit | undefined;
  let finalMethod = method ?? (json ? 'POST' : 'GET');

  if (json !== undefined) {
    if (!finalHeaders.has('Content-Type')) {
      finalHeaders.set('Content-Type', 'application/json');
    }
    body = JSON.stringify(json);
  } else if (rawBody !== undefined) {
    body = rawBody ?? undefined;
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
  });
}

export function useInstallPluginFromUrl() {
  const qc = useQueryClient();
  return useMutation<{ id: string; version: string }, Error, { url: string; expectedSha256?: string }>({
    mutationFn: (payload) =>
      http('market/plugins/install/url', {
        method: 'POST',
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['settings', 'plugins'] });
    },
  });
}

export function useUploadPlugin() {
  const qc = useQueryClient();
  return useMutation<{ id: string; version: string }, Error, File>({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append('file', file);
      return http('market/plugins/install/upload', {
        method: 'POST',
        body: form,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['settings', 'plugins'] });
    },
  });
}

export function usePluginSettingsList() {
  return useQuery<PluginSettingsSummary[], Error>({
    queryKey: ['settings', 'plugins'],
    queryFn: async () => {
      const response = await http<PluginSettingsListResponse>('settings/plugins');
      return response.plugins ?? [];
    },
    staleTime: 60_000,
  });
}

interface UsePluginSettingsOptions {
  enabled?: boolean;
}

export function usePluginSettings(
  pluginId: string,
  options?: UsePluginSettingsOptions,
) {
  const enabled = options?.enabled ?? true;

  return useQuery<PluginSettingsValuesResponse, Error>({
    queryKey: ['settings', 'plugins', pluginId],
    queryFn: () => http<PluginSettingsValuesResponse>(`settings/plugins/${pluginId}`),
    enabled: enabled && Boolean(pluginId),
  });
}

export function useUpdatePluginSettings(pluginId: string) {
  const queryClient = useQueryClient();

  return useMutation<PluginSettingsValuesResponse, Error, PluginSettingsUpdateRequest>({
    mutationFn: (payload) =>
      http<PluginSettingsValuesResponse>(`settings/plugins/${pluginId}`, {
        method: 'POST',
        json: payload,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings', 'plugins', pluginId] });
      void queryClient.invalidateQueries({ queryKey: ['settings', 'plugins'] });
    },
  });
}

export function fetchTorrentSearch(query: string, options?: { limit?: number }) {
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

// API Key Management
export function useApiKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: () => http<{ api_keys: Array<{ provider: string; configured: boolean; value?: string }> }>('settings/api-keys'),
  });
}

export function useUpdateApiKey(provider: string) {
  const queryClient = useQueryClient();

  return useMutation<
    { provider: string; configured: boolean; value?: string },
    Error,
    { value: string | null }
  >({
    mutationFn: (data) => http(`settings/api-keys/${provider}`, { method: 'POST', json: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });
}

export function useUpdateApiKeys() {
  const queryClient = useQueryClient();

  return useMutation<
    { api_keys: Array<{ provider: string; configured: boolean; value?: string }> },
    Error,
    { api_keys: Record<string, string | null> }
  >({
    mutationFn: (data) => http('settings/api-keys', { method: 'POST', json: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });
}
