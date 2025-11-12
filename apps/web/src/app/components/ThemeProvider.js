import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
const ThemeContext = createContext(undefined);
const STORAGE_KEY = 'phelia:theme';
function resolveSystemTheme() {
    if (typeof window === 'undefined' || !window.matchMedia)
        return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
export function ThemeProvider({ children }) {
    const [mode, setMode] = useState(() => {
        if (typeof window === 'undefined')
            return 'dark';
        const saved = window.localStorage.getItem(STORAGE_KEY);
        return saved ?? 'system';
    });
    const [resolved, setResolved] = useState(() => mode === 'system' ? resolveSystemTheme() : mode);
    useEffect(() => {
        if (mode === 'system') {
            const listener = (event) => {
                setResolved(event.matches ? 'dark' : 'light');
            };
            const media = window.matchMedia('(prefers-color-scheme: dark)');
            setResolved(media.matches ? 'dark' : 'light');
            media.addEventListener('change', listener);
            return () => media.removeEventListener('change', listener);
        }
        setResolved(mode);
        return undefined;
    }, [mode]);
    useEffect(() => {
        if (typeof document === 'undefined')
            return;
        const root = document.documentElement;
        root.classList.toggle('dark', resolved === 'dark');
        root.style.setProperty('color-scheme', resolved);
    }, [resolved]);
    useEffect(() => {
        if (typeof window === 'undefined')
            return;
        window.localStorage.setItem(STORAGE_KEY, mode);
    }, [mode]);
    const value = useMemo(() => ({
        mode,
        resolved,
        toggle: () => setMode((current) => (current === 'dark' ? 'light' : 'dark')),
        setMode,
    }), [mode, resolved]);
    return _jsx(ThemeContext.Provider, { value: value, children: children });
}
export function useTheme() {
    const ctx = useContext(ThemeContext);
    if (!ctx)
        throw new Error('useTheme must be used within ThemeProvider');
    return ctx;
}
