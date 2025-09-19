import { createContext, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface TabsProps {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}

function Tabs({ defaultValue, value: valueProp, onValueChange, children, className }: TabsProps) {
  const [valueState, setValueState] = useState(defaultValue);
  const value = valueProp ?? valueState;

  const context = useMemo<TabsContextValue>(
    () => ({
      value,
      setValue: (next) => {
        setValueState(next);
        onValueChange?.(next);
      },
    }),
    [onValueChange, value],
  );

  return <TabsContext.Provider value={context}><div className={className}>{children}</div></TabsContext.Provider>;
}

function TabsList({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('inline-flex h-11 items-center justify-center rounded-full bg-foreground/5 p-1 text-muted-foreground', className)} {...props} />;
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

function TabsTrigger({ value, className, children, ...props }: TabsTriggerProps) {
  const ctx = useTabsContext();
  const active = ctx.value === value;
  return (
    <button
      type="button"
      className={cn(
        'inline-flex min-w-[120px] items-center justify-center whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        active ? 'bg-background text-foreground shadow-sm' : 'opacity-70 hover:opacity-100',
        className,
      )}
      onClick={() => ctx.setValue(value)}
      {...props}
    >
      {children}
    </button>
  );
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

function TabsContent({ value, className, children, ...props }: TabsContentProps) {
  const ctx = useTabsContext();
  if (ctx.value !== value) return null;
  return (
    <div
      className={cn(
        'mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('Tabs components must be used within <Tabs>');
  return ctx;
}

export { Tabs, TabsList, TabsTrigger, TabsContent };
