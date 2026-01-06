import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import { useApiKeys, useCapabilities } from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
function formatProviderLabel(provider) {
    return provider
        .split(/[-_]/)
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(' ');
}
function ApiKeyManagement() {
    const apiKeysQuery = useApiKeys();
    const [formValues, setFormValues] = useState({});
    const [savingProvider, setSavingProvider] = useState(null);
    const apiKeys = apiKeysQuery.data?.api_keys ?? [];
    useEffect(() => {
        // Initialize form values
        const initialValues = {};
        apiKeys.forEach((key) => {
            initialValues[key.provider] = '';
        });
        setFormValues(initialValues);
    }, [apiKeys]);
    const handleSave = async (provider) => {
        const value = formValues[provider]?.trim() || null;
        setSavingProvider(provider);
        try {
            const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';
            const response = await fetch(`${API_BASE}/settings/api-keys/${provider}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value }),
            });
            if (!response.ok) {
                throw new Error('Failed to update API key');
            }
            toast.success(`${formatProviderLabel(provider)} API key updated`);
            setFormValues(prev => ({ ...prev, [provider]: '' }));
            apiKeysQuery.refetch();
        }
        catch (error) {
            toast.error(`Failed to update ${formatProviderLabel(provider)} API key`);
        }
        finally {
            setSavingProvider(null);
        }
    };
    const handleClear = async (provider) => {
        setSavingProvider(provider);
        try {
            const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';
            const response = await fetch(`${API_BASE}/settings/api-keys/${provider}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: null }),
            });
            if (!response.ok) {
                throw new Error('Failed to clear API key');
            }
            toast.success(`${formatProviderLabel(provider)} API key cleared`);
            setFormValues(prev => ({ ...prev, [provider]: '' }));
            apiKeysQuery.refetch();
        }
        catch (error) {
            toast.error(`Failed to clear ${formatProviderLabel(provider)} API key`);
        }
        finally {
            setSavingProvider(null);
        }
    };
    if (apiKeysQuery.isLoading) {
        return (_jsx("div", { className: "space-y-4", children: Array.from({ length: 4 }).map((_, index) => (_jsxs("div", { className: "space-y-2", children: [_jsx(Skeleton, { className: "h-4 w-32" }), _jsx(Skeleton, { className: "h-10 w-full" })] }, index))) }));
    }
    if (apiKeysQuery.isError) {
        return (_jsxs("p", { className: "text-sm text-destructive", children: ["Failed to load API keys", apiKeysQuery.error?.message ? `: ${apiKeysQuery.error.message}` : '.'] }));
    }
    return (_jsx("div", { className: "space-y-4", children: apiKeys.map((apiKey) => {
            const { provider, configured } = apiKey;
            const label = formatProviderLabel(provider);
            const value = formValues[provider] || '';
            const hasValue = value.length > 0;
            const isSaving = savingProvider === provider;
            return (_jsxs("div", { className: "space-y-2", children: [_jsxs("div", { className: "flex items-center justify-between", children: [_jsxs(Label, { htmlFor: `api-key-${provider}`, className: "text-sm font-medium text-foreground", children: [label, " API Key"] }), _jsxs("div", { className: "flex items-center gap-2", children: [configured && (_jsx("span", { className: "text-xs text-green-600 dark:text-green-400", children: "Configured" })), !configured && (_jsx("span", { className: "text-xs text-muted-foreground", children: "Not configured" }))] })] }), _jsxs("div", { className: "flex gap-2", children: [_jsx(Input, { id: `api-key-${provider}`, type: "password", placeholder: configured ? "Enter new API key to replace" : "Enter API key", value: value, onChange: (e) => setFormValues(prev => ({ ...prev, [provider]: e.target.value })), disabled: isSaving, className: "flex-1" }), _jsx(Button, { onClick: () => handleSave(provider), disabled: !hasValue || isSaving, size: "sm", children: isSaving ? 'Saving...' : 'Save' }), configured && (_jsx(Button, { onClick: () => handleClear(provider), disabled: isSaving, variant: "outline", size: "sm", children: "Clear" }))] }), _jsxs("p", { className: "text-xs text-muted-foreground", children: [provider === 'omdb' && 'OMDb API key for IMDb ratings and metadata', provider === 'discogs' && 'Discogs token for music metadata', provider === 'lastfm' && 'Last.fm API key for music scrobbling and tags', provider === 'listenbrainz' && 'ListenBrainz token for music listening data', provider === 'spotify_client_id' && 'Spotify Client ID for music metadata', provider === 'spotify_client_secret' && 'Spotify Client Secret for music metadata', provider === 'fanart' && 'Fanart.tv API key for additional artwork and images', provider === 'deezer' && 'Deezer API key for music discovery and metadata'] })] }, provider));
        }) }));
}
function SettingsPage() {
    const { data: capabilities } = useCapabilities();
    const { mode, setMode } = useTheme();
    return (_jsxs("div", { className: "space-y-8", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "Settings" }), _jsxs(Tabs, { defaultValue: "general", className: "space-y-6", children: [_jsxs(TabsList, { children: [_jsx(TabsTrigger, { value: "general", children: "General" }), _jsx(TabsTrigger, { value: "appearance", children: "Appearance" }), _jsx(TabsTrigger, { value: "services", children: "Services" })] }), _jsxs(TabsContent, { value: "general", className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6", children: [_jsxs("div", { children: [_jsx("h2", { className: "text-lg font-semibold text-foreground", children: "Playback" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Configure your streaming preferences." })] }), _jsx("div", { className: "grid gap-4 text-sm text-muted-foreground", children: _jsx("p", { children: "Streaming preferences are managed by the Phelia server. Adjust them from the server dashboard." }) })] }), _jsx(TabsContent, { value: "appearance", className: "space-y-6 rounded-3xl border border-border/60 bg-background/50 p-6", children: _jsxs("div", { className: "flex items-center justify-between", children: [_jsxs("div", { children: [_jsx(Label, { htmlFor: "theme-toggle", className: "text-foreground", children: "Dark mode" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Toggle between light and dark themes." })] }), _jsx(Switch, { id: "theme-toggle", checked: mode !== 'light', onCheckedChange: (checked) => setMode(checked ? 'dark' : 'light') })] }) }), _jsxs(TabsContent, { value: "services", className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6", children: [_jsxs("div", { className: "space-y-1", children: [_jsx("h2", { className: "text-lg font-semibold text-foreground", children: "Connected Services" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Configure API keys for enhanced metadata and features. TMDB is pre-configured." })] }), _jsx(ApiKeyManagement, {}), capabilities ? _jsxs("p", { className: "text-xs text-muted-foreground", children: ["Phelia version ", capabilities.version] }) : null] })] })] }));
}
export default SettingsPage;
