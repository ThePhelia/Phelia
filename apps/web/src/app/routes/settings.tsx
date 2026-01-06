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
          <ApiKeyManagement />
          {capabilities ? <p className="text-xs text-muted-foreground">Phelia version {capabilities.version}</p> : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SettingsPage;
