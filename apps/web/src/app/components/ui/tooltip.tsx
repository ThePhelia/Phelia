import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

interface TooltipContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const TooltipContext = createContext<TooltipContextValue | null>(null);

function TooltipProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

function Tooltip({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      <span className='relative inline-flex items-center'>{children}</span>
    </TooltipContext.Provider>
  );
}

interface TooltipTriggerProps {
  asChild?: boolean;
  children: ReactNode;
}

function TooltipTrigger({ children }: TooltipTriggerProps) {
  const ctx = useTooltipContext();
  return (
    <span
      className="inline-flex"
      onMouseEnter={() => ctx.setOpen(true)}
      onMouseLeave={() => ctx.setOpen(false)}
      onFocus={() => ctx.setOpen(true)}
      onBlur={() => ctx.setOpen(false)}
    >
      {children}
    </span>
  );
}

interface TooltipContentProps {
  children: ReactNode;
  className?: string;
  sideOffset?: number;
}

function TooltipContent({ children, className }: TooltipContentProps) {
  const ctx = useTooltipContext();
  if (!ctx.open) return null;
  return (
    <span
      className={cn(
        'absolute z-50 mt-2 whitespace-nowrap rounded-lg border border-border/60 bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-lg',
        className,
      )}
      role="tooltip"
    >
      {children}
    </span>
  );
}

function useTooltipContext() {
  const ctx = useContext(TooltipContext);
  if (!ctx) throw new Error('Tooltip components must be used within <Tooltip>');
  return ctx;
}

export { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent };
