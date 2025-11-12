import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createContext, useContext, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/app/utils/cn';
const DialogContext = createContext(null);
function Dialog({ open, onOpenChange, children }) {
    return _jsx(DialogContext.Provider, { value: { open, onOpenChange }, children: children });
}
function DialogTrigger({ children }) {
    const ctx = useDialogContext();
    return (_jsx("button", { type: "button", onClick: () => ctx.onOpenChange(!ctx.open), children: children }));
}
function DialogContent({ className, children }) {
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
    useEffect(() => {
        if (!ctx.open)
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
    }, [ctx.onOpenChange, ctx.open]);
    if (!ctx.open)
        return null;
    const container = document.getElementById('dialog-root') ?? document.body;
    return createPortal(_jsxs("div", { className: "fixed inset-0 z-50 flex items-center justify-center", children: [_jsx("button", { type: "button", "aria-label": "Close dialog", className: "absolute inset-0 bg-black/70 backdrop-blur", onClick: () => ctx.onOpenChange(false) }), _jsx("div", { className: cn('relative z-10 max-h-[95vh] w-full max-w-6xl overflow-hidden rounded-3xl bg-background shadow-2xl', className), children: children })] }), container);
}
function DialogClose({ children, className }) {
    const ctx = useDialogContext();
    return (_jsx("button", { type: "button", onClick: () => ctx.onOpenChange(false), className: className, children: children }));
}
function DialogHeader({ className, ...props }) {
    return _jsx("div", { className: cn('flex flex-col space-y-1.5 px-8 pb-6 pt-8 text-left', className), ...props });
}
function DialogFooter({ className, ...props }) {
    return _jsx("div", { className: cn('flex justify-end gap-2 px-8 pb-8', className), ...props });
}
function DialogTitle({ className, ...props }) {
    return _jsx("h2", { className: cn('text-2xl font-semibold leading-none', className), ...props });
}
function DialogDescription({ className, ...props }) {
    return _jsx("p", { className: cn('text-sm text-muted-foreground', className), ...props });
}
function useDialogContext() {
    const ctx = useContext(DialogContext);
    if (!ctx)
        throw new Error('Dialog components must be used within <Dialog>');
    return ctx;
}
export { Dialog, DialogTrigger, DialogContent, DialogClose, DialogHeader, DialogFooter, DialogTitle, DialogDescription };
