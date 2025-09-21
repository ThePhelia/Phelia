import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Switch } from '@/app/components/ui/switch';
import { Label } from '@/app/components/ui/label';
import { useCapabilities } from '@/app/lib/api';
import { useTheme } from '@/app/components/ThemeProvider';
import { Skeleton } from '@/app/components/ui/skeleton';
import { Button } from '@/app/components/ui/button';

function SettingsPage() {
  const { data, isLoading } = useCapabilities();
  const { mode, setMode } = useTheme();

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
          <h2 className="text-lg font-semibold text-foreground">Connected Services</h2>
          {isLoading ? (
            <Skeleton className="h-32 w-full rounded-2xl" />
          ) : data ? (
            <ul className="grid gap-3 sm:grid-cols-2">
              {Object.entries(data.services).map(([service, enabled]) => (
                <li key={service} className="flex items-center justify-between rounded-2xl border border-border/60 bg-background/60 px-4 py-3 text-sm">
                  <span className="capitalize text-foreground">{service}</span>
                  <span className={enabled ? 'text-emerald-400' : 'text-muted-foreground'}>
                    {enabled ? 'Online' : 'Offline'}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Service status unavailable.</p>
          )}
          {data ? <p className="text-xs text-muted-foreground">Phelia version {data.version}</p> : null}
        </TabsContent>
        <TabsContent value="jackett" className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-6">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-foreground">Jackett Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              Jackett lets you manage and configure torrent indexers that Phelia can search against when looking for
              new media.
            </p>
          </div>
          {isLoading ? (
            <Skeleton className="h-12 w-48 rounded-full" />
          ) : data?.jackettUrl ? (
            <Button asChild>
              <a href={data.jackettUrl} target="_blank" rel="noopener noreferrer">
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
