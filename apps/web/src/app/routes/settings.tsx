import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import { ChevronDown } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import {
  useCapabilities,
  useInstallPluginFromUrl,
  usePluginSettings,
  usePluginSettingsList,
  useProviderSettings,
  useUpdatePluginSettings,
  useUpdateProviderSetting,
  useUploadPlugin,
} from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
import type {
  MetadataProviderSlug,
  PluginSettingFieldSchema,
  PluginSettingsSchema,
  PluginSettingsSummary,
} from '@/app/lib/types';
import { cn } from '@/app/utils/cn';

interface ProviderMeta {
  label: string;
  description: string;
  fieldLabel: string;
  helpPrefix: string;
  helpUrl?: string;
  helpLabel?: string;
  title?: string;
  successLabel?: string;
  inputAriaLabel?: string;
}

const PROVIDER_META: Record<string, ProviderMeta> = {
  tmdb: {
    label: 'TMDb',
    description: 'Unlocks detailed movie and TV metadata from The Movie Database.',
    fieldLabel: 'API key',
    helpPrefix: 'TMDb API key:',
    helpUrl: 'https://www.themoviedb.org/settings/api',
    helpLabel: 'https://www.themoviedb.org/settings/api',
  },
  omdb: {
    label: 'OMDb',
    description: 'Adds IMDb and Rotten Tomatoes ratings alongside TMDb results.',
    fieldLabel: 'API key',
    helpPrefix: 'OMDb API key:',
    helpUrl: 'https://www.omdbapi.com/apikey.aspx',
    helpLabel: 'https://www.omdbapi.com/apikey.aspx',
  },
  discogs: {
    label: 'Discogs',
    description: 'Enriches album searches with Discogs catalogue data.',
    fieldLabel: 'Personal token',
    helpPrefix: 'Discogs personal token:',
    helpUrl: 'https://www.discogs.com/settings/developers',
    helpLabel: 'https://www.discogs.com/settings/developers',
  },
  lastfm: {
    label: 'Last.fm',
    description: 'Surfaces listener stats and top tags from Last.fm.',
    fieldLabel: 'API key',
    helpPrefix: 'Last.fm API key:',
    helpUrl: 'https://www.last.fm/api/account/create',
    helpLabel: 'https://www.last.fm/api/account/create',
  },
  musicbrainz: {
    label: 'MusicBrainz',
    description: 'Sets the user agent string used when contacting MusicBrainz.',
    fieldLabel: 'User agent',
    helpPrefix: 'MusicBrainz user agent:',
    helpUrl: 'https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2#User_Agent',
    helpLabel: 'https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2#User_Agent',
  },
  listenbrainz: {
    label: 'ListenBrainz',
    description: 'Share your ListenBrainz token so Phelia can pull in your listening history.',
    fieldLabel: 'User token',
    helpPrefix: 'ListenBrainz token:',
    helpUrl: 'https://listenbrainz.org/settings/',
    helpLabel: 'https://listenbrainz.org/settings/',
  },
  spotify_client_id: {
    label: 'Spotify',
    title: 'Spotify Client ID',
    description: 'Connect Phelia to your Spotify application by providing its client ID.',
    fieldLabel: 'Client ID',
    helpPrefix: 'Spotify Developer Dashboard:',
    helpUrl: 'https://developer.spotify.com/dashboard',
    helpLabel: 'https://developer.spotify.com/dashboard',
    successLabel: 'Spotify Client ID',
    inputAriaLabel: 'Spotify Client ID',
  },
  spotify_client_secret: {
    label: 'Spotify',
    title: 'Spotify Client Secret',
    description: 'Paste the client secret from your Spotify application. Keep this value private.',
    fieldLabel: 'Client secret',
    helpPrefix: 'Spotify Developer Dashboard:',
    helpUrl: 'https://developer.spotify.com/dashboard',
    helpLabel: 'https://developer.spotify.com/dashboard',
    successLabel: 'Spotify Client Secret',
    inputAriaLabel: 'Spotify Client Secret',
  },
};

const PROVIDER_ORDER: MetadataProviderSlug[] = [
  'tmdb',
  'omdb',
  'discogs',
  'lastfm',
  'musicbrainz',
  'listenbrainz',
  'spotify_client_id',
  'spotify_client_secret',
];

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

