import { cn } from '@/app/utils/cn';

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-shimmer rounded-md bg-foreground/10 bg-[length:400px_100%]', className)} />;
}

export { Skeleton };
