import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import { ChevronDown } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import {
  useApiKeys,
  useCapabilities,
  useInstallPluginFromUrl,
  usePluginSettings,
  usePluginSettingsList,
  useUpdatePluginSettings,
  useUploadPlugin,
} from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
import type { PluginSettingFieldSchema, PluginSettingsSchema, PluginSettingsSummary } from '@/app/lib/types';
import { cn } from '@/app/utils/cn';

type PluginFieldType = 'string' | 'password' | 'boolean' | 'select';

function getPluginFieldType(schema?: PluginSettingFieldSchema | null): PluginFieldType {
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

function normalizePluginValues(
  schema: PluginSettingsSchema | null | undefined,
  values: Record<string, unknown>,
): Record<string, unknown> {
  const normalized: Record<string, unknown> = {};
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
    } else if (value === undefined || value === null) {
      normalized[key] = '';
    } else {
      normalized[key] = String(value);
    }
  });

  return normalized;
}

function preparePluginSubmitValues(
  schema: PluginSettingsSchema | null | undefined,
  values: Record<string, unknown>,
): Record<string, unknown> {
  const prepared: Record<string, unknown> = {};
  const properties = schema?.properties ?? {};

  Object.entries(properties).forEach(([key, fieldSchema]) => {
    const fieldType = getPluginFieldType(fieldSchema);
    const rawValue = values[key];

    if (fieldType === 'boolean') {
      prepared[key] = Boolean(rawValue);
    } else if (rawValue === undefined || rawValue === null) {
      prepared[key] = '';
    } else if (typeof rawValue === 'string') {
      prepared[key] = rawValue;
    } else {
      prepared[key] = String(rawValue);
    }
  });

  return prepared;
}

function arePluginValuesEqual(
  a: Record<string, unknown>,
  b: Record<string, unknown>,
): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const key of keys) {
    if (a[key] !== b[key]) {
      return false;
    }
  }
  return true;
}

