import { jsx as _jsx } from "react/jsx-runtime";
import * as React from 'react';
import { cn } from '@/app/utils/cn';
const Label = React.forwardRef(({ className, ...props }, ref) => (_jsx("label", { ref: ref, className: cn('text-sm font-medium leading-none text-muted-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70', className), ...props })));
Label.displayName = 'Label';
export { Label };
