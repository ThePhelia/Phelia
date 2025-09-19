import { Loader2 } from 'lucide-react';

function LoadingView() {
  return (
    <div className="flex h-screen items-center justify-center bg-background/80">
      <div className="flex items-center gap-3 rounded-full bg-card/40 px-6 py-4 shadow-glow">
        <Loader2 className="h-6 w-6 animate-spin text-accent" />
        <span className="text-lg font-medium text-foreground">Loading Phelia…</span>
      </div>
    </div>
  );
}

export default LoadingView;
