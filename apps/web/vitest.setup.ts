import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import "./src/app/lib/i18n";

if (typeof window !== "undefined") {
  if (!window.matchMedia) {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    });
  }

  if (!("IntersectionObserver" in window)) {
    class MockIntersectionObserver implements IntersectionObserver {
      readonly root: Element | Document | null = null;

      readonly rootMargin = "0px";

      readonly thresholds: ReadonlyArray<number> = [];

      constructor(private readonly callback: IntersectionObserverCallback) {}

      observe(target: Element) {
        const emptyRect = new DOMRect();
        const entry: IntersectionObserverEntry = {
          time: Date.now(),
          target,
          isIntersecting: false,
          intersectionRatio: 0,
          boundingClientRect: emptyRect,
          intersectionRect: emptyRect,
          rootBounds: null,
        };
        this.callback([entry], this);
      }

      unobserve() {}

      disconnect() {}

      takeRecords(): IntersectionObserverEntry[] {
        return [];
      }
    }

    Object.defineProperty(window, "IntersectionObserver", {
      writable: true,
      configurable: true,
      value: MockIntersectionObserver,
    });
  }
}
