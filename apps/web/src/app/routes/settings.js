import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import { useApiKeys, useCapabilities, useInstallPluginFromUrl, usePluginSettings, usePluginSettingsList, useUpdatePluginSettings, useUploadPlugin, } from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
import { cn } from '@/app/utils/cn';
function getPluginFieldType(schema) {
    if (!schema) {
        return 'string';
    }
    if (Array.isArray(schema.enum) && schema.enum.length > 0) {
        return 'select';
    }
    const format = typeof schema.format === 'string' ? schema.format.toLowerCase() : '';
    const rawType = schema.type;
    const typeList = Array.isArray(rawType)
        ? rawType.map((entry) => (typeof entry === 'string' ? entry.toLowerCase() : ''))
        : typeof rawType === 'string'
            ? [rawType.toLowerCase()]
            : [];
    const normalizedTypes = typeList.filter((entry) => entry && entry !== 'null');
    if (normalizedTypes.includes('boolean')) {
        return 'boolean';
    }
    if (format === 'password' || normalizedTypes.includes('password')) {
        return 'password';
    }
    return 'string';
}
function normalizePluginValues(schema, values) {
    const normalized = {};
    const properties = schema?.properties ?? {};
    Object.entries(properties).forEach(([key, fieldSchema]) => {
        const fieldType = getPluginFieldType(fieldSchema);
        let value = values[key];
        if (value === undefined) {
            if (fieldSchema && Object.prototype.hasOwnProperty.call(fieldSchema, 'default')) {
                value = fieldSchema.default;
            }
        }
        if (fieldType === 'boolean') {
            normalized[key] = Boolean(value);
        }
        else if (value === undefined || value === null) {
            normalized[key] = '';
        }
        else {
            normalized[key] = String(value);
        }
    });
    return normalized;
}
function preparePluginSubmitValues(schema, values) {
    const prepared = {};
    const properties = schema?.properties ?? {};
    Object.entries(properties).forEach(([key, fieldSchema]) => {
        const fieldType = getPluginFieldType(fieldSchema);
        const rawValue = values[key];
        if (fieldType === 'boolean') {
            prepared[key] = Boolean(rawValue);
        }
        else if (rawValue === undefined || rawValue === null) {
            prepared[key] = '';
        }
        else if (typeof rawValue === 'string') {
            prepared[key] = rawValue;
        }
        else {
            prepared[key] = String(rawValue);
        }
    });
    return prepared;
}
function arePluginValuesEqual(a, b) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const key of keys) {
        if (a[key] !== b[key]) {
            return false;
        }
    }
    return true;
}
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
function PluginSettingsCard({ plugin }) {
    const schema = plugin.settings_schema ?? null;
    const [open, setOpen] = useState(false);
    const [formValues, setFormValues] = useState({});
    const [baseline, setBaseline] = useState({});
    const pluginValuesQuery = usePluginSettings(plugin.id, { enabled: open });
    const updatePluginSettings = useUpdatePluginSettings(plugin.id);
    useEffect(() => {
        if (!pluginValuesQuery.data) {
            return;
        }
        const normalized = normalizePluginValues(schema, pluginValuesQuery.data.values ?? {});
        setFormValues(normalized);
        setBaseline(normalized);
    }, [pluginValuesQuery.data, schema]);
    const fieldEntries = useMemo(() => Object.entries(schema?.properties ?? {}), [schema?.properties]);
    const requiredFields = useMemo(() => new Set(schema?.required ?? []), [schema?.required]);
    const isDirty = useMemo(() => !arePluginValuesEqual(formValues, baseline), [formValues, baseline]);
    const isSaving = updatePluginSettings.isPending;
    const isLoadingValues = pluginValuesQuery.isLoading || pluginValuesQuery.isFetching;
    const contentId = `${plugin.id}-settings`;
    const handleToggle = () => {
        setOpen((prev) => !prev);
    };
    const handleReset = () => {
        setFormValues(baseline);
    };
    const handleSubmit = async (event) => {
        event.preventDefault();
        const payload = preparePluginSubmitValues(schema, formValues);
        try {
            const result = await updatePluginSettings.mutateAsync({ values: payload });
            const normalized = normalizePluginValues(schema, result.values ?? {});
            setFormValues(normalized);
            setBaseline(normalized);
            toast.success('Settings saved');
        }
        catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to save settings.');
        }
    };
    const hasFields = fieldEntries.length > 0;
    return (_jsxs("div", { className: "space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4", children: [_jsxs("button", { type: "button", onClick: handleToggle, "aria-expanded": open, "aria-controls": contentId, className: "flex w-full items-center justify-between gap-4 text-left", children: [_jsxs("div", { className: "space-y-1", children: [_jsx("h3", { className: "text-base font-semibold text-foreground", children: plugin.name }), schema?.description ? (_jsx("p", { className: "text-sm text-muted-foreground", children: schema.description })) : null] }), _jsx(ChevronDown, { className: cn('h-5 w-5 shrink-0 text-muted-foreground transition-transform', open ? 'rotate-180' : 'rotate-0') })] }), open ? (_jsx("div", { id: contentId, className: "space-y-4", children: pluginValuesQuery.isError ? (_jsxs("p", { className: "text-sm text-destructive", children: ["Failed to load settings", pluginValuesQuery.error?.message ? `: ${pluginValuesQuery.error.message}` : '.'] })) : !schema ? (_jsx("p", { className: "text-sm text-muted-foreground", children: "This plugin did not provide a settings schema." })) : isLoadingValues ? (_jsx("div", { className: "space-y-3", children: Array.from({ length: Math.max(1, fieldEntries.length || 3) }).map((_, index) => (_jsxs("div", { className: "space-y-2", children: [_jsx(Skeleton, { className: "h-4 w-40" }), _jsx(Skeleton, { className: "h-10 w-full" })] }, index))) })) : !hasFields ? (_jsx("p", { className: "text-sm text-muted-foreground", children: "No configurable options are available for this plugin." })) : (_jsxs("form", { className: "space-y-4", onSubmit: handleSubmit, children: [fieldEntries.map(([key, fieldSchema]) => {
                            const fieldType = getPluginFieldType(fieldSchema);
                            const fieldId = `${plugin.id}-${key}`;
                            const label = fieldSchema?.title ?? formatProviderLabel(key);
                            const description = typeof fieldSchema?.description === 'string' ? fieldSchema.description : undefined;
                            const value = formValues[key];
                            const isRequired = requiredFields.has(key);
                            if (fieldType === 'boolean') {
                                return (_jsxs("div", { className: "flex items-center justify-between rounded-xl border border-border/60 bg-background/50 px-4 py-3", children: [_jsxs("div", { className: "space-y-1", children: [_jsx(Label, { htmlFor: fieldId, className: "text-sm font-medium text-foreground", children: label }), description ? _jsx("p", { className: "text-xs text-muted-foreground", children: description }) : null] }), _jsx(Switch, { id: fieldId, checked: Boolean(value), onCheckedChange: (checked) => setFormValues((prev) => ({ ...prev, [key]: checked })), disabled: isSaving || isLoadingValues })] }, key));
                            }
                            const commonLabel = (_jsxs(Label, { htmlFor: fieldId, className: "text-sm font-medium text-foreground", children: [label, isRequired ? _jsx("span", { className: "ml-1 text-destructive", children: "*" }) : null] }));
                            if (fieldType === 'select') {
                                const options = Array.isArray(fieldSchema?.enum) ? fieldSchema.enum : [];
                                const selectValue = typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value);
                                return (_jsxs("div", { className: "space-y-2", children: [commonLabel, description ? _jsx("p", { className: "text-xs text-muted-foreground", children: description }) : null, _jsxs("select", { id: fieldId, value: selectValue, onChange: (event) => setFormValues((prev) => ({ ...prev, [key]: event.target.value })), disabled: isSaving || isLoadingValues, className: "flex h-10 w-full rounded-md border border-input bg-background/60 px-3 py-2 text-sm text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50", children: [!isRequired ? _jsx("option", { value: "", children: "Select an option" }) : null, options.map((option) => {
                                                    const optionValue = option === null ? '' : String(option);
                                                    const optionLabel = typeof option === 'string'
                                                        ? option
                                                        : option === null
                                                            ? 'None'
                                                            : String(option);
                                                    return (_jsx("option", { value: optionValue, children: optionLabel }, optionValue));
                                                })] })] }, key));
                            }
                            const inputType = fieldType === 'password' ? 'password' : 'text';
                            const inputValue = typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value);
                            return (_jsxs("div", { className: "space-y-2", children: [commonLabel, description ? _jsx("p", { className: "text-xs text-muted-foreground", children: description }) : null, _jsx(Input, { id: fieldId, type: inputType, value: inputValue, onChange: (event) => setFormValues((prev) => ({ ...prev, [key]: event.target.value })), disabled: isSaving || isLoadingValues })] }, key));
                        }), _jsxs("div", { className: "flex items-center justify-end gap-2", children: [_jsx(Button, { type: "button", variant: "ghost", onClick: handleReset, disabled: !isDirty || isSaving, children: "Reset" }), _jsx(Button, { type: "submit", disabled: !isDirty || isSaving, children: isSaving ? 'Saving…' : 'Save' })] })] })) })) : null] }));
}
function PluginInstallToolbar() {
    const capsQuery = useCapabilities();
    const uploadMutation = useUploadPlugin();
    const urlMutation = useInstallPluginFromUrl();
    const fileInputRef = useRef(null);
    const canUpload = Boolean(capsQuery.data?.plugins?.upload ?? true);
    const canUrl = Boolean(capsQuery.data?.plugins?.urlInstall ?? true);
    const onPickFile = () => {
        fileInputRef.current?.click();
    };
    const onFileSelected = async (event) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        try {
            await uploadMutation.mutateAsync(file);
            toast.success(`Plugin installed: ${file.name}`);
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            toast.error(`Upload failed: ${message}`);
        }
        finally {
            event.target.value = '';
        }
    };
    const onInstallFromUrl = async () => {
        if (typeof window === 'undefined') {
            return;
        }
        const url = window.prompt('Paste .phex URL:');
        if (!url) {
            return;
        }
        try {
            await urlMutation.mutateAsync({ url });
            toast.success(`Plugin installed from URL: ${url}`);
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            toast.error(`Install failed: ${message}`);
        }
    };
    if (!canUpload && !canUrl) {
        return null;
    }
    return (_jsxs("div", { className: "mb-4 flex flex-wrap gap-2", children: [canUpload ? (_jsxs(_Fragment, { children: [_jsx("input", { ref: fileInputRef, type: "file", accept: ".phex,.tar.gz", className: "hidden", onChange: onFileSelected }), _jsx(Button, { variant: "secondary", onClick: onPickFile, disabled: uploadMutation.isPending, children: uploadMutation.isPending ? 'Uploading…' : 'Upload .phex' })] })) : null, canUrl ? (_jsx(Button, { onClick: onInstallFromUrl, disabled: urlMutation.isPending, children: urlMutation.isPending ? 'Installing…' : 'Install from URL' })) : null] }));
}
function SettingsPage() {
    const { data: capabilities } = useCapabilities();
    const { mode, setMode } = useTheme();
    const pluginListQuery = usePluginSettingsList();
    const pluginsWithSettings = useMemo(() => {
        if (!pluginListQuery.data) {
            return [];
        }
        return pluginListQuery.data.filter((plugin) => plugin.contributes_settings);
    }, [pluginListQuery.data]);
    return (_jsxs("div", { className: "space-y-8", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "Settings" }), _jsxs(Tabs, { defaultValue: "general", className: "space-y-6", children: [_jsxs(TabsList, { children: [_jsx(TabsTrigger, { value: "general", children: "General" }), _jsx(TabsTrigger, { value: "appearance", children: "Appearance" }), _jsx(TabsTrigger, { value: "services", children: "Services" }), _jsx(TabsTrigger, { value: "plugins", children: "Plugins" })] }), _jsxs(TabsContent, { value: "general", className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6", children: [_jsxs("div", { children: [_jsx("h2", { className: "text-lg font-semibold text-foreground", children: "Playback" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Configure your streaming preferences." })] }), _jsx("div", { className: "grid gap-4 text-sm text-muted-foreground", children: _jsx("p", { children: "Streaming preferences are managed by the Phelia server. Adjust them from the server dashboard." }) })] }), _jsx(TabsContent, { value: "appearance", className: "space-y-6 rounded-3xl border border-border/60 bg-background/50 p-6", children: _jsxs("div", { className: "flex items-center justify-between", children: [_jsxs("div", { children: [_jsx(Label, { htmlFor: "theme-toggle", className: "text-foreground", children: "Dark mode" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Toggle between light and dark themes." })] }), _jsx(Switch, { id: "theme-toggle", checked: mode !== 'light', onCheckedChange: (checked) => setMode(checked ? 'dark' : 'light') })] }) }), _jsxs(TabsContent, { value: "services", className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6", children: [_jsxs("div", { className: "space-y-1", children: [_jsx("h2", { className: "text-lg font-semibold text-foreground", children: "Connected Services" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Configure API keys for enhanced metadata and features. TMDB is pre-configured." })] }), _jsx(ApiKeyManagement, {}), capabilities ? _jsxs("p", { className: "text-xs text-muted-foreground", children: ["Phelia version ", capabilities.version] }) : null] }), _jsxs(TabsContent, { value: "plugins", className: "space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6", children: [_jsxs("div", { className: "space-y-1", children: [_jsx("h2", { className: "text-lg font-semibold text-foreground", children: "Plugins" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Manage plugin-specific settings contributed by installed extensions." })] }), _jsx(PluginInstallToolbar, {}), pluginListQuery.isLoading ? (_jsx("div", { className: "space-y-4", children: Array.from({ length: 2 }).map((_, index) => (_jsxs("div", { className: "space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4", "aria-busy": "true", children: [_jsx(Skeleton, { className: "h-5 w-32" }), _jsx(Skeleton, { className: "h-4 w-48" }), _jsxs("div", { className: "space-y-2", children: [_jsx(Skeleton, { className: "h-4 w-40" }), _jsx(Skeleton, { className: "h-10 w-full" })] })] }, index))) })) : pluginListQuery.isError ? (_jsxs("p", { className: "text-sm text-destructive", children: ["Failed to load plugin settings", pluginListQuery.error?.message ? `: ${pluginListQuery.error.message}` : '.'] })) : pluginsWithSettings.length > 0 ? (_jsx("div", { className: "space-y-4", children: pluginsWithSettings.map((plugin) => (_jsx(PluginSettingsCard, { plugin: plugin }, plugin.id))) })) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "No plugins with configurable settings are installed." }))] })] })] }));
}
export default SettingsPage;