function formatProviderLabel(provider: string): string {
  return provider
    .split(/[-_]/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

function ApiKeyManagement() {
  const apiKeysQuery = useApiKeys();
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [savingProvider, setSavingProvider] = useState<string | null>(null);

  const apiKeys = apiKeysQuery.data?.api_keys ?? [];

  useEffect(() => {
    // Initialize form values
    const initialValues: Record<string, string> = {};
    apiKeys.forEach((key) => {
      initialValues[key.provider] = '';
    });
    setFormValues(initialValues);
  }, [apiKeys]);

  const handleSave = async (provider: string) => {
    const value = formValues[provider]?.trim() || null;
    setSavingProvider(provider);
    
    try {
      const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';
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
    } catch (error) {
      toast.error(`Failed to update ${formatProviderLabel(provider)} API key`);
    } finally {
      setSavingProvider(null);
    }
  };

  const handleClear = async (provider: string) => {
    setSavingProvider(provider);
    
    try {
      const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';
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
    } catch (error) {
      toast.error(`Failed to clear ${formatProviderLabel(provider)} API key`);
    } finally {
      setSavingProvider(null);
    }
  };

  if (apiKeysQuery.isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (apiKeysQuery.isError) {
    return (
      <p className="text-sm text-destructive">
        Failed to load API keys{apiKeysQuery.error?.message ? `: ${apiKeysQuery.error.message}` : '.'}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {apiKeys.map((apiKey) => {
        const { provider, configured } = apiKey;
        const label = formatProviderLabel(provider);
        const value = formValues[provider] || '';
        const hasValue = value.length > 0;
        const isSaving = savingProvider === provider;
        
        return (
          <div key={provider} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor={`api-key-${provider}`} className="text-sm font-medium text-foreground">
                {label} API Key
              </Label>
              <div className="flex items-center gap-2">
                {configured && (
                  <span className="text-xs text-green-600 dark:text-green-400">Configured</span>
                )}
                {!configured && (
                  <span className="text-xs text-muted-foreground">Not configured</span>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Input
                id={`api-key-${provider}`}
                type="password"
                placeholder={configured ? "Enter new API key to replace" : "Enter API key"}
                value={value}
                onChange={(e) => setFormValues(prev => ({ ...prev, [provider]: e.target.value }))}
                disabled={isSaving}
                className="flex-1"
              />
              <Button
                onClick={() => handleSave(provider)}
                disabled={!hasValue || isSaving}
                size="sm"
              >
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
              {configured && (
                <Button
                  onClick={() => handleClear(provider)}
                  disabled={isSaving}
                  variant="outline"
                  size="sm"
                >
                  Clear
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {provider === 'omdb' && 'OMDb API key for IMDb ratings and metadata'}
              {provider === 'discogs' && 'Discogs token for music metadata'}
              {provider === 'lastfm' && 'Last.fm API key for music scrobbling and tags'}
              {provider === 'listenbrainz' && 'ListenBrainz token for music listening data'}
              {provider === 'spotify_client_id' && 'Spotify Client ID for music metadata'}
              {provider === 'spotify_client_secret' && 'Spotify Client Secret for music metadata'}
              {provider === 'fanart' && 'Fanart.tv API key for additional artwork and images'}
              {provider === 'deezer' && 'Deezer API key for music discovery and metadata'}
            </p>
          </div>
        );
      })}
    </div>
  );
}

interface PluginSettingsCardProps {
  plugin: PluginSettingsSummary;
}

function PluginSettingsCard({ plugin }: PluginSettingsCardProps) {
  const schema = plugin.settings_schema ?? null;
  const [open, setOpen] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [baseline, setBaseline] = useState<Record<string, unknown>>({});

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

  const fieldEntries = useMemo(
    () => Object.entries(schema?.properties ?? {}),
    [schema?.properties],
  );
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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload = preparePluginSubmitValues(schema, formValues);
    try {
      const result = await updatePluginSettings.mutateAsync({ values: payload });
      const normalized = normalizePluginValues(schema, result.values ?? {});
      setFormValues(normalized);
      setBaseline(normalized);
      toast.success('Settings saved');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save settings.');
    }
  };

  const hasFields = fieldEntries.length > 0;

  return (
    <div className="space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4">
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={open}
        aria-controls={contentId}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">{plugin.name}</h3>
          {schema?.description ? (
            <p className="text-sm text-muted-foreground">{schema.description}</p>
          ) : null}
        </div>
        <ChevronDown
          className={cn(
            'h-5 w-5 shrink-0 text-muted-foreground transition-transform',
            open ? 'rotate-180' : 'rotate-0',
          )}
        />
      </button>
      {open ? (
        <div id={contentId} className="space-y-4">
          {pluginValuesQuery.isError ? (
            <p className="text-sm text-destructive">
              Failed to load settings{pluginValuesQuery.error?.message ? `: ${pluginValuesQuery.error.message}` : '.'}
            </p>
          ) : !schema ? (
            <p className="text-sm text-muted-foreground">
              This plugin did not provide a settings schema.
            </p>
          ) : isLoadingValues ? (
            <div className="space-y-3">
              {Array.from({ length: Math.max(1, fieldEntries.length || 3) }).map((_, index) => (
                <div key={index} className="space-y-2">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
            </div>
          ) : !hasFields ? (
            <p className="text-sm text-muted-foreground">No configurable options are available for this plugin.</p>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              {fieldEntries.map(([key, fieldSchema]) => {
                const fieldType = getPluginFieldType(fieldSchema);
                const fieldId = `${plugin.id}-${key}`;
                const label = fieldSchema?.title ?? formatProviderLabel(key);
                const description =
                  typeof fieldSchema?.description === 'string' ? fieldSchema.description : undefined;
                const value = formValues[key];
                const isRequired = requiredFields.has(key);

                if (fieldType === 'boolean') {
                  return (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded-xl border border-border/60 bg-background/50 px-4 py-3"
                    >
                      <div className="space-y-1">
                        <Label htmlFor={fieldId} className="text-sm font-medium text-foreground">
                          {label}
                        </Label>
                        {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
                      </div>
                      <Switch
                        id={fieldId}
                        checked={Boolean(value)}
                        onCheckedChange={(checked) =>
                          setFormValues((prev) => ({ ...prev, [key]: checked }))
                        }
                        disabled={isSaving || isLoadingValues}
                      />
                    </div>
                  );
                }

                const commonLabel = (
                  <Label htmlFor={fieldId} className="text-sm font-medium text-foreground">
                    {label}
                    {isRequired ? <span className="ml-1 text-destructive">*</span> : null}
                  </Label>
                );

                if (fieldType === 'select') {
                  const options = Array.isArray(fieldSchema?.enum) ? fieldSchema.enum : [];
                  const selectValue =
                    typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value);

                  return (
                    <div key={key} className="space-y-2">
                      {commonLabel}
                      {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
                      <select
                        id={fieldId}
                        value={selectValue}
                        onChange={(event) =>
                          setFormValues((prev) => ({ ...prev, [key]: event.target.value }))
                        }
                        disabled={isSaving || isLoadingValues}
                        className="flex h-10 w-full rounded-md border border-input bg-background/60 px-3 py-2 text-sm text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {!isRequired ? <option value="">Select an option</option> : null}
                        {options.map((option) => {
                          const optionValue = option === null ? '' : String(option);
                          const optionLabel =
                            typeof option === 'string'
                              ? option
                              : option === null
                                ? 'None'
                                : String(option);
                          return (
                            <option key={optionValue} value={optionValue}>
                              {optionLabel}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                  );
                }

                const inputType = fieldType === 'password' ? 'password' : 'text';
                const inputValue =
                  typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value);

                return (
                  <div key={key} className="space-y-2">
                    {commonLabel}
                    {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
                    <Input
                      id={fieldId}
                      type={inputType}
                      value={inputValue}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setFormValues((prev) => ({ ...prev, [key]: event.target.value }))
                      }
                      disabled={isSaving || isLoadingValues}
                    />
                  </div>
                );
              })}
              <div className="flex items-center justify-end gap-2">
                <Button type="button" variant="ghost" onClick={handleReset} disabled={!isDirty || isSaving}>
                  Reset
                </Button>
                <Button type="submit" disabled={!isDirty || isSaving}>
                  {isSaving ? 'Saving…' : 'Save'}
                </Button>
              </div>
            </form>
          )}
        </div>
      ) : null}
    </div>
  );
}

function PluginInstallToolbar() {
  const capsQuery = useCapabilities();
  const uploadMutation = useUploadPlugin();
  const urlMutation = useInstallPluginFromUrl();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canUpload = Boolean(capsQuery.data?.plugins?.upload ?? true);
  const canUrl = Boolean(capsQuery.data?.plugins?.urlInstall ?? true);

  const onPickFile = () => {
    fileInputRef.current?.click();
  };

  const onFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      await uploadMutation.mutateAsync(file);
      toast.success(`Plugin installed: ${file.name}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      toast.error(`Upload failed: ${message}`);
    } finally {
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
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      toast.error(`Install failed: ${message}`);
    }
  };

  if (!canUpload && !canUrl) {
    return null;
  }

  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {canUpload ? (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept=".phex,.tar.gz"
            className="hidden"
            onChange={onFileSelected}
          />
          <Button variant="secondary" onClick={onPickFile} disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? 'Uploading…' : 'Upload .phex'}
          </Button>
        </>
      ) : null}
      {canUrl ? (
        <Button onClick={onInstallFromUrl} disabled={urlMutation.isPending}>
          {urlMutation.isPending ? 'Installing…' : 'Install from URL'}
        </Button>
      ) : null}
    </div>
  );
}

function SettingsPage() {
  const { data: capabilities } = useCapabilities();
  const { mode, setMode } = useTheme();

  const pluginListQuery = usePluginSettingsList();
  const pluginsWithSettings = useMemo(() => {
    if (!pluginListQuery.data) {
      return [] as PluginSettingsSummary[];
    }
    return pluginListQuery.data.filter((plugin) => plugin.contributes_settings);
  }, [pluginListQuery.data]);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="plugins">Plugins</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Playback</h2>
            <p className="text-sm text-muted-foreground">Configure your streaming preferences.</p>
          </div>
          <div className="grid gap-4 text-sm text-muted-foreground">
            <p>Streaming preferences are managed by the Phelia server. Adjust them from the server dashboard.</p>
          </div>
        </TabsContent>
        <TabsContent value="appearance" className="space-y-6 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="theme-toggle" className="text-foreground">
                Dark mode
              </Label>
              <p className="text-sm text-muted-foreground">Toggle between light and dark themes.</p>
            </div>
            <Switch
              id="theme-toggle"
              checked={mode !== 'light'}
              onCheckedChange={(checked) => setMode(checked ? 'dark' : 'light')}
            />
          </div>
        </TabsContent>
        <TabsContent value="services" className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-foreground">Connected Services</h2>
            <p className="text-sm text-muted-foreground">
              Configure API keys for enhanced metadata and features. TMDB is pre-configured.
            </p>
          </div>
          <ApiKeyManagement />
          {capabilities ? <p className="text-xs text-muted-foreground">Phelia version {capabilities.version}</p> : null}
        </TabsContent>
        <TabsContent value="plugins" className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-foreground">Plugins</h2>
            <p className="text-sm text-muted-foreground">
              Manage plugin-specific settings contributed by installed extensions.
            </p>
          </div>
          <PluginInstallToolbar />
          {pluginListQuery.isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 2 }).map((_, index) => (
                <div
                  key={index}
                  className="space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4"
                  aria-busy="true"
                >
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : pluginListQuery.isError ? (
            <p className="text-sm text-destructive">
              Failed to load plugin settings{pluginListQuery.error?.message ? `: ${pluginListQuery.error.message}` : '.'}
            </p>
          ) : pluginsWithSettings.length > 0 ? (
            <div className="space-y-4">
              {pluginsWithSettings.map((plugin) => (
                <PluginSettingsCard key={plugin.id} plugin={plugin} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No plugins with configurable settings are installed.
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SettingsPage;
