import { createContext, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

interface DropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  triggerRef: React.RefObject<HTMLDivElement>;
}

const DropdownContext = createContext<DropdownContextValue | null>(null);

function DropdownMenu({ children }: { children: ReactNode }) {
  const triggerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  return (
    <DropdownContext.Provider value={{ open, setOpen, triggerRef }}>
      <div className="relative inline-flex" ref={triggerRef}>
        {children}
      </div>
    </DropdownContext.Provider>
  );
}

interface TriggerProps {
  asChild?: boolean;
  children: ReactNode;
}

function DropdownMenuTrigger({ children }: TriggerProps) {
  const ctx = useDropdownContext();
  return (
    <div onClick={() => ctx.setOpen(!ctx.open)} className="cursor-pointer">
      {children}
    </div>
  );
}

interface ContentProps {
  children: ReactNode;
  className?: string;
  align?: 'start' | 'end';
}

function DropdownMenuContent({ children, className, align = 'start' }: ContentProps) {
  const ctx = useDropdownContext();
  if (!ctx.open) return null;
  return (
    <div
      className={cn(
        'absolute z-50 mt-2 min-w-[12rem] rounded-xl border border-border/60 bg-popover p-1 text-popover-foreground shadow-xl',
        align === 'end' ? 'right-0' : 'left-0',
        className,
      )}
    >
      {children}
    </div>
  );
}

function DropdownMenuItem({ children, className, onSelect }: { children: ReactNode; className?: string; onSelect?: () => void }) {
  const ctx = useDropdownContext();
  return (
    <button
      type="button"
      className={cn(
        'w-full rounded-lg px-2 py-2 text-left text-sm text-foreground transition hover:bg-foreground/10',
        className,
      )}
      onClick={() => {
        onSelect?.();
        ctx.setOpen(false);
      }}
    >
      {children}
    </button>
  );
}

function DropdownMenuLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('px-2 py-1.5 text-xs font-semibold text-muted-foreground', className)}>{children}</div>;
}

function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn('my-1 h-px bg-border', className)} />;
}

function DropdownMenuCheckboxItem(props: any) {
  return <DropdownMenuItem {...props} />;
}

function DropdownMenuRadioItem(props: any) {
  return <DropdownMenuItem {...props} />;
}

function DropdownMenuShortcut({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('ml-auto text-xs tracking-widest text-muted-foreground', className)}>{children}</span>;
}

function DropdownMenuSub(props: { children: ReactNode }) {
  return <>{props.children}</>;
}

const DropdownMenuSubTrigger = DropdownMenuTrigger;
const DropdownMenuSubContent = DropdownMenuContent;
const DropdownMenuPortal = ({ children }: { children: ReactNode }) => <>{children}</>;
const DropdownMenuGroup = ({ children }: { children: ReactNode }) => <>{children}</>;
const DropdownMenuRadioGroup = ({ children }: { children: ReactNode }) => <>{children}</>;
const DropdownMenuItemIndicator = ({ children }: { children: ReactNode }) => <span>{children}</span>;

function useDropdownContext() {
  const ctx = useContext(DropdownContext);
  if (!ctx) throw new Error('Dropdown components must be used within <DropdownMenu>');
  return ctx;
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuPortal,
  DropdownMenuGroup,
  DropdownMenuRadioGroup,
  DropdownMenuItemIndicator,
};
