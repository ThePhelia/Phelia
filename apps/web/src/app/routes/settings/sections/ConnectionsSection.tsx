import { useEffect, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { useServiceSettings, useUpdateProwlarrSettings, useUpdateQbittorrentSettings } from '@/app/lib/api';
import { safeString, safeTrimmedString } from '@/app/utils/safe';
import { toast } from 'sonner';

export function ConnectionsSection({ onDirtyChange }: { onDirtyChange: (d: boolean) => void }) {
  const serviceQuery = useServiceSettings();
  const updateProwlarr = useUpdateProwlarrSettings();
  const updateQb = useUpdateQbittorrentSettings();
  const [prowlarrUrl, setProwlarrUrl] = useState('');
  const [qbUrl, setQbUrl] = useState('');
  const [qbUsername, setQbUsername] = useState('');
  const [qbPassword, setQbPassword] = useState('');

  useEffect(() => {
    if (!serviceQuery.data) return;
    setProwlarrUrl(serviceQuery.data.prowlarr.url ?? '');
    setQbUrl(serviceQuery.data.qbittorrent.url ?? '');
    setQbUsername(serviceQuery.data.qbittorrent.username ?? '');
    setQbPassword('');
  }, [serviceQuery.data]);

  const prowlarrChanged = safeTrimmedString(prowlarrUrl) !== safeString(serviceQuery.data?.prowlarr.url);
  const qbChanged = safeTrimmedString(qbUrl) !== safeString(serviceQuery.data?.qbittorrent.url) || safeTrimmedString(qbUsername) !== safeString(serviceQuery.data?.qbittorrent.username) || safeTrimmedString(qbPassword).length > 0;
  const dirty = prowlarrChanged || qbChanged;
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  return <div className="space-y-4">
    <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Connections</h2>{dirty ? <span className="text-xs rounded bg-amber-100 px-2 py-1">Unsaved changes</span> : null}</div>
    <div className="rounded-lg border p-3 space-y-2">
      <Label htmlFor="connections-prowlarr-url">Prowlarr URL</Label>
      <Input id="connections-prowlarr-url" value={prowlarrUrl} onChange={(e)=>setProwlarrUrl(e.target.value)} />
      <Button onClick={async()=>{await updateProwlarr.mutateAsync({url:safeTrimmedString(prowlarrUrl)||null});toast.success('Prowlarr settings updated');}} disabled={!prowlarrChanged || updateProwlarr.isPending}>Save</Button>
    </div>
    <div className="rounded-lg border p-3 space-y-2">
      <Label htmlFor="connections-qb-url">qBittorrent URL</Label><Input id="connections-qb-url" value={qbUrl} onChange={(e)=>setQbUrl(e.target.value)} />
      <Label htmlFor="connections-qb-user">qBittorrent Username</Label><Input id="connections-qb-user" value={qbUsername} onChange={(e)=>setQbUsername(e.target.value)} />
      <Label htmlFor="connections-qb-pass">qBittorrent Password</Label><Input id="connections-qb-pass" type="password" value={qbPassword} onChange={(e)=>setQbPassword(e.target.value)} />
      <div className="flex gap-2">
        <Button onClick={async()=>{await updateQb.mutateAsync({url:safeTrimmedString(qbUrl)||null,username:safeTrimmedString(qbUsername)||null,password:safeTrimmedString(qbPassword)||undefined});toast.success('qBittorrent settings updated');setQbPassword('');}} disabled={!qbChanged || updateQb.isPending}>Save</Button>
        {(serviceQuery.data?.qbittorrent.password_configured ?? false) ? <Button variant="outline" onClick={async()=>{await updateQb.mutateAsync({password:null});toast.success('qBittorrent password cleared');setQbPassword('');}} disabled={updateQb.isPending}>Clear password</Button> : null}
      </div>
    </div>
  </div>;
}
