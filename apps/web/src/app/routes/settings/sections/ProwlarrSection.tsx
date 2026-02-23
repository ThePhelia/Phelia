import { useEffect, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { useDiscoverProwlarrApiKey, useServiceSettings, useUpdateProwlarrSettings } from '@/app/lib/api';
import { toast } from 'sonner';
import { safeTrimmedString } from '@/app/utils/safe';

export function ProwlarrSection({ onDirtyChange }: { onDirtyChange: (d: boolean) => void }) {
  const serviceQuery = useServiceSettings();
  const updateProwlarr = useUpdateProwlarrSettings();
  const discover = useDiscoverProwlarrApiKey();
  const [manualKey, setManualKey] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  useEffect(()=>onDirtyChange(Boolean(safeTrimmedString(manualKey))),[manualKey,onDirtyChange]);
  const url = serviceQuery.data?.prowlarr.url ?? '';
  return <div className="space-y-4">
    <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Prowlarr</h2>{safeTrimmedString(manualKey) ? <span className="text-xs rounded bg-amber-100 px-2 py-1">Unsaved changes</span> : null}</div>
    <div className="rounded-lg border p-3 space-y-2">
      <Label>Prowlarr API Key</Label>
      <Input value={manualKey} onChange={(e)=>setManualKey(e.target.value)} placeholder="Paste API key" />
      <p className="text-xs text-muted-foreground">Used to manage indexers via Prowlarr API.</p>
      <div className="flex gap-2">
        <Button onClick={async()=>{await updateProwlarr.mutateAsync({api_key:safeTrimmedString(manualKey)||null});toast.success('Prowlarr key saved');setManualKey('');}} disabled={!safeTrimmedString(manualKey)}>Save key</Button>
        <Button variant="outline" onClick={async()=>{await updateProwlarr.mutateAsync({api_key:null});toast.success('Prowlarr key cleared');setManualKey('');}}>Clear key</Button>
        <Button variant="outline" onClick={()=>window.open(url,'_blank','noopener,noreferrer')} disabled={!url}>Open Prowlarr</Button>
      </div>
    </div>
    <div className="rounded-lg border p-3 space-y-2">
      <Label>Username (optional)</Label><Input value={username} onChange={(e)=>setUsername(e.target.value)} />
      <Label>Password (optional)</Label><Input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} />
      <Button onClick={async()=>{const auth=safeTrimmedString(username)?{username:safeTrimmedString(username),password}:null;const res=await discover.mutateAsync({force_refresh:false,auth});toast.success(res.message);}}>Fetch API key</Button>
    </div>
  </div>;
}
