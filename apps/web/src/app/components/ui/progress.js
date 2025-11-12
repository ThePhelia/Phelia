import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function Progress({ value = 0, className, ...props }) {
    return (_jsx("div", { className: cn('relative h-2 w-full overflow-hidden rounded-full bg-foreground/10', className), ...props, children: _jsx("div", { className: "h-full bg-[color:var(--accent)] transition-all", style: { width: `${Math.min(Math.max(value, 0), 100)}%` } }) }));
}
export { Progress };
