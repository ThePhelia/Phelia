import type { InputHTMLAttributes } from 'react';
import { cn } from '@/app/utils/cn';

function Switch({ className, checked, onCheckedChange, ...props }: InputHTMLAttributes<HTMLInputElement> & { onCheckedChange?: (checked: boolean) => void }) {
  return (
    <label className={cn('relative inline-flex h-6 w-11 cursor-pointer items-center', className)}>
      <input
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        onChange={(event) => onCheckedChange?.(event.target.checked)}
        {...props}
      />
      <span className="absolute inset-0 rounded-full bg-muted transition peer-checked:bg-[color:var(--accent)]/80" />
      <span className="absolute left-1 top-1 h-4 w-4 rounded-full bg-background shadow transition peer-checked:translate-x-5" />
    </label>
  );
}

export { Switch };
