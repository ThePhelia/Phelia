import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
export const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';
const API_BASE_WITH_SLASH = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;
function buildUrl(path, query) {
    const normalizedPath = path.replace(/^\//, '');
    const url = new URL(normalizedPath, API_BASE_WITH_SLASH);
    if (query) {
        Object.entries(query).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '')
                return;
            url.searchParams.set(key, String(value));
        });
    }
    return url.toString();
}
async function http(path, options = {}) {
    const { query, json, headers, method, body: rawBody, ...rest } = options;
    const url = buildUrl(path, query);
    const finalHeaders = new Headers(headers);
    let body;
    let finalMethod = method ?? (json ? 'POST' : 'GET');
    if (json !== undefined) {
        if (!finalHeaders.has('Content-Type')) {
            finalHeaders.set('Content-Type', 'application/json');
        }
        body = JSON.stringify(json);
    }
    else if (rawBody !== undefined) {
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
        }
        catch {
            // ignore JSON parse errors and fall back to status text
            if (response.statusText) {
                message = response.statusText;
            }
        }
        throw new Error(message);
    }
    if (response.status === 204) {
        return undefined;
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
        return (await response.json());
    }
    return (await response.text());
}
function getNextPageParam(lastPage) {
    if (typeof lastPage.total_pages !== 'number' || typeof lastPage.page !== 'number') {
        return undefined;
    }
    return lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined;
}
export function useSearch(params) {
    const enabled = Boolean(params.q && params.q.trim().length > 1);
    return useInfiniteQuery({
        queryKey: ['search', params],
        queryFn: ({ pageParam = 1, queryKey }) => {
            const [, keyParams] = queryKey;
            return http('search', {
                query: { ...keyParams, page: pageParam },
            });
        },
        initialPageParam: 1,
        getNextPageParam: (lastPage) => getNextPageParam(lastPage),
        enabled,
        staleTime: 60000,
    });
}
export function metaSearch(q, limit = 20) {
    return http('meta/search', { query: { q, limit } });
}
export function metaDetail(params) {
    return http('meta/detail', { query: params });
}
export function useMetaSearch(query, limit = 20) {
    const enabled = query.trim().length > 1;
    return useQuery({
        queryKey: ['meta-search', query, limit],
        queryFn: () => metaSearch(query, limit),
        enabled,
        staleTime: 60000,
    });
}
export function useMetaDetail(params) {
    return useQuery({
        queryKey: ['meta-detail', params],
        queryFn: () => metaDetail(params),
        enabled: Boolean(params.id && params.provider && params.type),
        staleTime: 5 * 60000,
    });
}
export function useDiscover(kind, params) {
    return useInfiniteQuery({
        queryKey: ['discover', kind, params],
        queryFn: ({ pageParam = 1, queryKey }) => {
            const [, keyKind, keyParams] = queryKey;
            return http(`discover/${keyKind}`, {
                query: { ...(keyParams ?? {}), page: pageParam },
            });
        },
        initialPageParam: 1,
        getNextPageParam: (lastPage) => getNextPageParam(lastPage),
        staleTime: 5 * 60000,
    });
}
export function useDetails(kind, id) {
    return useQuery({
        queryKey: ['details', kind, id],
        queryFn: () => http(`details/${kind}/${id}`),
        staleTime: 5 * 60000,
    });
}
export function useDownloads(enabled = true) {
    return useQuery({
        queryKey: ['downloads'],
        queryFn: () => http('downloads'),
        enabled,
        refetchInterval: enabled ? 500 : false,
    });
}
export function useCreateDownload() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (input) => http('downloads', {
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
    return useMutation({
        mutationFn: (id) => http(`downloads/${id}/pause`, {
            method: 'POST',
        }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['downloads'] });
        },
    });
}
export function useResumeDownload() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id) => http(`downloads/${id}/resume`, {
            method: 'POST',
        }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['downloads'] });
        },
    });
}
export function useDeleteDownload() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, withFiles }) => http(`downloads/${id}`, {
            method: 'DELETE',
            query: { withFiles },
        }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['downloads'] });
        },
    });
}
export function useLibrary() {
    return useQuery({
        queryKey: ['library'],
        queryFn: () => http('library'),
        staleTime: 60000,
    });
}
export function useCapabilities() {
    return useQuery({
        queryKey: ['capabilities'],
        queryFn: () => http('capabilities'),
        staleTime: 10 * 60000,
    });
}
export function useInstallPluginFromUrl() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload) => http('market/plugins/install/url', {
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
    return useMutation({
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
    return useQuery({
        queryKey: ['settings', 'plugins'],
        queryFn: async () => {
            const response = await http('settings/plugins');
            return response.plugins ?? [];
        },
        staleTime: 60000,
    });
}
export function usePluginSettings(pluginId, options) {
    const enabled = options?.enabled ?? true;
    return useQuery({
        queryKey: ['settings', 'plugins', pluginId],
        queryFn: () => http(`settings/plugins/${pluginId}`),
        enabled: enabled && Boolean(pluginId),
    });
}
export function useUpdatePluginSettings(pluginId) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload) => http(`settings/plugins/${pluginId}`, {
            method: 'POST',
            json: payload,
        }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['settings', 'plugins', pluginId] });
            void queryClient.invalidateQueries({ queryKey: ['settings', 'plugins'] });
        },
    });
}
export function fetchTorrentSearch(query, options) {
    const limit = options?.limit;
    return http('search', {
        query: {
            q: query,
            ...(typeof limit === 'number' ? { limit } : {}),
        },
    });
}
export function useMutateList() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (input) => http('library/list', { method: 'POST', json: input }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['library'] });
        },
    });
}
// API Key Management
export function useApiKeys() {
    return useQuery({
        queryKey: ['api-keys'],
        queryFn: () => http('settings/api-keys'),
    });
}
export function useUpdateApiKey(provider) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data) => http(`settings/api-keys/${provider}`, { method: 'POST', json: data }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['api-keys'] });
        },
    });
}
export function useUpdateApiKeys() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data) => http('settings/api-keys', { method: 'POST', json: data }),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ['api-keys'] });
        },
    });
}
