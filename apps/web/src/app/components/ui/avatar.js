import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function Avatar({ className, children }) {
    return _jsx("div", { className: cn('relative flex h-9 w-9 shrink-0 overflow-hidden rounded-full bg-muted', className), children: children });
}
function AvatarImage({ className, ...props }) {
    return _jsx("img", { className: cn('h-full w-full object-cover', className), ...props });
}
function AvatarFallback({ className, children }) {
    return _jsx("div", { className: cn('flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground', className), children: children });
}
export { Avatar, AvatarImage, AvatarFallback };
