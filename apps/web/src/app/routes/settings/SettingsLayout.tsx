import type { ReactNode } from 'react';
import { LocalErrorBoundary } from '@/app/components/LocalErrorBoundary';
import { Button } from '@/app/components/ui/button';

export interface SettingsSectionDef { id: string; label: string; node: ReactNode; }

export function SettingsLayout({ sections, currentSection, setCurrentSection, dirtySections }: { sections: SettingsSectionDef[]; currentSection: string; setCurrentSection: (id: string) => void; dirtySections: Record<string, boolean>; }) {
  const current = sections.find((s) => s.id === currentSection) ?? sections[0];
  return <div className="grid gap-6 md:grid-cols-[220px_minmax(0,1fr)]">
    <aside className="space-y-1">
      {sections.map((section) => <Button key={section.id} variant={section.id===currentSection?'secondary':'ghost'} className="w-full justify-start" onClick={()=>setCurrentSection(section.id)}>{section.label}{dirtySections[section.id] ? <span className="ml-2 text-amber-600">●</span> : null}</Button>)}
    </aside>
    <section className="rounded-2xl border p-5">
      <LocalErrorBoundary selectorKey={`settings.${current.id}`} title="This section crashed" description="Try reloading this section.">
        {current.node}
      </LocalErrorBoundary>
    </section>
  </div>;
}
