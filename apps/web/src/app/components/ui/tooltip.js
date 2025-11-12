import { Fragment as _Fragment, jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useState } from 'react';
import { cn } from '@/app/utils/cn';
const TooltipContext = createContext(null);
function TooltipProvider({ children }) {
    return _jsx(_Fragment, { children: children });
}
function Tooltip({ children }) {
    const [open, setOpen] = useState(false);
    return (_jsx(TooltipContext.Provider, { value: { open, setOpen }, children: _jsx("span", { className: 'relative inline-flex items-center', children: children }) }));
}
function TooltipTrigger({ children }) {
    const ctx = useTooltipContext();
    return (_jsx("span", { className: "inline-flex", onMouseEnter: () => ctx.setOpen(true), onMouseLeave: () => ctx.setOpen(false), onFocus: () => ctx.setOpen(true), onBlur: () => ctx.setOpen(false), children: children }));
}
function TooltipContent({ children, className }) {
    const ctx = useTooltipContext();
    if (!ctx.open)
        return null;
    return (_jsx("span", { className: cn('absolute z-50 mt-2 whitespace-nowrap rounded-lg border border-border/60 bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-lg', className), role: "tooltip", children: children }));
}
function useTooltipContext() {
    const ctx = useContext(TooltipContext);
    if (!ctx)
        throw new Error('Tooltip components must be used within <Tooltip>');
    return ctx;
}
export { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent };
