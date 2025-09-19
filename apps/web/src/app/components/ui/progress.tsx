import type { HTMLAttributes } from 'react';
import { cn } from '@/app/utils/cn';

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value?: number;
}

function Progress({ value = 0, className, ...props }: ProgressProps) {
  return (
    <div className={cn('relative h-2 w-full overflow-hidden rounded-full bg-foreground/10', className)} {...props}>
      <div className="h-full bg-[color:var(--accent)] transition-all" style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
    </div>
  );
}

export { Progress };
