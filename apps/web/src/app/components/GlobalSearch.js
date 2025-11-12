import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { useDebounce } from '@/app/hooks/useDebounce';
import { useMetaSearch } from '@/app/lib/api';
import { cn } from '@/app/utils/cn';
const RECENT_KEY = 'phelia:recent-searches';
const SEARCH_KINDS = ['all', 'movie', 'tv', 'music'];
function loadRecent() {
    if (typeof window === 'undefined')
        return [];
    try {
        const raw = window.localStorage.getItem(RECENT_KEY);
        if (!raw)
            return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
    }
    catch {
        return [];
    }
}
function saveRecent(values) {
    if (typeof window === 'undefined')
        return;
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(values.slice(0, 8)));
}
function GlobalSearch() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const containerRef = useRef(null);
    const inputRef = useRef(null);
    const [query, setQuery] = useState('');
    const [kind, setKind] = useState('all');
    const [highlight, setHighlight] = useState(0);
    const [recent, setRecent] = useState(loadRecent);
    const debounced = useDebounce(query, 350);
    const [open, setOpen] = useState(false);
    const { data, isFetching } = useMetaSearch(debounced);
    const results = useMemo(() => data?.items ?? [], [data]);
    const filteredResults = useMemo(() => {
        if (kind === 'all')
            return results;
        if (kind === 'music')
            return results.filter((item) => item.type === 'album');
        return results.filter((item) => item.type === kind);
    }, [results, kind]);
    useEffect(() => {
        function handleKey(event) {
            if (event.key === '/' && event.target.tagName !== 'INPUT') {
                event.preventDefault();
                inputRef.current?.focus();
            }
        }
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, []);
    useEffect(() => {
        setHighlight(0);
    }, [kind, debounced]);
    const visible = open && (debounced.length > 1 || recent.length > 0);
    const handleSubmit = (item) => {
        const list = filteredResults;
        const next = item ?? list[highlight];
        if (!next)
            return;
        const dest = `/details/${next.type === 'album' ? 'music' : next.type}/${next.id}?provider=${next.provider}`;
        navigate(dest, { state: { backgroundLocation: location } });
        const updated = [query, ...recent.filter((value) => value !== query && value.trim())]
            .filter(Boolean)
            .slice(0, 8);
        setRecent(updated);
        saveRecent(updated);
        setOpen(false);
    };
    const handleInputBlur = (event) => {
        if (typeof window === 'undefined') {
            setOpen(false);
            return;
        }
        const next = event.relatedTarget;
        if (next && containerRef.current?.contains(next)) {
            return;
        }
        window.setTimeout(() => {
            const active = document.activeElement;
            if (!active || !containerRef.current?.contains(active)) {
                setOpen(false);
            }
        }, 50);
    };
    return (_jsxs("div", { ref: containerRef, className: "relative w-full max-w-2xl", children: [_jsxs("div", { className: "group relative flex items-center rounded-full border border-border/60 bg-background/80 px-4 py-2 shadow-sm focus-within:border-[color:var(--accent)]/80 focus-within:shadow-glow", children: [_jsx(Search, { className: "mr-2 h-4 w-4 text-muted-foreground" }), _jsx(Input, { ref: inputRef, value: query, placeholder: t('common.searchPlaceholder'), onFocus: () => setOpen(true), onBlur: handleInputBlur, onChange: (event) => setQuery(event.target.value), onKeyDown: (event) => {
                            if (event.key === 'ArrowDown') {
                                event.preventDefault();
                                setHighlight((prev) => Math.min(prev + 1, Math.max(results.length - 1, 0)));
                            }
                            else if (event.key === 'ArrowUp') {
                                event.preventDefault();
                                setHighlight((prev) => Math.max(prev - 1, 0));
                            }
                            else if (event.key === 'Enter') {
                                event.preventDefault();
                                handleSubmit();
                            }
                        }, className: "h-9 border-none bg-transparent px-0 text-sm focus-visible:ring-0" }), query ? (_jsx("button", { type: "button", onClick: () => {
                            setQuery('');
                            setOpen(false);
                        }, className: "rounded-full bg-muted/60 p-1 text-muted-foreground transition hover:text-foreground", children: _jsx(X, { className: "h-3.5 w-3.5" }) })) : (_jsx("span", { className: "ml-auto hidden rounded-full border border-border/70 px-2 py-0.5 text-[10px] uppercase text-muted-foreground sm:block", children: "/" }))] }), visible ? (_jsx("div", { className: "absolute left-0 right-0 z-40 mt-2 rounded-2xl border border-border/60 bg-background/95 shadow-2xl backdrop-blur-xl", children: _jsxs(Tabs, { defaultValue: "all", value: kind, onValueChange: (value) => setKind(value), children: [_jsx(TabsList, { className: "mx-auto mt-3 flex w-fit", children: SEARCH_KINDS.map((option) => (_jsx(TabsTrigger, { value: option, className: "capitalize", children: option }, option))) }), _jsxs(TabsContent, { value: kind, className: "px-4 pb-3 pt-2", children: [debounced.length <= 1 ? (_jsxs("div", { className: "space-y-2 text-sm text-muted-foreground", children: [_jsx("p", { className: "text-xs uppercase tracking-widest", children: "Recent" }), recent.length ? (_jsx("ul", { className: "space-y-1", children: recent.map((item) => (_jsx("li", { children: _jsx("button", { type: "button", className: "w-full rounded-lg px-3 py-2 text-left text-foreground transition hover:bg-foreground/10", onMouseDown: (event) => event.preventDefault(), onClick: () => {
                                                        setQuery(item);
                                                        setOpen(true);
                                                    }, children: item }) }, item))) })) : (_jsx("p", { className: "text-xs text-muted-foreground", children: "No recent searches yet." }))] })) : filteredResults.length ? (_jsx("ul", { className: "max-h-80 space-y-1 overflow-y-auto pr-2", children: filteredResults.map((item, index) => (_jsx("li", { children: _jsxs("button", { type: "button", onMouseDown: (event) => event.preventDefault(), onClick: () => handleSubmit(item), onMouseEnter: () => setHighlight(index), className: cn('flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition', highlight === index ? 'bg-foreground/10' : 'hover:bg-foreground/5'), children: [_jsx("div", { className: "relative h-14 w-10 overflow-hidden rounded-lg bg-muted", children: item.poster ? (_jsx("img", { src: item.poster, alt: item.title, className: "h-full w-full object-cover", loading: "lazy" })) : null }), _jsxs("div", { className: "flex-1", children: [_jsx("p", { className: "text-sm font-semibold text-foreground", children: item.title }), _jsx("p", { className: "text-xs text-muted-foreground", children: [item.subtitle, item.year].filter(Boolean).join(' • ') })] }), _jsx("span", { className: "rounded-full bg-foreground/10 px-2 py-1 text-[10px] uppercase text-muted-foreground", children: item.type })] }) }, `${item.type}-${item.id}`))) })) : (_jsx("div", { className: "px-3 py-6 text-center text-sm text-muted-foreground", children: "No results found." })), filteredResults.length > 0 ? (_jsx("div", { className: "flex justify-end pt-2", children: _jsx(Button, { size: "sm", variant: "ghost", onMouseDown: (event) => event.preventDefault(), onClick: () => handleSubmit(), children: isFetching ? 'Searching…' : t('common.viewDetails') }) })) : null] })] }) })) : null] }));
}
export default GlobalSearch;
