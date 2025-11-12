import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useMemo, useState } from 'react';
import { cn } from '@/app/utils/cn';
const TabsContext = createContext(null);
function Tabs({ defaultValue, value: valueProp, onValueChange, children, className }) {
    const [valueState, setValueState] = useState(defaultValue ?? valueProp ?? '');
    const value = valueProp ?? valueState;
    const context = useMemo(() => ({
        value,
        setValue: (next) => {
            setValueState(next);
            onValueChange?.(next);
        },
    }), [onValueChange, value]);
    return _jsx(TabsContext.Provider, { value: context, children: _jsx("div", { className: className, children: children }) });
}
function TabsList({ className, ...props }) {
    return _jsx("div", { className: cn('inline-flex h-11 items-center justify-center rounded-full bg-foreground/5 p-1 text-muted-foreground', className), ...props });
}
function TabsTrigger({ value, className, children, ...props }) {
    const ctx = useTabsContext();
    const active = ctx.value === value;
    return (_jsx("button", { type: "button", className: cn('inline-flex min-w-[120px] items-center justify-center whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background', active ? 'bg-background text-foreground shadow-sm' : 'opacity-70 hover:opacity-100', className), onClick: () => ctx.setValue(value), ...props, children: children }));
}
function TabsContent({ value, className, children, ...props }) {
    const ctx = useTabsContext();
    if (ctx.value !== value)
        return null;
    return (_jsx("div", { className: cn('mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2', className), ...props, children: children }));
}
function useTabsContext() {
    const ctx = useContext(TabsContext);
    if (!ctx)
        throw new Error('Tabs components must be used within <Tabs>');
    return ctx;
}
export { Tabs, TabsList, TabsTrigger, TabsContent };
