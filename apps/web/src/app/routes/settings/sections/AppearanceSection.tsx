import { Label } from '@/app/components/ui/label';
import { Switch } from '@/app/components/ui/switch';
import { useTheme } from '@/app/components/ThemeProvider';

export function AppearanceSection() {
  const { mode, setMode } = useTheme();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Label htmlFor="theme-toggle" className="text-foreground">Dark mode</Label>
          <p className="text-sm text-muted-foreground">Toggle between light and dark themes.</p>
        </div>
        <Switch id="theme-toggle" checked={mode !== 'light'} onCheckedChange={(c) => setMode(c ? 'dark' : 'light')} />
      </div>
    </div>
  );
}
