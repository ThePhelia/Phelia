import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SettingsLayout } from './SettingsLayout';
import { AppearanceSection } from './sections/AppearanceSection';
import { DownloadsSection } from './sections/DownloadsSection';
import { ConnectionsSection } from './sections/ConnectionsSection';
import { ProwlarrSection } from './sections/ProwlarrSection';
import { IndexersSection } from './sections/IndexersSection';
import { IntegrationsSection } from './sections/IntegrationsSection';
import { LegacyApiKeysSection } from './sections/LegacyApiKeysSection';

const IDS = ['appearance','downloads','connections','prowlarr','indexers','integrations','api-keys-legacy'] as const;

export default function SettingsPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get('section') || 'appearance';
  const currentSection = IDS.includes(raw as any) ? raw : 'appearance';
  const [dirtySections, setDirtySections] = useState<Record<string, boolean>>({});
  const setDirty = (id: string, dirty: boolean) => setDirtySections((p) => ({ ...p, [id]: dirty }));

  const sections = useMemo(() => [
    { id: 'appearance', label: 'Appearance', node: <AppearanceSection /> },
    { id: 'downloads', label: 'Downloads', node: <DownloadsSection onDirtyChange={(d)=>setDirty('downloads',d)} /> },
    { id: 'connections', label: 'Connections', node: <ConnectionsSection onDirtyChange={(d)=>setDirty('connections',d)} /> },
    { id: 'prowlarr', label: 'Prowlarr', node: <ProwlarrSection onDirtyChange={(d)=>setDirty('prowlarr',d)} /> },
    { id: 'indexers', label: 'Indexers', node: <IndexersSection /> },
    { id: 'integrations', label: 'Integrations', node: <IntegrationsSection onDirtyChange={(d)=>setDirty('integrations',d)} /> },
    { id: 'api-keys-legacy', label: 'API Keys (Legacy)', node: <LegacyApiKeysSection /> },
  ], []);

  const changeSection = (next: string) => {
    if (next === currentSection) return;
    if (dirtySections[currentSection]) {
      const currentLabel = sections.find((s) => s.id === currentSection)?.label ?? currentSection;
      const ok = window.confirm(`Discard changes?\nYou have unsaved changes in ${currentLabel}. Discard them?`);
      if (!ok) return;
    }
    params.set('section', next);
    setParams(params, { replace: true });
  };

  return <div className="space-y-6"><h1 className="text-2xl font-semibold">Settings</h1><SettingsLayout sections={sections} currentSection={currentSection} setCurrentSection={changeSection} dirtySections={dirtySections} /></div>;
}
