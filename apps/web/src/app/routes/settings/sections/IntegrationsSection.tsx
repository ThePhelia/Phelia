import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { useIntegrationSettings } from '@/app/lib/api';
import { toast } from 'sonner';
import { safeTrimmedString } from '@/app/utils/safe';
import { SECRET_MASK, parseValidationRule } from './shared';

function fieldError(field: any, value: string, initial: string) {
  const trimmed = safeTrimmedString(value);
  const isMaskedUnchanged = field.masked_at_rest && field.configured && value === initial && initial === SECRET_MASK;
  if (isMaskedUnchanged) return null;
  if (field.required && !trimmed) return `${field.label} is required.`;
  if (!trimmed) return null;
  const rule = parseValidationRule(field.validation_rule);
  if (rule.minLength && trimmed.length < rule.minLength) return `${field.label} must be at least ${rule.minLength} characters.`;
  if (rule.regex && !rule.regex.test(trimmed)) return `${field.label} format is invalid.`;
  return null;
}

export function IntegrationsSection({ onDirtyChange }: { onDirtyChange: (d: boolean) => void }) {
  const integrationsQuery = useIntegrationSettings();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'enabled' | 'missing'>('all');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [initial, setInitial] = useState<Record<string, string>>({});
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});

  const fields = integrationsQuery.data?.integrations ?? [];
  const providers = integrationsQuery.data?.providers ?? [];

  useEffect(() => {
    const next: Record<string, string> = {};
    fields.forEach((f) => next[f.key] = f.value ?? '');
    setValues(next); setInitial(next);
    const e: Record<string, boolean> = {};
    providers.forEach((p: any) => e[p.id] = Boolean(p.enabled));
    setEnabled(e);
  }, [integrationsQuery.data]);

  const providerFields = useMemo(() => fields.reduce<Record<string, any[]>>((acc, f) => {
    const provider = f.key.split('.')[0];
    acc[provider] = acc[provider] ?? [];
    acc[provider].push(f);
    return acc;
  }, {}), [fields]);

  const providerDirty = useMemo(() => Object.fromEntries(Object.entries(providerFields).map(([pid, fs]) => [pid, fs.some((f:any)=>(values[f.key] ?? '') !== (initial[f.key] ?? ''))])), [providerFields, values, initial]);
  useEffect(()=>onDirtyChange(Object.values(providerDirty).some(Boolean)),[providerDirty,onDirtyChange]);

  const visibleProviders = providers.filter((p: any) => {
    const text = `${p.name} ${p.description}`.toLowerCase();
    if (search && !text.includes(search.toLowerCase())) return false;
    if (filter === 'enabled' && !enabled[p.id]) return false;
    if (filter === 'missing' && p.configured) return false;
    return true;
  });

  const saveProvider = async (providerId: string) => {
    const fs = providerFields[providerId] ?? [];
    const valuesPayload: Record<string, string | null> = {};
    for (const field of fs) {
      const current = values[field.key] ?? '';
      if (current === (initial[field.key] ?? '')) continue;
      if (field.masked_at_rest && field.configured && current === SECRET_MASK && initial[field.key] === SECRET_MASK) continue;
      valuesPayload[field.key.split('.').slice(1).join('.')] = safeTrimmedString(current) || null;
    }
    const response = await fetch('/api/v1/settings/integrations', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ providers: { [providerId]: { enabled: enabled[providerId], values: valuesPayload } } }) });
    if (!response.ok) throw new Error('save failed');
    toast.success(`Saved ${providers.find((p:any)=>p.id===providerId)?.name ?? providerId}`);
    integrationsQuery.refetch();
  };

  return <div className="space-y-4">
    <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Integrations</h2>{Object.values(providerDirty).some(Boolean) ? <span className="text-xs rounded bg-amber-100 px-2 py-1">Unsaved changes</span> : null}</div>
    <div className="flex gap-2"><Input placeholder="Search services…" value={search} onChange={(e)=>setSearch(e.target.value)} /><Button variant={filter==='all'?'default':'outline'} onClick={()=>setFilter('all')}>All</Button><Button variant={filter==='enabled'?'default':'outline'} onClick={()=>setFilter('enabled')}>Enabled</Button><Button variant={filter==='missing'?'default':'outline'} onClick={()=>setFilter('missing')}>Not Configured</Button></div>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {visibleProviders.map((provider: any) => <div key={provider.id} className="rounded-lg border p-3 space-y-2"><div className="flex items-center justify-between"><div><div className="font-medium">{provider.name}</div><p className="text-xs text-muted-foreground">{provider.description}</p></div><Button size="sm" variant="outline" onClick={()=>setEnabled((p)=>({...p,[provider.id]:!p[provider.id]}))}>{enabled[provider.id] ? 'Disable' : 'Enable'}</Button></div>
        <div className="flex gap-1 text-xs"><span className="rounded border px-2 py-0.5">{enabled[provider.id] ? 'Enabled':'Disabled'}</span><span className="rounded border px-2 py-0.5">{provider.configured ? 'Configured':'Missing'}</span>{providerDirty[provider.id] ? <span className="rounded border px-2 py-0.5">Unsaved</span>:null}</div>
        <Button size="sm" onClick={()=>setExpanded(expanded===provider.id?null:provider.id)}>Configure</Button>
        {expanded===provider.id && enabled[provider.id] ? <div className="space-y-2 border-t pt-2">{(providerFields[provider.id] ?? []).map((field:any)=>{const error=fieldError(field, values[field.key] ?? '', initial[field.key] ?? ''); const isSecret=field.masked_at_rest; return <div key={field.key} className="space-y-1"><Label htmlFor={`integration-${field.key}`}>{field.label}</Label><div className="flex gap-2"><Input id={`integration-${field.key}`} type={isSecret && !revealed[field.key] ? 'password' : 'text'} value={values[field.key] ?? ''} placeholder={field.configured ? SECRET_MASK : ''} onChange={(e)=>setValues((p)=>({...p,[field.key]:e.target.value}))} /><Button size="sm" variant="outline" onClick={()=>setValues((p)=>({...p,[field.key]:''}))}>Clear field</Button>{isSecret ? <Button size="sm" variant="outline" onClick={()=>setRevealed((p)=>({...p,[field.key]:!p[field.key]}))}>{revealed[field.key] ? 'Hide' : 'Reveal'}</Button> : null}</div>{error ? <p className="text-xs text-destructive">{error}</p> : null}</div>;})}
          <Button onClick={()=>saveProvider(provider.id)} disabled={(providerFields[provider.id] ?? []).some((f:any)=>{const cur=values[f.key] ?? ''; const init=initial[f.key] ?? ''; return cur!==init && Boolean(fieldError(f, cur, init));}) || !providerDirty[provider.id]}>Save</Button></div> : null}
      </div>)}
    </div>
  </div>;
}
