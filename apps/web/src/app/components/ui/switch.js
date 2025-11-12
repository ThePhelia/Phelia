import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function Switch({ className, checked, onCheckedChange, ...props }) {
    return (_jsxs("label", { className: cn('relative inline-flex h-6 w-11 cursor-pointer items-center', className), children: [_jsx("input", { type: "checkbox", className: "peer sr-only", checked: checked, onChange: (event) => onCheckedChange?.(event.target.checked), ...props }), _jsx("span", { className: "absolute inset-0 rounded-full bg-muted transition peer-checked:bg-[color:var(--accent)]/80" }), _jsx("span", { className: "absolute left-1 top-1 h-4 w-4 rounded-full bg-background shadow transition peer-checked:translate-x-5" })] }));
}
export { Switch };
