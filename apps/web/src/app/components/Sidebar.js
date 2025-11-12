import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Bookmark, Download, Film, Home, Music2, Puzzle, Settings, Tv } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/app/components/ui/tooltip';
import { useUiState } from '@/app/stores/ui';
import { cn } from '@/app/utils/cn';
const NAV_ITEMS = [
    { to: '/', label: 'Home', icon: Home },
    { to: '/movies', label: 'Movies', icon: Film },
    { to: '/tv', label: 'TV Shows', icon: Tv },
    { to: '/music', label: 'Music', icon: Music2 },
    { to: '/library', label: 'My Library', icon: Bookmark },
    { to: '/market', label: 'Marketplace', icon: Puzzle },
    { to: '/downloads', label: 'Downloads', icon: Download },
    { to: '/settings', label: 'Settings', icon: Settings },
];
const STORAGE_KEY = 'phelia:sidebar-collapsed';
function Sidebar() {
    const [hovered, setHovered] = useState(false);
    const { sidebarCollapsed, setSidebarCollapsed } = useUiState();
    useEffect(() => {
        if (typeof window === 'undefined')
            return;
        const saved = window.localStorage.getItem(STORAGE_KEY);
        if (saved) {
            setSidebarCollapsed(saved === 'true');
        }
    }, [setSidebarCollapsed]);
    useEffect(() => {
        if (typeof window === 'undefined')
            return;
        window.localStorage.setItem(STORAGE_KEY, String(sidebarCollapsed));
    }, [sidebarCollapsed]);
    const collapsed = sidebarCollapsed && !hovered;
    const content = useMemo(() => (_jsx("nav", { className: "flex flex-1 flex-col gap-1 py-6", children: NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (_jsxs(NavLink, { to: item.to, className: ({ isActive }) => cn('group flex items-center gap-3 rounded-full px-4 py-3 text-sm font-medium transition', isActive
                    ? 'bg-[color:var(--accent)]/15 text-[color:var(--accent)] shadow-glow'
                    : 'text-muted-foreground hover:bg-foreground/10 hover:text-foreground', collapsed ? 'justify-center px-0 py-2' : ''), children: [_jsx(Icon, { className: "h-5 w-5" }), !collapsed ? _jsx("span", { children: item.label }) : null] }, item.to));
        }) })), [collapsed]);
    return (_jsx(TooltipProvider, { children: _jsxs("aside", { className: cn('relative hidden min-h-screen flex-col border-r border-border/60 bg-background/80 px-4 transition-all duration-300 lg:flex', collapsed ? 'w-20 items-center' : 'w-64'), onMouseEnter: () => setHovered(true), onMouseLeave: () => setHovered(false), children: [_jsxs("div", { className: "flex items-center justify-between pt-6", children: [!collapsed ? (_jsx("span", { className: "text-sm font-semibold uppercase tracking-widest text-muted-foreground", children: "Navigation" })) : null, _jsxs(Tooltip, { children: [_jsx(TooltipTrigger, { asChild: true, children: _jsx(Button, { variant: "ghost", size: "icon", className: "rounded-full border border-border/60 bg-background/40", onClick: () => setSidebarCollapsed(!sidebarCollapsed), children: collapsed ? '›' : '‹' }) }), _jsx(TooltipContent, { children: collapsed ? 'Expand' : 'Collapse' })] })] }), collapsed ? (_jsx("div", { className: "flex flex-1 flex-col items-center gap-2 py-6", children: NAV_ITEMS.map((item) => {
                        const Icon = item.icon;
                        return (_jsxs(Tooltip, { children: [_jsx(TooltipTrigger, { asChild: true, children: _jsx(NavLink, { to: item.to, className: ({ isActive }) => cn('flex h-12 w-12 items-center justify-center rounded-full text-sm transition', isActive
                                            ? 'bg-[color:var(--accent)]/15 text-[color:var(--accent)] shadow-glow'
                                            : 'text-muted-foreground hover:bg-foreground/10 hover:text-foreground'), children: _jsx(Icon, { className: "h-5 w-5" }) }) }), _jsx(TooltipContent, { children: item.label })] }, item.to));
                    }) })) : (content)] }) }));
}
export default Sidebar;
