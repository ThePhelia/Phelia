import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function Skeleton({ className }) {
    return _jsx("div", { className: cn('animate-shimmer rounded-md bg-foreground/10 bg-[length:400px_100%]', className) });
}
export { Skeleton };
