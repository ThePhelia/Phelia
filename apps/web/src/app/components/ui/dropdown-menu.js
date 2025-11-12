import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { createContext, useContext, useRef, useState } from 'react';
import { cn } from '@/app/utils/cn';
const DropdownContext = createContext(null);
function DropdownMenu({ children }) {
    const triggerRef = useRef(null);
    const [open, setOpen] = useState(false);
    return (_jsx(DropdownContext.Provider, { value: { open, setOpen, triggerRef }, children: _jsx("div", { className: "relative inline-flex", ref: triggerRef, children: children }) }));
}
function DropdownMenuTrigger({ children }) {
    const ctx = useDropdownContext();
    return (_jsx("div", { onClick: () => ctx.setOpen(!ctx.open), className: "cursor-pointer", children: children }));
}
function DropdownMenuContent({ children, className, align = 'start' }) {
    const ctx = useDropdownContext();
    if (!ctx.open)
        return null;
    return (_jsx("div", { className: cn('absolute z-50 mt-2 min-w-[12rem] rounded-xl border border-border/60 bg-popover p-1 text-popover-foreground shadow-xl', align === 'end' ? 'right-0' : 'left-0', className), children: children }));
}
function DropdownMenuItem({ children, className, onSelect }) {
    const ctx = useDropdownContext();
    return (_jsx("button", { type: "button", className: cn('w-full rounded-lg px-2 py-2 text-left text-sm text-foreground transition hover:bg-foreground/10', className), onClick: () => {
            onSelect?.();
            ctx.setOpen(false);
        }, children: children }));
}
function DropdownMenuLabel({ children, className }) {
    return _jsx("div", { className: cn('px-2 py-1.5 text-xs font-semibold text-muted-foreground', className), children: children });
}
function DropdownMenuSeparator({ className }) {
    return _jsx("div", { className: cn('my-1 h-px bg-border', className) });
}
function DropdownMenuCheckboxItem(props) {
    return _jsx(DropdownMenuItem, { ...props });
}
function DropdownMenuRadioItem(props) {
    return _jsx(DropdownMenuItem, { ...props });
}
function DropdownMenuShortcut({ children, className }) {
    return _jsx("span", { className: cn('ml-auto text-xs tracking-widest text-muted-foreground', className), children: children });
}
function DropdownMenuSub(props) {
    return _jsx(_Fragment, { children: props.children });
}
const DropdownMenuSubTrigger = DropdownMenuTrigger;
const DropdownMenuSubContent = DropdownMenuContent;
const DropdownMenuPortal = ({ children }) => _jsx(_Fragment, { children: children });
const DropdownMenuGroup = ({ children }) => _jsx(_Fragment, { children: children });
const DropdownMenuRadioGroup = ({ children }) => _jsx(_Fragment, { children: children });
const DropdownMenuItemIndicator = ({ children }) => _jsx("span", { children: children });
function useDropdownContext() {
    const ctx = useContext(DropdownContext);
    if (!ctx)
        throw new Error('Dropdown components must be used within <DropdownMenu>');
    return ctx;
}
export { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuCheckboxItem, DropdownMenuRadioItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent, DropdownMenuPortal, DropdownMenuGroup, DropdownMenuRadioGroup, DropdownMenuItemIndicator, };
