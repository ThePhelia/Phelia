import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createContext, useContext, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/app/utils/cn';
const SheetContext = createContext(null);
function Sheet({ open, onOpenChange, children, side = 'right' }) {
    return _jsx(SheetContext.Provider, { value: { open, onOpenChange, side }, children: children });
}
function SheetTrigger({ children }) {
    const ctx = useSheetContext();
    return (_jsx("button", { type: "button", onClick: () => ctx.onOpenChange(!ctx.open), children: children }));
}
function SheetContent({ children, className, side }) {
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
    useEffect(() => {
        if (!isOpen)
            return undefined;
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                ctx.onOpenChange(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [ctx.onOpenChange, isOpen]);
    if (!isOpen)
        return null;
    const container = document.getElementById('dialog-root') ?? document.body;
    const positionClasses = {
        right: 'right-0 top-0 h-full w-full max-w-xl translate-x-0',
        left: 'left-0 top-0 h-full w-full max-w-xl translate-x-0',
        bottom: 'bottom-0 left-0 w-full max-h-[80vh] translate-y-0',
    };
    return createPortal(_jsxs("div", { className: "fixed inset-0 z-50 flex", children: [_jsx("div", { className: "absolute inset-0 bg-black/70", onClick: () => ctx.onOpenChange(false) }), _jsx("div", { className: cn('relative ml-auto flex flex-col bg-background/95 p-6 shadow-2xl backdrop-blur-xl', positionClasses[sheetSide], className), children: children })] }), container);
}
function SheetClose({ children }) {
    const ctx = useSheetContext();
    return (_jsx("button", { type: "button", onClick: () => ctx.onOpenChange(false), children: children }));
}
function SheetHeader({ className, ...props }) {
    return _jsx("div", { className: cn('flex flex-col space-y-1 text-left', className), ...props });
}
function SheetTitle({ className, ...props }) {
    return _jsx("h2", { className: cn('text-xl font-semibold text-foreground', className), ...props });
}
function SheetDescription({ className, ...props }) {
    return _jsx("p", { className: cn('text-sm text-muted-foreground', className), ...props });
}
function useSheetContext() {
    const ctx = useContext(SheetContext);
    if (!ctx)
        throw new Error('Sheet components must be used within <Sheet>');
    return ctx;
}
export { Sheet, SheetTrigger, SheetContent, SheetClose, SheetHeader, SheetTitle, SheetDescription };
