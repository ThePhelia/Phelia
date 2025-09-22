import { useEffect, useMemo, useRef, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import { useCapabilities, useProviderSettings, useUpdateProviderSetting } from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
import type { MetadataProviderSlug } from '@/app/lib/types';

interface ProviderMeta {
  label: string;
  description: string;
  fieldLabel: string;
  helpPrefix: string;
  helpUrl?: string;
  helpLabel?: string;
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
};

const PROVIDER_ORDER: MetadataProviderSlug[] = ['tmdb', 'omdb', 'discogs', 'lastfm', 'musicbrainz'];

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

function SettingsPage() {
  const { data: capabilities, isLoading: capabilitiesLoading } = useCapabilities();
  const providerQuery = useProviderSettings();
  const updateProvider = useUpdateProviderSetting();
  const { mode, setMode } = useTheme();

  const [values, setValues] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [baselines, setBaselines] = useState<Record<string, string>>({});
  const previousPreviewsRef = useRef<Record<string, string>>({});

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
          <TabsTrigger value="jackett">Jackett</TabsTrigger>
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

                const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  const rawValue = values[provider.provider] ?? '';
                  const trimmed = rawValue.trim();
                  const payload = trimmed.length > 0 ? trimmed : null;

                  try {
                    await updateProvider.mutateAsync({ provider: provider.provider, key: payload });
                    const successMessage =
                      payload === null
                        ? `${meta.label} ${meta.fieldLabel} cleared.`
                        : `${meta.label} ${meta.fieldLabel} saved.`;
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
                        <h3 className="text-base font-semibold text-foreground">{meta.label}</h3>
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
                          aria-label={`${meta.label} ${meta.fieldLabel}`}
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
                        <Button type="submit" disabled={!isDirty || isSaving} aria-label={`Save ${meta.label} key`}>
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
        <TabsContent value="jackett" className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-foreground">Jackett Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              Jackett lets you manage and configure torrent indexers that Phelia can search against when looking for
              new media.
            </p>
          </div>
          {capabilitiesLoading ? (
            <Skeleton className="h-12 w-48 rounded-full" />
          ) : capabilities?.jackettUrl ? (
            <Button asChild>
              <a href={capabilities.jackettUrl} target="_blank" rel="noopener noreferrer">
                Open Jackett Dashboard
              </a>
            </Button>
          ) : (
            <div className="space-y-2">
              <Button disabled>Jackett Dashboard Unavailable</Button>
              <p className="text-xs text-muted-foreground">
                The server did not provide a Jackett dashboard link. Contact your administrator if you expect one.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SettingsPage;
