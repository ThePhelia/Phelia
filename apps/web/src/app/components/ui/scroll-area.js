import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function ScrollArea({ children, className }) {
    return _jsx("div", { className: cn('overflow-auto', className), children: children });
}
function ScrollBar() {
    return null;
}
export { ScrollArea, ScrollBar };
