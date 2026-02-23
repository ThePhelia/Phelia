import { useEffect, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { useServiceSettings, useUpdateDownloadSettings } from '@/app/lib/api';
import { normalizeStringList, safeString, safeTrimmedString } from '@/app/utils/safe';
import { toast } from 'sonner';

const parseDirList = (value: string) => value.split(/[\n,]/).map((i) => i.trim()).filter(Boolean);
const equal = (a: string[], b: string[]) => a.length === b.length && a.every((v, i) => v === b[i]);

export function DownloadsSection({ onDirtyChange }: { onDirtyChange: (d: boolean) => void }) {
  const serviceQuery = useServiceSettings();
  const updateDownloads = useUpdateDownloadSettings();
  const [allowedDirs, setAllowedDirs] = useState('');
  const [defaultDir, setDefaultDir] = useState('');

  useEffect(() => {
    if (!serviceQuery.data) return;
    setAllowedDirs(normalizeStringList(serviceQuery.data.downloads.allowed_dirs).join(', '));
    setDefaultDir(serviceQuery.data.downloads.default_dir ?? '');
  }, [serviceQuery.data]);

  const persistedAllowed = normalizeStringList(serviceQuery.data?.downloads.allowed_dirs ?? []);
  const parsedAllowed = parseDirList(allowedDirs);
  const trimmedDefault = safeTrimmedString(defaultDir);
  const dirty = !equal(parsedAllowed, persistedAllowed) || trimmedDefault !== safeString(serviceQuery.data?.downloads.default_dir);
  const valid = Boolean(trimmedDefault);

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const save = async () => {
    await updateDownloads.mutateAsync({ allowed_dirs: parsedAllowed, default_dir: trimmedDefault || null });
    toast.success('Downloads settings updated');
  };

  return <div className="space-y-3">
    <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Downloads</h2>{dirty ? <span className="text-xs rounded bg-amber-100 px-2 py-1">Unsaved changes</span> : null}</div>
    <div className="space-y-2"><Label htmlFor="downloads-default">Default download path</Label><Input id="downloads-default" value={defaultDir} onChange={(e)=>setDefaultDir(e.target.value)} /></div>
    <div className="space-y-2"><Label htmlFor="downloads-allowed">Allowed paths</Label><Input id="downloads-allowed" value={allowedDirs} onChange={(e)=>setAllowedDirs(e.target.value)} /><p className="text-xs text-muted-foreground">Use commas or new lines to separate paths.</p></div>
    <Button onClick={save} disabled={!dirty || !valid || updateDownloads.isPending}>Save</Button>
  </div>;
}
