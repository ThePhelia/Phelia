import type { ImgHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/app/utils/cn';

function Avatar({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('relative flex h-9 w-9 shrink-0 overflow-hidden rounded-full bg-muted', className)}>{children}</div>;
}

function AvatarImage({ className, ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  return <img className={cn('h-full w-full object-cover', className)} {...props} />;
}

function AvatarFallback({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground', className)}>{children}</div>;
}

export { Avatar, AvatarImage, AvatarFallback };
