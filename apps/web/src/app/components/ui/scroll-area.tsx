import type { ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

function ScrollArea({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('overflow-auto', className)}>{children}</div>;
}

function ScrollBar() {
  return null;
}

export { ScrollArea, ScrollBar };
