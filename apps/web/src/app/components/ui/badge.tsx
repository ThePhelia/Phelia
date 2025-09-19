import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes } from 'react';
import { cn } from '@/app/utils/cn';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border border-transparent px-2.5 py-1 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-foreground/10 text-foreground',
        accent: 'bg-[color:var(--accent)]/15 text-[color:var(--accent)]',
        outline: 'border-border text-muted-foreground',
        success: 'bg-emerald-500/20 text-emerald-300',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
