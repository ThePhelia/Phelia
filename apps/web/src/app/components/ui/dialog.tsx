import { createContext, useContext, useEffect } from 'react';
import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

interface DialogContextValue {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | null>(null);

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  return <DialogContext.Provider value={{ open, onOpenChange }}>{children}</DialogContext.Provider>;
}

function DialogTrigger({ children }: { children: ReactNode }) {
  const ctx = useDialogContext();
  return (
    <button type="button" onClick={() => ctx.onOpenChange(!ctx.open)}>
      {children}
    </button>
  );
}

interface DialogContentProps {
  className?: string;
  children: ReactNode;
}

function DialogContent({ className, children }: DialogContentProps) {
  const ctx = useDialogContext();
  useEffect(() => {
    if (ctx.open) {
      const previous = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = previous;
      };
    }
    return undefined;
  }, [ctx.open]);

  if (!ctx.open) return null;

  const container = document.getElementById('dialog-root') ?? document.body;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur">
      <div className={cn('max-h-[95vh] w-full max-w-6xl overflow-hidden rounded-3xl bg-background shadow-2xl', className)}>
        {children}
      </div>
    </div>,
    container,
  );
}

function DialogClose({ children, className }: { children: ReactNode; className?: string }) {
  const ctx = useDialogContext();
  return (
    <button type="button" onClick={() => ctx.onOpenChange(false)} className={className}>
      {children}
    </button>
  );
}

function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1.5 px-8 pb-6 pt-8 text-left', className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex justify-end gap-2 px-8 pb-8', className)} {...props} />;
}

function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-2xl font-semibold leading-none', className)} {...props} />;
}

function DialogDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />;
}

function useDialogContext() {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error('Dialog components must be used within <Dialog>');
  return ctx;
}

export { Dialog, DialogTrigger, DialogContent, DialogClose, DialogHeader, DialogFooter, DialogTitle, DialogDescription };
