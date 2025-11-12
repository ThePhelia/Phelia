import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from '@/app/utils/cn';
function Separator({ className, orientation = 'horizontal' }) {
    return (_jsx("div", { className: cn('shrink-0 bg-border', orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px', className) }));
}
export { Separator };
