import { useIntegrationSettings } from '@/app/lib/api';

export function LegacyApiKeysSection() {
  const integrations = useIntegrationSettings().data?.integrations ?? [];
  const legacy = integrations.filter((i) => ['omdb','discogs','lastfm','listenbrainz','fanart','deezer','spotify','tmdb'].some((p)=>i.key.startsWith(`${p}.`)));
  return <div className="space-y-3"><h2 className="text-lg font-semibold">API Keys (Legacy)</h2><p className="text-sm text-muted-foreground">Legacy (Advanced). Prefer Integrations.</p>{legacy.map((f)=><div key={f.key} className="rounded border p-2 text-sm flex justify-between"><span>{f.label}</span><span className="text-muted-foreground">{f.configured ? 'Configured' : 'Not configured'}</span></div>)}</div>;
}
