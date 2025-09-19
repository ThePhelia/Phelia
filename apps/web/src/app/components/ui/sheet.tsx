import { createContext, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/app/utils/cn';

interface SheetContextValue {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side: 'left' | 'right' | 'bottom';
}

const SheetContext = createContext<SheetContextValue | null>(null);

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  side?: 'left' | 'right' | 'bottom';
}

function Sheet({ open, onOpenChange, children, side = 'right' }: SheetProps) {
  return <SheetContext.Provider value={{ open, onOpenChange, side }}>{children}</SheetContext.Provider>;
}

function SheetTrigger({ children }: { children: ReactNode }) {
  const ctx = useSheetContext();
  return (
    <button type="button" onClick={() => ctx.onOpenChange(!ctx.open)}>
      {children}
    </button>
  );
}

interface SheetContentProps {
  children: ReactNode;
  className?: string;
  side?: 'left' | 'right' | 'bottom';
}

function SheetContent({ children, className, side }: SheetContentProps) {
  const ctx = useSheetContext();
  const isOpen = ctx.open;
  const sheetSide = side ?? ctx.side;

  useEffect(() => {
    if (isOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
    return undefined;
  }, [isOpen]);

  if (!isOpen) return null;

  const container = document.getElementById('dialog-root') ?? document.body;
  const positionClasses = {
    right: 'right-0 top-0 h-full w-full max-w-xl translate-x-0',
    left: 'left-0 top-0 h-full w-full max-w-xl translate-x-0',
    bottom: 'bottom-0 left-0 w-full max-h-[80vh] translate-y-0',
  } as const;

  return createPortal(
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black/70" onClick={() => ctx.onOpenChange(false)} />
      <div className={cn('relative ml-auto flex flex-col bg-background/95 p-6 shadow-2xl backdrop-blur-xl', positionClasses[sheetSide], className)}>
        {children}
      </div>
    </div>,
    container,
  );
}

function SheetClose({ children }: { children: ReactNode }) {
  const ctx = useSheetContext();
  return (
    <button type="button" onClick={() => ctx.onOpenChange(false)}>
      {children}
    </button>
  );
}

function SheetHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1 text-left', className)} {...props} />;
}

function SheetTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-xl font-semibold text-foreground', className)} {...props} />;
}

function SheetDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />;
}

function useSheetContext() {
  const ctx = useContext(SheetContext);
  if (!ctx) throw new Error('Sheet components must be used within <Sheet>');
  return ctx;
}

export { Sheet, SheetTrigger, SheetContent, SheetClose, SheetHeader, SheetTitle, SheetDescription };
