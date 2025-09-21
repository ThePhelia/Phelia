import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  CapabilitiesResponse,
  DetailResponse,
  DiscoverItem,
  DiscoverParams,
  DownloadItem,
  LibraryItemSummary,
  ListMutationInput,
  MediaKind,
  PaginatedResponse,
  SearchParams,
} from './types';

const DEFAULT_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api/v1';

interface RequestConfig extends RequestInit {
  retry?: number;
}

export function createClient(baseUrl: string) {
  async function request<T>(url: string, config: RequestConfig = {}): Promise<T> {
    const { retry = 2, headers, ...init } = config;
    const target = `${baseUrl}${url}`;

    for (let attempt = 0; attempt <= retry; attempt += 1) {
      try {
        const response = await fetch(target, {
          credentials: 'include',
          ...init,
          headers: {
            'Content-Type': 'application/json',
            ...(headers ?? {}),
          },
        });

        if (!response.ok) {
          const data = await response.json().catch(() => null);
          const message =
            data?.detail || data?.message || response.statusText || 'Request failed';
          throw new Error(message);
        }

        if (response.status === 204) return undefined as T;
        const data = (await response.json()) as T;
        return data;
      } catch (error) {
        if (attempt === retry) throw error;
        await new Promise((resolve) => setTimeout(resolve, 250 * (attempt + 1)));
      }
    }

    throw new Error('Unable to fetch');
  }

  return {
    discover: (kind: DiscoverKind, params: DiscoverParams = {}) =>
      request<PaginatedResponse<DiscoverItem>>(
        `/discover/${kind === 'album' ? 'music' : kind}${toQueryString(params)}`,
      )  
    }

    getDetails: (kind: MediaKind, id: string) => request<DetailResponse>(`/details/${kind}/${id}`),
    search: (params: SearchParams) => request<PaginatedResponse<DiscoverItem>>(
        `/search${toQueryString(params)}`,
      ),
    getLibrary: () => request<LibraryItemSummary>('/me/library'),
    mutateList: (input: ListMutationInput) =>
      request('/me/list', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    getCapabilities: () => request<CapabilitiesResponse>('/meta/capabilities'),
    getDownloads: () => request<DownloadItem[]>('/downloads'),
  };
}

export const apiClient = createClient(DEFAULT_BASE);

function toQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) {
      value.forEach((item) => searchParams.append(key, String(item)));
      return;
    }
    searchParams.set(key, String(value));
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

export function useDiscover(
  kind: MediaKind,
  params: DiscoverParams,
) {
  return useInfiniteQuery({
    queryKey: ['discover', kind, params],
    queryFn: ({ pageParam = 1 }) =>
      apiClient.discover(kind, { ...params, page: Number(pageParam) }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage) return undefined;
      if (lastPage.page >= lastPage.total_pages) return undefined;
      return lastPage.page + 1;
    },
    staleTime: 1000 * 60 * 5,
  });
}

export function useDetails(kind: MediaKind, id?: string) {
  return useQuery({
    queryKey: ['details', kind, id],
    enabled: Boolean(id),
    queryFn: () => {
      if (!id) throw new Error('Missing id');
      return apiClient.getDetails(kind, id);
    },
    staleTime: 1000 * 60 * 10,
  });
}

export function useSearch(params: SearchParams) {
  return useInfiniteQuery({
    queryKey: ['search', params],
    queryFn: ({ pageParam = 1 }) =>
      apiClient.search({ ...params, page: Number(pageParam) }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage) return undefined;
      if (lastPage.page >= lastPage.total_pages) return undefined;
      return lastPage.page + 1;
    },
    enabled: Boolean(params.q?.length),
    staleTime: 1000 * 30,
  });
}

export function useLibrary() {
  return useQuery({
    queryKey: ['library'],
    queryFn: () => apiClient.getLibrary(),
    staleTime: 1000 * 60 * 2,
  });
}

export function useMutateList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: apiClient.mutateList,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
}

export function useCapabilities() {
  return useQuery({
    queryKey: ['capabilities'],
    queryFn: () => apiClient.getCapabilities(),
    staleTime: 1000 * 60 * 10,
  });
}

export function useDownloads(enabled: boolean) {
  return useQuery({
    queryKey: ['downloads'],
    queryFn: () => apiClient.getDownloads(),
    enabled,
    refetchInterval: enabled ? 5000 : false,
  });
}

export type { DiscoverItem } from './types';
