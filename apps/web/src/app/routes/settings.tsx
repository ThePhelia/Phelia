import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { Input } from '@/app/components/ui/input';
import {
  API_BASE,
  useApiKeys,
  useCapabilities,
  useServiceSettings,
  useUpdateDownloadSettings,
  useUpdateJackettSettings,
  useUpdateQbittorrentSettings,
} from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';
import { toast } from 'sonner';

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

function parseDirList(value: string): string[] {
  return value
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

function ServiceConnections() {
  const serviceQuery = useServiceSettings();
  const updateJackett = useUpdateJackettSettings();
  const updateQbittorrent = useUpdateQbittorrentSettings();
  const updateDownloads = useUpdateDownloadSettings();

  const [jackettUrl, setJackettUrl] = useState('');
  const [jackettApiKey, setJackettApiKey] = useState('');
  const [qbUrl, setQbUrl] = useState('');
  const [qbUsername, setQbUsername] = useState('');
  const [qbPassword, setQbPassword] = useState('');
  const [allowedDirs, setAllowedDirs] = useState('');
  const [defaultDir, setDefaultDir] = useState('');

  useEffect(() => {
    if (!serviceQuery.data) return;
    setJackettUrl(serviceQuery.data.jackett.url ?? '');
    setQbUrl(serviceQuery.data.qbittorrent.url ?? '');
    setQbUsername(serviceQuery.data.qbittorrent.username ?? '');
    setAllowedDirs(serviceQuery.data.downloads.allowed_dirs.join(', '));
    setDefaultDir(serviceQuery.data.downloads.default_dir ?? '');
  }, [serviceQuery.data]);

  const jackettConfigured = serviceQuery.data?.jackett.api_key_configured ?? false;
  const qbPasswordConfigured = serviceQuery.data?.qbittorrent.password_configured ?? false;
  const allowedDirList = parseDirList(allowedDirs);
  const downloadsChanged =
    (serviceQuery.data?.downloads.default_dir ?? '') !== defaultDir.trim() ||
    !areEqualLists(allowedDirList, serviceQuery.data?.downloads.allowed_dirs ?? []);

  const jackettChanged =
    jackettUrl.trim() !== (serviceQuery.data?.jackett.url ?? '') ||
    jackettApiKey.trim().length > 0;
  const qbChanged =
    qbUrl.trim() !== (serviceQuery.data?.qbittorrent.url ?? '') ||
    qbUsername.trim() !== (serviceQuery.data?.qbittorrent.username ?? '') ||
    qbPassword.trim().length > 0;

  const handleJackettSave = async () => {
    const payload: { url?: string | null; api_key?: string | null } = {};
    if (jackettUrl.trim()) {
      payload.url = jackettUrl.trim();
    }
    if (jackettApiKey.trim()) {
      payload.api_key = jackettApiKey.trim();
    }

    try {
      await updateJackett.mutateAsync(payload);
      toast.success('Jackett settings updated');
      setJackettApiKey('');
    } catch (error) {
      toast.error('Failed to update Jackett settings');
    }
  };

  const handleJackettClear = async () => {
    try {
      await updateJackett.mutateAsync({ api_key: null });
      toast.success('Jackett API key cleared');
      setJackettApiKey('');
    } catch (error) {
      toast.error('Failed to clear Jackett API key');
    }
  };

  const handleQbSave = async () => {
    const payload: { url?: string | null; username?: string | null; password?: string | null } = {};
    if (qbUrl.trim()) {
      payload.url = qbUrl.trim();
    }
    if (qbUsername.trim()) {
      payload.username = qbUsername.trim();
    }
    if (qbPassword.trim()) {
      payload.password = qbPassword.trim();
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
        default_dir: defaultDir.trim(),
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
            <h3 className="text-base font-semibold text-foreground">Jackett</h3>
            <p className="text-sm text-muted-foreground">Configure the Jackett URL and API key.</p>
          </div>
          <span className="text-xs text-muted-foreground">
            {jackettConfigured ? 'API key configured' : 'API key missing'}
          </span>
        </div>
        <div className="space-y-2">
          <Label htmlFor="jackett-url">Jackett URL</Label>
          <Input
            id="jackett-url"
            value={jackettUrl}
            onChange={(e) => setJackettUrl(e.target.value)}
            placeholder="http://jackett:9117"
            disabled={updateJackett.isPending}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="jackett-api-key">Jackett API Key</Label>
          <Input
            id="jackett-api-key"
            type="password"
            value={jackettApiKey}
            onChange={(e) => setJackettApiKey(e.target.value)}
            placeholder={jackettConfigured ? 'Enter new API key to replace' : 'Enter API key'}
            disabled={updateJackett.isPending}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={handleJackettSave}
            disabled={!jackettChanged || updateJackett.isPending}
          >
            {updateJackett.isPending ? 'Saving...' : 'Save'}
          </Button>
          {jackettConfigured && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleJackettClear}
              disabled={updateJackett.isPending}
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
          disabled={!downloadsChanged || updateDownloads.isPending || !defaultDir.trim()}
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
              Configure API keys for enhanced metadata and features. TMDB is pre-configured.
            </p>
          </div>
          <ServiceConnections />
          <div className="border-t border-border/60 pt-6">
            <h3 className="text-base font-semibold text-foreground">Metadata API Keys</h3>
            <p className="text-sm text-muted-foreground">
              Keys are stored in memory and can be updated without restarting the server.
            </p>
          </div>
          <ApiKeyManagement />
          {capabilities ? <p className="text-xs text-muted-foreground">Phelia version {capabilities.version}</p> : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SettingsPage;
