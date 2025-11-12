import { jsx as _jsx } from "react/jsx-runtime";
import * as React from 'react';
import { cva } from 'class-variance-authority';
import { cn } from '@/app/utils/cn';
const buttonVariants = cva('inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ring-offset-background', {
    variants: {
        variant: {
            default: 'bg-primary text-primary-foreground shadow hover:bg-primary/90',
            secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
            ghost: 'hover:bg-foreground/10 text-foreground',
            outline: 'border border-border bg-transparent hover:bg-foreground/10',
            accent: 'bg-[color:var(--accent)] text-black hover:bg-[color:var(--accent)]/90',
            destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
            subtle: 'bg-card text-foreground hover:bg-card/80 shadow-sm',
        },
        size: {
            default: 'h-10 px-4 py-2',
            sm: 'h-9 rounded-md px-3',
            lg: 'h-11 rounded-md px-8 text-base',
            icon: 'h-10 w-10',
        },
    },
    defaultVariants: {
        variant: 'default',
        size: 'default',
    },
});
const Button = React.forwardRef(({ className, variant, size, asChild = false, children, ...props }, ref) => {
    if (asChild && React.isValidElement(children)) {
        return React.cloneElement(children, {
            className: cn(buttonVariants({ variant, size, className }), children.props.className),
            ref,
            ...props,
        });
    }
    return (_jsx("button", { className: cn(buttonVariants({ variant, size, className })), ref: ref, ...props, children: children }));
});
Button.displayName = 'Button';
export { Button, buttonVariants };
