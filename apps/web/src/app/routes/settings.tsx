import { useEffect, useMemo, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import {
  API_BASE,
  useApiKeys,
  useCapabilities,
  useServiceSettings,
  useIntegrationSettings,
  useUpdateDownloadSettings,
  useUpdateIntegrationSettings,
  useUpdateProwlarrSettings,
  useDiscoverProwlarrApiKey,
  useUpdateQbittorrentSettings,
  useProwlarrIndexers,
  useProwlarrIndexerTemplates,
  useCreateProwlarrIndexer,
  useUpdateProwlarrIndexer,
  useDeleteProwlarrIndexer,
  useTestProwlarrIndexer,
} from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';
import { LocalErrorBoundary } from '@/app/components/LocalErrorBoundary';
import type { ProwlarrIndexer, ProwlarrIndexerTemplate } from '@/app/lib/types';
import { normalizeStringList, safeString, safeTrimmedString } from '@/app/utils/safe';

function formatProviderLabel(provider: string): string {
  return provider
    .split(/[-_]/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

const API_KEY_HELP_TEXT: Record<string, string> = {
  tmdb: 'Used for movie and TV metadata lookups and posters.',
  omdb: 'Used for IMDb ratings and fallback movie metadata.',
  fanart: 'Used for additional artwork and background images.',
  discogs: 'Used for album and artist metadata enrichment.',
  lastfm: 'Used for tags, scrobble-style metadata, and popularity signals.',
  listenbrainz: 'Used for listening history and related artist data.',
  deezer: 'Used for music discovery metadata.',
  spotify: 'Used for Spotify music metadata fields.',
  prowlarr: 'Used to authenticate indexer API calls through Prowlarr.',
};

function getApiKeyHelpText(provider: string): string {
  const normalized = provider.toLowerCase();
  if (normalized in API_KEY_HELP_TEXT) return API_KEY_HELP_TEXT[normalized];
  if (normalized.includes('tmdb')) return API_KEY_HELP_TEXT.tmdb;
  if (normalized.includes('spotify')) return API_KEY_HELP_TEXT.spotify;
  if (normalized.includes('prowlarr')) return API_KEY_HELP_TEXT.prowlarr;
  if (normalized.includes('token')) return 'Paste the full provider token exactly as issued.';
  if (normalized.includes('secret')) return 'Paste the full secret value exactly as issued.';
  return 'Paste the full value provided by this service.';
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

  if (!apiKeys.length) {
    return <p className="text-sm text-muted-foreground">No API key providers are available.</p>;
  }

  return (
    <div className="space-y-3">
      {apiKeys.map((apiKey) => {
        const { provider, configured } = apiKey;
        const label = formatProviderLabel(provider);
        const value = formValues[provider] || '';
        const hasValue = value.length > 0;
        const isSaving = savingProvider === provider;
        
        return (
          <div key={provider} className="space-y-2 rounded-lg border border-border/60 p-3">
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
            <p className="text-xs text-muted-foreground">{getApiKeyHelpText(provider)}</p>
          </div>
        );
      })}
    </div>
  );
}


const SECRET_MASK = '••••••••';

function parseValidationRule(rule: string): { minLength?: number; regex?: RegExp } {
  if (rule.startsWith('min_length:')) {
    const min = Number(rule.split(':')[1]);
    return Number.isFinite(min) ? { minLength: min } : {};
  }
  if (rule.startsWith('regex:')) {
    const pattern = rule.slice('regex:'.length);
    try {
      return { regex: new RegExp(pattern) };
    } catch {
      return {};
    }
  }
  return {};
}

function integrationValueError(field: { required: boolean; validation_rule: string; label: string; configured: boolean; masked_at_rest: boolean }, value: string, initialValue: string): string | null {
  const trimmed = safeTrimmedString(value);
  const isMaskedUnchanged = field.masked_at_rest && field.configured && value === initialValue && initialValue === SECRET_MASK;

  if (isMaskedUnchanged) return null;
  if (field.required && !trimmed) {
    return `${field.label} is required.`;
  }
  if (!trimmed) return null;

  const rule = parseValidationRule(field.validation_rule);
  if (rule.minLength && trimmed.length < rule.minLength) {
    return `${field.label} must be at least ${rule.minLength} characters.`;
  }
  if (rule.regex && !rule.regex.test(trimmed)) {
    return `${field.label} format is invalid.`;
  }
  return null;
}

function IntegrationsPanel() {
  const integrationsQuery = useIntegrationSettings();
  const updateIntegrations = useUpdateIntegrationSettings();
  const [values, setValues] = useState<Record<string, string>>({});
  const [initialValues, setInitialValues] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});

  const integrations = integrationsQuery.data?.integrations ?? [];
  const orderedIntegrations = useMemo(
    () => [...integrations].sort((a, b) => {
      const aTmdb = a.key.startsWith('tmdb.') ? 0 : 1;
      const bTmdb = b.key.startsWith('tmdb.') ? 0 : 1;
      if (aTmdb !== bTmdb) return aTmdb - bTmdb;
      return a.label.localeCompare(b.label);
    }),
    [integrations],
  );

  useEffect(() => {
    const nextValues: Record<string, string> = {};
    const nextTouched: Record<string, boolean> = {};
    integrations.forEach((field) => {
      nextValues[field.key] = field.value ?? '';
      nextTouched[field.key] = false;
    });
    setValues(nextValues);
    setInitialValues(nextValues);
    setTouched(nextTouched);
    setRevealed({});
  }, [integrationsQuery.data]);

  const providerHealth = integrations.reduce<Record<string, { configured: number; total: number }>>((acc, field) => {
    const provider = field.key.split('.')[0] ?? 'general';
    const current = acc[provider] ?? { configured: 0, total: 0 };
    current.total += 1;
    if (field.configured) current.configured += 1;
    acc[provider] = current;
    return acc;
  }, {});

  const fieldErrors = integrations.reduce<Record<string, string | null>>((acc, field) => {
    acc[field.key] = integrationValueError(field, values[field.key] ?? '', initialValues[field.key] ?? '');
    return acc;
  }, {});

  const changedKeys = integrations
    .map((field) => field.key)
    .filter((key) => touched[key] && (values[key] ?? '') !== (initialValues[key] ?? ''));

  const hasValidationErrors = changedKeys.some((key) => Boolean(fieldErrors[key]));

  const handleSave = async () => {
    const payload: Record<string, string | null> = {};

    integrations.forEach((field) => {
      const key = field.key;
      if (!touched[key]) return;
      const current = values[key] ?? '';
      const initial = initialValues[key] ?? '';
      if (current === initial) return;

      if (field.masked_at_rest && field.configured && current === SECRET_MASK && initial === SECRET_MASK) {
        return;
      }

      const trimmed = safeTrimmedString(current);
      payload[key] = trimmed ? trimmed : null;
    });

    const payloadKeys = Object.keys(payload);
    if (!payloadKeys.length) return;

    try {
      await updateIntegrations.mutateAsync({ integrations: payload });
      toast.success('Integrations updated');
      await integrationsQuery.refetch();
    } catch (error) {
      toast.error('Failed to update integrations');
    }
  };

  if (integrationsQuery.isLoading) {
    return <Skeleton className="h-24 w-full" />;
  }

  if (integrationsQuery.isError) {
    return <p className="text-sm text-destructive">Failed to load integrations.</p>;
  }

  if (!integrations.length) {
    return <p className="text-sm text-muted-foreground">No integration fields are configured yet.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-foreground">Provider API Keys</h3>
        <p className="text-sm text-muted-foreground">Paste each provider key exactly as issued, then click Save Integrations. TMDB is listed first.</p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {Object.entries(providerHealth).map(([provider, health]) => {
          const healthy = health.configured === health.total;
          return (
            <div key={provider} className="rounded-lg border border-border/60 px-3 py-2 text-xs">
              <div className="font-medium text-foreground">{formatProviderLabel(provider)}</div>
              <div className={healthy ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}>
                {healthy ? 'Configured' : `Unconfigured (${health.configured}/${health.total})`}
              </div>
            </div>
          );
        })}
      </div>

      {orderedIntegrations.map((field) => {
        const value = values[field.key] ?? '';
        const dirty = touched[field.key] && value !== (initialValues[field.key] ?? '');
        const error = fieldErrors[field.key];
        const isSecret = field.masked_at_rest;
        const displayType = isSecret && !revealed[field.key] ? 'password' : 'text';

        return (
          <div key={field.key} className="space-y-2 rounded-lg border border-border/60 p-3">
            <div className="flex items-center justify-between">
              <Label htmlFor={`integration-${field.key}`}>{field.label}</Label>
              <span className="text-xs text-muted-foreground">
                {field.configured ? 'Configured' : 'Unconfigured'}
                {dirty ? ' • Modified' : ' • Unchanged'}
              </span>
            </div>
            <div className="flex gap-2">
              <Input
                id={`integration-${field.key}`}
                type={displayType}
                value={value}
                onChange={(e) => {
                  const next = e.target.value;
                  setValues((prev) => ({ ...prev, [field.key]: next }));
                  setTouched((prev) => ({ ...prev, [field.key]: true }));
                }}
                placeholder={field.configured ? 'Paste a new value to replace the current one' : 'Paste API key / token'}
                disabled={updateIntegrations.isPending}
                className="flex-1"
              />
              {isSecret && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setRevealed((prev) => ({ ...prev, [field.key]: !prev[field.key] }))}
                  disabled={updateIntegrations.isPending}
                >
                  {revealed[field.key] ? 'Hide' : 'Reveal'}
                </Button>
              )}
              {field.configured && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setValues((prev) => ({ ...prev, [field.key]: '' }));
                    setTouched((prev) => ({ ...prev, [field.key]: true }));
                  }}
                  disabled={updateIntegrations.isPending}
                >
                  Clear
                </Button>
              )}
            </div>
            {error ? (
              <p className="text-xs text-destructive">{error}</p>
            ) : (
              <p className="text-xs text-muted-foreground">{getApiKeyHelpText(field.key.split('.')[0] ?? field.key)}</p>
            )}
          </div>
        );
      })}

      <Button
        size="sm"
        onClick={handleSave}
        disabled={updateIntegrations.isPending || !changedKeys.length || hasValidationErrors}
      >
        {updateIntegrations.isPending ? 'Saving...' : 'Save Integrations'}
      </Button>
    </div>
  );
}