function getProviderMeta(provider: string): ProviderMeta {
  if (PROVIDER_META[provider]) {
    return PROVIDER_META[provider];
  }

  const fallbackLabel = formatProviderLabel(provider);
  return {
    label: fallbackLabel,
    description: 'Manage this provider from your Phelia server configuration.',
    fieldLabel: 'Credential',
    helpPrefix: `${fallbackLabel} documentation:`,
  };
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
                      onChange={(event) =>
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
  const providerQuery = useProviderSettings();
  const updateProvider = useUpdateProviderSetting();
  const { mode, setMode } = useTheme();

  const [values, setValues] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [baselines, setBaselines] = useState<Record<string, string>>({});
  const previousPreviewsRef = useRef<Record<string, string>>({});

  const pluginListQuery = usePluginSettingsList();
  const pluginsWithSettings = useMemo(() => {
    if (!pluginListQuery.data) {
      return [] as PluginSettingsSummary[];
    }
    return pluginListQuery.data.filter((plugin) => plugin.contributes_settings);
  }, [pluginListQuery.data]);

  const providers = useMemo(() => {
    if (!providerQuery.data) {
      return [];
    }

    const ordered = [...providerQuery.data];
    ordered.sort((a, b) => {
      const aIndex = PROVIDER_ORDER.indexOf(a.provider as MetadataProviderSlug);
      const bIndex = PROVIDER_ORDER.indexOf(b.provider as MetadataProviderSlug);

      if (aIndex === -1 && bIndex === -1) {
        return a.provider.localeCompare(b.provider);
      }
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    });
    return ordered;
  }, [providerQuery.data]);

  useEffect(() => {
    if (providers.length === 0) {
      previousPreviewsRef.current = {};
      setValues((prev) => (Object.keys(prev).length === 0 ? prev : {}));
      setTouched((prev) => (Object.keys(prev).length === 0 ? prev : {}));
      setBaselines((prev) => (Object.keys(prev).length === 0 ? prev : {}));
      return;
    }

    const providerIds = providers.map((provider) => provider.provider);
    const previousPreviews = previousPreviewsRef.current;

    setBaselines((prev) => {
      const next = { ...prev } as Record<string, string>;
      let changed = false;

      providers.forEach((provider) => {
        const key = provider.provider;
        const incoming = provider.preview ?? '';
        const hasBaseline = Object.prototype.hasOwnProperty.call(next, key);

        if (!touched[key]) {
          const previousPreview = previousPreviews[key];
          if (!hasBaseline) {
            next[key] = incoming;
            changed = true;
          } else if (previousPreview !== incoming && next[key] !== incoming) {
            next[key] = incoming;
            changed = true;
          }
        } else if (!hasBaseline) {
          next[key] = incoming;
          changed = true;
        }
      });

      Object.keys(next).forEach((key) => {
        if (!providerIds.includes(key)) {
          delete next[key];
          changed = true;
        }
      });

      return changed ? next : prev;
    });

    setValues((prev) => {
      const next = { ...prev } as Record<string, string>;
      let changed = false;

      providers.forEach((provider) => {
        const key = provider.provider;
        const incoming = provider.preview ?? '';
        const hasValue = Object.prototype.hasOwnProperty.call(next, key);

        if (!touched[key]) {
          const previousPreview = previousPreviews[key];
          if (!hasValue) {
            next[key] = incoming;
            changed = true;
          } else if (previousPreview !== incoming && next[key] !== incoming) {
            next[key] = incoming;
            changed = true;
          }
        } else if (!hasValue) {
          next[key] = incoming;
          changed = true;
        }
      });

      Object.keys(next).forEach((key) => {
        if (!providerIds.includes(key)) {
          delete next[key];
          changed = true;
        }
      });

      return changed ? next : prev;
    });

    setTouched((prev) => {
      const next = { ...prev } as Record<string, boolean>;
      let changed = false;

      providerIds.forEach((id) => {
        if (!(id in next)) {
          next[id] = false;
          changed = true;
        }
      });

      Object.keys(next).forEach((key) => {
        if (!providerIds.includes(key)) {
          delete next[key];
          changed = true;
        }
      });

      return changed ? next : prev;
    });

    const nextPreviewState: Record<string, string> = {};
    providers.forEach((provider) => {
      nextPreviewState[provider.provider] = provider.preview ?? '';
    });
    previousPreviewsRef.current = nextPreviewState;
  }, [providers, touched]);

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
            <p className="text-sm text-muted-foreground">Manage the API keys that power Phelia's metadata integrations.</p>
          </div>
          {providerQuery.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4"
                  aria-busy="true"
                >
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-10 w-full" />
                  <div className="flex justify-end">
                    <Skeleton className="h-9 w-20" />
                  </div>
                </div>
              ))}
            </div>
          ) : providerQuery.isError ? (
            <p className="text-sm text-destructive">
              Failed to load provider settings{providerQuery.error?.message ? `: ${providerQuery.error.message}` : '.'}
            </p>
          ) : providers.length > 0 ? (
            <ul className="grid gap-4 sm:grid-cols-2">
              {providers.map((provider) => {
                const meta = getProviderMeta(provider.provider);
                const displayLabel = meta.title ?? meta.label;
                const inputId = `provider-${provider.provider}`;
                const currentValue = values[provider.provider] ?? '';
                const baseline = baselines[provider.provider] ?? '';
                const normalizedValue = currentValue.trim();
                const normalizedBaseline = baseline.trim();
                const isDirty = normalizedValue !== normalizedBaseline;
                const isSaving =
                  updateProvider.isPending && updateProvider.variables?.provider === provider.provider;
                const statusClass = provider.configured ? 'text-emerald-400' : 'text-muted-foreground';
                const statusLabel = provider.configured ? 'Configured' : 'Not configured';
                const combinedLabel = `${meta.label}${meta.fieldLabel ? ` ${meta.fieldLabel}` : ''}`.trim();
                const successLabel = meta.successLabel ?? combinedLabel;
                const inputAriaLabel = meta.inputAriaLabel ?? combinedLabel;

                const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  const rawValue = values[provider.provider] ?? '';
                  const trimmed = rawValue.trim();
                  const payload = trimmed.length > 0 ? trimmed : null;

                  try {
                    await updateProvider.mutateAsync({ provider: provider.provider, api_key: payload });
                    const successMessage =
                      payload === null
                        ? `${successLabel} cleared.`
                        : `${successLabel} saved.`;
                    toast.success(successMessage);
                    setTouched((prev) => ({ ...prev, [provider.provider]: false }));
                    setValues((prev) => ({ ...prev, [provider.provider]: payload ?? '' }));
                    setBaselines((prev) => ({ ...prev, [provider.provider]: payload ?? '' }));
                  } catch (error) {
                    toast.error(error instanceof Error ? error.message : 'Failed to update provider.');
                  }
                };

                const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
                  const nextValue = event.target.value;
                  setValues((prev) => ({ ...prev, [provider.provider]: nextValue }));
                  const normalizedNext = nextValue.trim();
                  setTouched((prev) => ({
                    ...prev,
                    [provider.provider]: normalizedNext !== normalizedBaseline,
                  }));
                };

                return (
                  <li key={provider.provider} className="space-y-4 rounded-2xl border border-border/60 bg-background/60 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <h3 className="text-base font-semibold text-foreground">{displayLabel}</h3>
                        <p className="text-sm text-muted-foreground">{meta.description}</p>
                      </div>
                      <span className={`text-xs font-medium ${statusClass}`}>{statusLabel}</span>
                    </div>
                    <form className="space-y-3" onSubmit={handleSubmit}>
                      <div className="space-y-2">
                        <Label htmlFor={inputId} className="text-xs font-medium text-muted-foreground">
                          {meta.fieldLabel}
                        </Label>
                        <Input
                          id={inputId}
                          value={currentValue}
                          onChange={handleChange}
                          placeholder={`Enter ${meta.fieldLabel.toLowerCase()} or leave blank to remove`}
                          aria-label={inputAriaLabel}
                          disabled={isSaving}
                        />
                      </div>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        {meta.helpUrl ? (
                          <p>
                            {meta.helpPrefix}{' '}
                            <a
                              className="text-primary underline"
                              href={meta.helpUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {meta.helpLabel ?? meta.helpUrl}
                            </a>
                          </p>
                        ) : (
                          <p>{meta.helpPrefix}</p>
                        )}
                        <p>Leave blank to remove the saved key.</p>
                      </div>
                      <div className="flex justify-end">
                        <Button type="submit" disabled={!isDirty || isSaving} aria-label={`Save ${successLabel}`}>
                          {isSaving ? 'Saving...' : 'Save'}
                        </Button>
                      </div>
                    </form>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No provider settings available.</p>
          )}
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
