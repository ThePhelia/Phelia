import { useMemo, useState } from 'react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { useCreateProwlarrIndexer, useDeleteProwlarrIndexer, useProwlarrIndexerTemplates, useProwlarrIndexers, useTestProwlarrIndexer, useUpdateProwlarrIndexer } from '@/app/lib/api';
import type { ProwlarrIndexer, ProwlarrIndexerTemplate } from '@/app/lib/types';
import { toast } from 'sonner';
import { getErrorMessage } from './shared';

export function IndexersSection() {
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
  const selectedTemplate = useMemo(() => templates.find((t) => t.id === selectedTemplateId) ?? null, [templates, selectedTemplateId]);

  if (indexersQuery.isPending || templatesQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Loading indexers…</p>;
  }

  if (indexersQuery.isError || templatesQuery.isError) {
    const error = indexersQuery.error ?? templatesQuery.error;
    return <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <p className="font-medium">Failed to load indexers.</p>
      <p className="text-muted-foreground">{getErrorMessage(error)}</p>
      <Button className="mt-2" variant="outline" onClick={() => { void indexersQuery.refetch(); void templatesQuery.refetch(); }}>Retry</Button>
    </div>;
  }

  const loadTemplateDefaults = (template: ProwlarrIndexerTemplate | null) => {
    const defaults: Record<string, string> = {};
    template?.fields.forEach((field) => defaults[field.name] = field.value == null ? '' : String(field.value));
    setNewSettings(defaults);
  };
  const startEdit = (indexer: ProwlarrIndexer) => {
    setEditingId(indexer.id); setEditName(indexer.name);
    const next: Record<string, string> = {};
    indexer.fields.forEach((field) => next[field.name] = field.value == null ? '' : String(field.value));
    setEditSettings(next);
  };

  return <div className="space-y-3"><h2 className="text-lg font-semibold">Indexers</h2>
    <div className="rounded-lg border p-3 space-y-2">
      <Label>Add indexer from template</Label>
      <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={selectedTemplateId ?? ''} onChange={(e)=>{const value=e.target.value?Number(e.target.value):null; setSelectedTemplateId(value); const t=templates.find((i)=>i.id===value) ?? null; loadTemplateDefaults(t); setNewName(t?.name ?? '');}}>
        <option value="">Choose template</option>
        {templates.map((template)=><option key={template.id} value={template.id}>{template.name}</option>)}
      </select>
      {selectedTemplate ? <div className="space-y-2"><Input placeholder="Indexer name" value={newName} onChange={(e)=>setNewName(e.target.value)} />
      {selectedTemplate.fields.slice(0,8).map((field)=><div key={field.name} className="space-y-1"><Label>{field.label}</Label><Input value={newSettings[field.name] ?? ''} onChange={(e)=>setNewSettings((p)=>({...p,[field.name]:e.target.value}))} /></div>)}
      <Button onClick={async()=>{try{await createIndexer.mutateAsync({template_id:selectedTemplate.id,name:newName.trim()||selectedTemplate.name,settings:newSettings}); toast.success('Indexer added');}catch(error){toast.error(getErrorMessage(error));}}}>Add Indexer</Button></div> : null}
    </div>
    {indexers.map((indexer)=><div key={indexer.id} className="rounded-lg border p-3 space-y-2"><div className="flex justify-between"><div>{indexer.name}</div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={async()=>{try{await testIndexer.mutateAsync({id:indexer.id});toast.success(`Indexer "${indexer.name}" test sent`);}catch(error){toast.error(getErrorMessage(error));}}}>Test</Button><Button size="sm" variant="outline" onClick={()=>startEdit(indexer)}>Edit</Button><Button size="sm" variant="outline" onClick={async()=>{if(!window.confirm(`Delete indexer \"${indexer.name}\"? This cannot be undone.`)) return; try{await deleteIndexer.mutateAsync({id:indexer.id});toast.success('Indexer deleted');}catch(error){toast.error(getErrorMessage(error));}}}>Delete</Button></div></div>
    {editingId===indexer.id ? <div className="space-y-2"><Input value={editName} onChange={(e)=>setEditName(e.target.value)} />
    {indexer.fields.slice(0,8).map((field)=><div key={field.name} className="space-y-1"><Label>{field.label}</Label><Input value={editSettings[field.name] ?? ''} onChange={(e)=>setEditSettings((p)=>({...p,[field.name]:e.target.value}))} /></div>)}
    <Button onClick={async()=>{try{await updateIndexer.mutateAsync({id:indexer.id,name:editName.trim(),settings:editSettings});toast.success('Indexer updated');}catch(error){toast.error(getErrorMessage(error));}}}>Save</Button></div> : null}
    </div>)}
  </div>;
}