function parseDirList(value: unknown): string[] {
  return safeString(value)
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function areEqualLists(a: string[], b: string[]): boolean {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((value, index) => value === b[index]);
}

function normalizeAllowedDirs(value: unknown): string[] {
  if (typeof value === 'string') {
    return parseDirList(value);
  }
  return normalizeStringList(value);
}



function IndexersPanel() {
  const indexersQuery = useProwlarrIndexers();
  const templatesQuery = useProwlarrIndexerTemplates();
  const createIndexer = useCreateProwlarrIndexer();
  const updateIndexer = useUpdateProwlarrIndexer();
  const deleteIndexer = useDeleteProwlarrIndexer();
  const testIndexer = useTestProwlarrIndexer();

  const templates = templatesQuery.data?.templates ?? [];
  const indexers = indexersQuery.data?.indexers ?? [];
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [newName, setNewName] = useState('');
  const [newSettings, setNewSettings] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editSettings, setEditSettings] = useState<Record<string, string>>({});

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [templates, selectedTemplateId],
  );

  const busy = createIndexer.isPending || updateIndexer.isPending || deleteIndexer.isPending || testIndexer.isPending;

  const loadTemplateDefaults = (template: ProwlarrIndexerTemplate | null) => {
    if (!template) {
      setNewSettings({});
      return;
    }
    const defaults: Record<string, string> = {};
    template.fields.forEach((field) => {
      defaults[field.name] = field.value == null ? '' : String(field.value);
    });
    setNewSettings(defaults);
  };

  const startEdit = (indexer: ProwlarrIndexer) => {
    setEditingId(indexer.id);
    setEditName(indexer.name);
    const next: Record<string, string> = {};
    indexer.fields.forEach((field) => {
      next[field.name] = field.value == null ? '' : String(field.value);
    });
    setEditSettings(next);
  };

  const saveNewIndexer = async () => {
    if (!selectedTemplate) return;
    try {
      await createIndexer.mutateAsync({
        template_id: selectedTemplate.id,
        name: newName.trim() || selectedTemplate.name,
        settings: newSettings,
      });
      toast.success('Indexer added');
      setSelectedTemplateId(null);
      setNewName('');
      setNewSettings({});
    } catch (error) {
      toast.error((error as Error).message || 'Failed to add indexer');
    }
  };

  const saveEditIndexer = async () => {
    if (editingId == null) return;
    try {
      await updateIndexer.mutateAsync({
        id: editingId,
        name: editName.trim(),
        settings: editSettings,
      });
      toast.success('Indexer updated');
      setEditingId(null);
      setEditSettings({});
    } catch (error) {
      toast.error((error as Error).message || 'Failed to update indexer');
    }
  };


  if (indexersQuery.isLoading || templatesQuery.isLoading) {
    return <Skeleton className="h-24 w-full" />;
  }

  if (indexersQuery.isError) {
    return <p className="text-sm text-destructive">Failed to load indexers: {indexersQuery.error.message}</p>;
  }

  if (templatesQuery.isError) {
    return <p className="text-sm text-destructive">Failed to load indexer templates: {templatesQuery.error.message}</p>;
  }

  if (!templates.length && !indexers.length) {
    return <p className="text-sm text-muted-foreground">No indexer templates or configured indexers were returned.</p>;
  }

  const handleDelete = async (indexer: ProwlarrIndexer) => {
    if (!window.confirm(`Delete indexer "${indexer.name}"? This cannot be undone.`)) return;
    try {
      await deleteIndexer.mutateAsync({ id: indexer.id });
      toast.success('Indexer deleted');
    } catch (error) {
      toast.error((error as Error).message || 'Failed to delete indexer');
    }
  };

  const handleTest = async (indexer: ProwlarrIndexer) => {
    try {
      const result = await testIndexer.mutateAsync({ id: indexer.id });
      toast.success(result.message || 'Indexer test succeeded');
    } catch (error) {
      toast.error((error as Error).message || 'Indexer test failed');
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-foreground">Indexers</h3>
        <p className="text-sm text-muted-foreground">Manage Prowlarr indexers from Phelia.</p>
      </div>
      <div className="rounded-lg border border-border/60 p-3 space-y-2">
        <Label>Add indexer from template</Label>
        <select
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={selectedTemplateId ?? ''}
          onChange={(e) => {
            const value = e.target.value ? Number(e.target.value) : null;
            setSelectedTemplateId(value);
            const template = templates.find((item) => item.id === value) ?? null;
            loadTemplateDefaults(template);
            setNewName(template?.name ?? '');
          }}
          disabled={busy}
        >
          <option value="">Choose template</option>
          {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
        </select>
        {selectedTemplate && (
          <div className="space-y-2">
            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Indexer name" disabled={busy} />
            {selectedTemplate.fields.slice(0, 8).map((field) => (
              <div key={field.name} className="space-y-1">
                <Label>{field.label}</Label>
                <Input
                  value={newSettings[field.name] ?? ''}
                  onChange={(e) => setNewSettings((prev) => ({ ...prev, [field.name]: e.target.value }))}
                  disabled={busy}
                />
              </div>
            ))}
            <Button size="sm" onClick={saveNewIndexer} disabled={busy || !newName.trim()}>{createIndexer.isPending ? 'Saving...' : 'Add Indexer'}</Button>
          </div>
        )}
      </div>

      <div className="space-y-2">
        {!indexers.length ? <p className="text-sm text-muted-foreground">No indexers configured yet.</p> : null}
        {indexers.map((indexer) => (
          <div key={indexer.id} className="rounded-lg border border-border/60 p-3 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="font-medium text-sm">{indexer.name}</div>
                <div className="text-xs text-muted-foreground">{indexer.implementation_name || indexer.implementation || 'Indexer'}</div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => handleTest(indexer)} disabled={busy}>{testIndexer.isPending ? 'Testing...' : 'Test'}</Button>
                <Button size="sm" variant="outline" onClick={() => startEdit(indexer)} disabled={busy}>Edit</Button>
                <Button size="sm" variant="outline" onClick={() => handleDelete(indexer)} disabled={busy}>Delete</Button>
              </div>
            </div>
            {editingId === indexer.id && (
              <div className="space-y-2">
                <Input value={editName} onChange={(e) => setEditName(e.target.value)} disabled={busy} />
                {indexer.fields.slice(0, 8).map((field) => (
                  <div key={field.name} className="space-y-1">
                    <Label>{field.label}</Label>
                    <Input
                      value={editSettings[field.name] ?? ''}
                      onChange={(e) => setEditSettings((prev) => ({ ...prev, [field.name]: e.target.value }))}
                      disabled={busy}
                    />
                  </div>
                ))}
                <div className="flex gap-2">
                  <Button size="sm" onClick={saveEditIndexer} disabled={busy || !editName.trim()}>{updateIndexer.isPending ? 'Saving...' : 'Save'}</Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingId(null)} disabled={busy}>Cancel</Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ServiceConnections() {
  const serviceQuery = useServiceSettings();
  const updateProwlarr = useUpdateProwlarrSettings();
  const discoverProwlarrApiKey = useDiscoverProwlarrApiKey();
  const updateQbittorrent = useUpdateQbittorrentSettings();
  const updateDownloads = useUpdateDownloadSettings();

  const [prowlarrUrl, setProwlarrUrl] = useState('');
  const [prowlarrApiKey, setProwlarrApiKey] = useState('');
  const [prowlarrAuthUsername, setProwlarrAuthUsername] = useState('');
  const [prowlarrAuthPassword, setProwlarrAuthPassword] = useState('');
  const [prowlarrFetchStatus, setProwlarrFetchStatus] = useState<'idle' | 'fetching' | 'success' | 'failed'>('idle');
  const [qbUrl, setQbUrl] = useState('');
  const [qbUsername, setQbUsername] = useState('');
  const [qbPassword, setQbPassword] = useState('');
  const [allowedDirs, setAllowedDirs] = useState('');
  const [defaultDir, setDefaultDir] = useState('');

  useEffect(() => {
    if (!serviceQuery.data) return;
    setProwlarrUrl(serviceQuery.data.prowlarr?.url ?? '');
    setQbUrl(serviceQuery.data.qbittorrent?.url ?? '');
    setQbUsername(serviceQuery.data.qbittorrent?.username ?? '');
    setAllowedDirs(normalizeAllowedDirs(serviceQuery.data.downloads?.allowed_dirs).join(', '));
    setDefaultDir(serviceQuery.data.downloads?.default_dir ?? '');
  }, [serviceQuery.data]);

  const prowlarrConfigured = serviceQuery.data?.prowlarr?.api_key_configured ?? false;
  const prowlarrFetchBusy = discoverProwlarrApiKey.isPending || updateProwlarr.isPending;
  const canFetchFromCache = !prowlarrConfigured;
  const qbPasswordConfigured = serviceQuery.data?.qbittorrent?.password_configured ?? false;
  const allowedDirList = parseDirList(allowedDirs);
  const persistedAllowedDirs = normalizeAllowedDirs(serviceQuery.data?.downloads?.allowed_dirs);
  const persistedDefaultDir = safeString(serviceQuery.data?.downloads?.default_dir);
  const trimmedDefaultDir = safeTrimmedString(defaultDir);
  const trimmedProwlarrUrl = safeTrimmedString(prowlarrUrl);
  const trimmedProwlarrApiKey = safeTrimmedString(prowlarrApiKey);
  const trimmedQbUrl = safeTrimmedString(qbUrl);
  const trimmedQbUsername = safeTrimmedString(qbUsername);
  const trimmedQbPassword = safeTrimmedString(qbPassword);

  const downloadsChanged =
    persistedDefaultDir !== trimmedDefaultDir ||
    !areEqualLists(allowedDirList, persistedAllowedDirs);

  const prowlarrChanged =
    trimmedProwlarrUrl !== safeString(serviceQuery.data?.prowlarr?.url) ||
    trimmedProwlarrApiKey.length > 0;
  const prowlarrUiUrl = 'http://localhost:9696';
  const qbChanged =
    trimmedQbUrl !== safeString(serviceQuery.data?.qbittorrent?.url) ||
    trimmedQbUsername !== safeString(serviceQuery.data?.qbittorrent?.username) ||
    trimmedQbPassword.length > 0;

  const handleProwlarrSave = async () => {
    const payload: { url?: string | null; api_key?: string | null } = {};
    if (trimmedProwlarrUrl) {
      payload.url = trimmedProwlarrUrl;
    }
    if (trimmedProwlarrApiKey) {
      payload.api_key = trimmedProwlarrApiKey;
    }

    try {
      await updateProwlarr.mutateAsync(payload);
      toast.success('Prowlarr settings updated');
      setProwlarrApiKey('');
    } catch (error) {
      toast.error('Failed to update Prowlarr settings');
    }
  };

  const handleProwlarrClear = async () => {
    try {
      await updateProwlarr.mutateAsync({ api_key: null });
      toast.success('Prowlarr API key cleared');
      setProwlarrApiKey('');
      setProwlarrFetchStatus('idle');
    } catch (error) {
      toast.error('Failed to clear Prowlarr API key');
    }
  };

  const handleProwlarrFetchApiKey = async (forceRefresh = false) => {
    setProwlarrFetchStatus('fetching');
    try {
      const trimmedProwlarrAuthUsername = safeTrimmedString(prowlarrAuthUsername);
      const auth = trimmedProwlarrAuthUsername
        ? { username: trimmedProwlarrAuthUsername, password: safeString(prowlarrAuthPassword) }
        : null;
      const response = await discoverProwlarrApiKey.mutateAsync({
        force_refresh: forceRefresh,
        auth,
      });
      setProwlarrFetchStatus('success');
      toast.success(response.message);
    } catch (error) {
      setProwlarrFetchStatus('failed');
      toast.error(error instanceof Error ? error.message : 'Failed to fetch Prowlarr API key');
    }
  };

  const handleQbSave = async () => {
    const payload: { url?: string | null; username?: string | null; password?: string | null } = {};
    if (trimmedQbUrl) {
      payload.url = trimmedQbUrl;
    }
    if (trimmedQbUsername) {
      payload.username = trimmedQbUsername;
    }
    if (trimmedQbPassword) {
      payload.password = trimmedQbPassword;
    }

    try {
      await updateQbittorrent.mutateAsync(payload);
      toast.success('qBittorrent settings updated');
      setQbPassword('');
    } catch (error) {
      toast.error('Failed to update qBittorrent settings');
    }
  };

  const handleQbClear = async () => {
    try {
      await updateQbittorrent.mutateAsync({ password: null });
      toast.success('qBittorrent password cleared');
      setQbPassword('');
    } catch (error) {
      toast.error('Failed to clear qBittorrent password');
    }
  };

  const handleDownloadSave = async () => {
    try {
      await updateDownloads.mutateAsync({
        allowed_dirs: allowedDirList,
        default_dir: trimmedDefaultDir,
      });
      toast.success('Download paths updated');
    } catch (error) {
      toast.error('Failed to update download paths');
    }
  };

  if (serviceQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (serviceQuery.isError) {
    return (
      <p className="text-sm text-destructive">
        Failed to load service settings{serviceQuery.error?.message ? `: ${serviceQuery.error.message}` : '.'}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground">Prowlarr</h3>
            <p className="text-sm text-muted-foreground">Configure the Prowlarr URL and API key.</p>
          </div>
          <span className="text-xs text-muted-foreground">
            {prowlarrConfigured ? 'API key configured' : 'API key missing'}
          </span>
        </div>
        <div className="space-y-2">
          <Label htmlFor="prowlarr-url">Prowlarr URL</Label>
          <Input
            id="prowlarr-url"
            value={prowlarrUrl}
            onChange={(e) => setProwlarrUrl(e.target.value)}
            placeholder="http://prowlarr:9696"
            disabled={updateProwlarr.isPending}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="prowlarr-api-key">Prowlarr API Key</Label>
          <Input
            id="prowlarr-api-key"
            type="password"
            value={prowlarrApiKey}
            onChange={(e) => setProwlarrApiKey(e.target.value)}
            placeholder={prowlarrConfigured ? 'Enter new API key to replace' : 'Enter API key'}
            disabled={updateProwlarr.isPending}
          />
        </div>
        <div className="space-y-2 rounded-md border border-border p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium">API key discovery</p>
            <span className="text-xs text-muted-foreground">
              {prowlarrFetchStatus === 'fetching' ? 'Fetching…' : prowlarrFetchStatus === 'success' ? 'Success' : prowlarrFetchStatus === 'failed' ? 'Failed' : 'Idle'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">Automatically fetch from Prowlarr config endpoint. Manual API key entry remains available as fallback.</p>
          <div className="grid gap-2 md:grid-cols-2">
            <Input
              value={prowlarrAuthUsername}
              onChange={(e) => setProwlarrAuthUsername(e.target.value)}
              placeholder="Optional local username"
              disabled={prowlarrFetchBusy}
            />
            <Input
              type="password"
              value={prowlarrAuthPassword}
              onChange={(e) => setProwlarrAuthPassword(e.target.value)}
              placeholder="Optional local password"
              disabled={prowlarrFetchBusy}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => handleProwlarrFetchApiKey(false)} disabled={prowlarrFetchBusy || !canFetchFromCache}>
              {discoverProwlarrApiKey.isPending ? 'Fetching...' : 'Fetch API key'}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => handleProwlarrFetchApiKey(true)} disabled={prowlarrFetchBusy}>
              Refresh
            </Button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>Need to add indexers? Open the Prowlarr UI.</span>
          <Button asChild size="sm" variant="outline">
            <a href={prowlarrUiUrl} target="_blank" rel="noreferrer">
              Open Prowlarr UI
            </a>
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={handleProwlarrSave}
            disabled={!prowlarrChanged || updateProwlarr.isPending}
          >
            {updateProwlarr.isPending ? 'Saving...' : 'Save'}
          </Button>
          {prowlarrConfigured && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleProwlarrClear}
              disabled={updateProwlarr.isPending}
            >
              Clear API key
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground">qBittorrent</h3>
            <p className="text-sm text-muted-foreground">Set the qBittorrent WebUI connection.</p>
          </div>
          <span className="text-xs text-muted-foreground">
            {qbPasswordConfigured ? 'Password configured' : 'Password missing'}
          </span>
        </div>
        <div className="space-y-2">
          <Label htmlFor="qb-url">qBittorrent URL</Label>
          <Input
            id="qb-url"
            value={qbUrl}
            onChange={(e) => setQbUrl(e.target.value)}
            placeholder="http://qbittorrent:8080"
            disabled={updateQbittorrent.isPending}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="qb-user">Username</Label>
          <Input
            id="qb-user"
            value={qbUsername}
            onChange={(e) => setQbUsername(e.target.value)}
            placeholder="admin"
            disabled={updateQbittorrent.isPending}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="qb-password">Password</Label>
          <Input
            id="qb-password"
            type="password"
            value={qbPassword}
            onChange={(e) => setQbPassword(e.target.value)}
            placeholder={qbPasswordConfigured ? 'Enter new password to replace' : 'Enter password'}
            disabled={updateQbittorrent.isPending}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={handleQbSave}
            disabled={!qbChanged || updateQbittorrent.isPending}
          >
            {updateQbittorrent.isPending ? 'Saving...' : 'Save'}
          </Button>
          {qbPasswordConfigured && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleQbClear}
              disabled={updateQbittorrent.isPending}
            >
              Clear password
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">Download Paths</h3>
          <p className="text-sm text-muted-foreground">
            Choose the default save directory and allowed paths for downloads.
          </p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="default-download-dir">Default download path</Label>
          <Input
            id="default-download-dir"
            value={defaultDir}
            onChange={(e) => setDefaultDir(e.target.value)}
            placeholder="/downloads"
            disabled={updateDownloads.isPending}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="allowed-download-dirs">Allowed paths</Label>
          <Input
            id="allowed-download-dirs"
            value={allowedDirs}
            onChange={(e) => setAllowedDirs(e.target.value)}
            placeholder="/downloads, /music"
            disabled={updateDownloads.isPending}
          />
          <p className="text-xs text-muted-foreground">Use commas or new lines to separate paths.</p>
        </div>
        <Button
          size="sm"
          onClick={handleDownloadSave}
          disabled={!downloadsChanged || updateDownloads.isPending || !trimmedDefaultDir}
        >
          {updateDownloads.isPending ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}

function SettingsPage() {
  const { data: capabilities } = useCapabilities();
  const { mode, setMode } = useTheme();

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
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
              Configure services and paste API keys in one place. TMDB is included below with the other providers.
            </p>
          </div>
          <LocalErrorBoundary selectorKey="settings.services.connection-cards" title="Service settings unavailable" description="We hit an unexpected error while rendering service connection controls. Try again or refresh this page.">
            <ServiceConnections />
          </LocalErrorBoundary>
          <div className="border-t border-border/60 pt-6">
            <LocalErrorBoundary selectorKey="settings.services.indexer-table" title="Indexer controls unavailable" description="We couldn't render the indexer list. Refresh and verify Prowlarr is reachable.">
              <IndexersPanel />
            </LocalErrorBoundary>
          </div>
          <div className="border-t border-border/60 pt-6">
            <LocalErrorBoundary selectorKey="settings.services.integration-form" title="Integration form unavailable" description="Integration fields failed to render. Refresh and try again.">
              <IntegrationsPanel />
            </LocalErrorBoundary>
          </div>
          <div className="border-t border-border/60 pt-6">
            <h3 className="text-base font-semibold text-foreground">Metadata API Keys</h3>
            <p className="text-sm text-muted-foreground">
              These optional keys are direct provider entries. Paste full values and save per row.
            </p>
          </div>
          <LocalErrorBoundary selectorKey="settings.services.api-key-form" title="API key settings unavailable" description="API key controls crashed while rendering. Refresh and retry your update.">
            <ApiKeyManagement />
          </LocalErrorBoundary>
          {capabilities ? <p className="text-xs text-muted-foreground">Phelia version {capabilities.version}</p> : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SettingsPage;
