import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

interface UseKeyboardGridNavOptions {
  columns?: number;
  loop?: boolean;
  onActivate?: (index: number) => void;
}

export function useKeyboardGridNav(length: number, options: UseKeyboardGridNavOptions = {}) {
  const { columns = 6, loop = true, onActivate } = options;
  const [activeIndex, setActiveIndex] = useState(0);
  const itemRefs = useRef<Array<HTMLElement | null>>([]);

  useEffect(() => {
    if (activeIndex >= length) {
      setActiveIndex(length ? length - 1 : 0);
    }
  }, [activeIndex, length]);

  useEffect(() => {
    const node = itemRefs.current[activeIndex];
    if (node) {
      node.focus({ preventScroll: true });
    }
  }, [activeIndex]);

  const move = useCallback(
    (next: number) => {
      if (length === 0) return;
      let index = next;
      if (loop) {
        index = (next + length) % length;
      } else {
        index = Math.min(Math.max(next, 0), length - 1);
      }
      setActiveIndex(index);
    },
    [length, loop],
  );

  const getItemProps = useCallback(
    (index: number) => {
      const refCallback = (node: HTMLElement | null) => {
        itemRefs.current[index] = node;
      };
      return {
        ref: refCallback,
        tabIndex: index === activeIndex ? 0 : -1,
        onFocus: () => setActiveIndex(index),
        onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
          switch (event.key) {
            case 'ArrowRight':
              event.preventDefault();
              move(index + 1);
              break;
            case 'ArrowLeft':
              event.preventDefault();
              move(index - 1);
              break;
            case 'ArrowDown':
              event.preventDefault();
              move(index + columns);
              break;
            case 'ArrowUp':
              event.preventDefault();
              move(index - columns);
              break;
            case 'Home':
              event.preventDefault();
              move(0);
              break;
            case 'End':
              event.preventDefault();
              move(length - 1);
              break;
            case 'Enter':
            case ' ':
              if (onActivate) {
                event.preventDefault();
                onActivate(index);
              }
              break;
            case 'Backspace':
            case 'Escape':
              (event.target as HTMLElement)?.blur();
              break;
            default:
              break;
          }
        },
      };
    },
    [activeIndex, columns, length, move, onActivate],
  );

  return useMemo(
    () => ({
      activeIndex,
      setActiveIndex,
      getItemProps,
    }),
    [activeIndex, getItemProps],
  );
}
