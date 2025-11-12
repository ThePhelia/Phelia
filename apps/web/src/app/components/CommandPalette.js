import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Compass, Download, Home, Music2, Search, Settings, Tv, Film } from 'lucide-react';
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator, CommandShortcut, } from '@/app/components/ui/command';
import { useUiState } from '@/app/stores/ui';
import { useDebounce } from '@/app/hooks/useDebounce';
import { useSearch } from '@/app/lib/api';
const NAV_ITEMS = [
    { label: 'Home', icon: Home, to: '/' },
    { label: 'Movies', icon: Film, to: '/movies' },
    { label: 'TV Shows', icon: Tv, to: '/tv' },
    { label: 'Music', icon: Music2, to: '/music' },
    { label: 'Settings', icon: Settings, to: '/settings' },
];
function CommandPalette() {
    const navigate = useNavigate();
    const { commandOpen, setCommandOpen, setDownloadsOpen } = useUiState();
    const location = useLocation();
    const [search, setSearch] = useState('');
    const debounced = useDebounce(search, 300);
    const { data, isFetching } = useSearch({ q: debounced, kind: 'all' });
    const results = useMemo(() => data?.pages.flatMap((page) => page.items) ?? [], [data]);
    useEffect(() => {
        function handler(event) {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                setCommandOpen(!commandOpen);
            }
        }
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [commandOpen, setCommandOpen]);
    return (_jsx(CommandDialog, { open: commandOpen, onOpenChange: setCommandOpen, children: _jsxs(Command, { className: "max-w-2xl", children: [_jsx(CommandInput, { placeholder: "Jump to\u2026", value: search, onValueChange: setSearch, icon: _jsx(Search, { className: "h-4 w-4 text-muted-foreground" }) }), _jsxs(CommandList, { children: [_jsx(CommandEmpty, { children: isFetching ? 'Searching…' : 'Nothing found.' }), _jsxs(CommandGroup, { heading: "Navigate", children: [NAV_ITEMS.map((item) => (_jsxs(CommandItem, { onSelect: () => {
                                        navigate(item.to);
                                        setCommandOpen(false);
                                    }, children: [_jsx(item.icon, { className: "mr-2 h-4 w-4" }), item.label, _jsx(CommandShortcut, { children: "\u21B5" })] }, item.to))), _jsxs(CommandItem, { onSelect: () => {
                                        setDownloadsOpen(true);
                                        setCommandOpen(false);
                                    }, children: [_jsx(Download, { className: "mr-2 h-4 w-4" }), " Downloads"] })] }), results.length ? _jsx(CommandSeparator, {}) : null, results.length ? (_jsx(CommandGroup, { heading: "Search results", children: results.slice(0, 6).map((item) => (_jsxs(CommandItem, { onSelect: () => {
                                    navigate(`/details/${item.kind === 'album' ? 'music' : item.kind}/${item.id}`, {
                                        state: { backgroundLocation: location },
                                    });
                                    setCommandOpen(false);
                                }, children: [_jsx(Compass, { className: "mr-2 h-4 w-4" }), _jsxs("span", { className: "flex-1", children: [item.title, _jsx("span", { className: "ml-2 text-xs text-muted-foreground", children: item.kind })] })] }, `${item.kind}-${item.id}`))) })) : null] })] }) }));
}
export default CommandPalette;
