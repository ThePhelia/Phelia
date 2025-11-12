import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { AlertTriangle, DownloadCloud, Pause as PauseIcon } from 'lucide-react';
import { useEffect } from 'react';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, } from '@/app/components/ui/sheet';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { Progress } from '@/app/components/ui/progress';
import { Badge } from '@/app/components/ui/badge';
import { useDownloads } from '@/app/lib/api';
import { useUiState } from '@/app/stores/ui';
import DownloadActions from '@/app/components/DownloadActions';
import { formatDownloadEta, formatDownloadProgress, formatDownloadSpeed, formatDownloadStatus, } from '@/app/lib/downloads';
function formatProgress(item) {
    return formatDownloadProgress(item);
}
function DownloadsDrawer() {
    const { downloadsOpen, setDownloadsOpen } = useUiState();
    const { data, isLoading, isError, refetch } = useDownloads(downloadsOpen);
    useEffect(() => {
        if (downloadsOpen) {
            void refetch();
        }
    }, [downloadsOpen, refetch]);
    return (_jsx(Sheet, { open: downloadsOpen, onOpenChange: setDownloadsOpen, children: _jsxs(SheetContent, { side: "right", className: "w-full max-w-xl border-l border-border/60", children: [_jsxs(SheetHeader, { children: [_jsxs(SheetTitle, { className: "flex items-center gap-2 text-lg font-semibold", children: [_jsx(DownloadCloud, { className: "h-5 w-5 text-[color:var(--accent)]" }), " Downloads"] }), _jsx(SheetDescription, { className: "text-sm text-muted-foreground", children: "Monitor current and recent downloads. This view is read-only." })] }), _jsx("div", { className: "mt-6 flex-1", children: isLoading ? (_jsx("div", { className: "space-y-4", children: Array.from({ length: 4 }).map((_, index) => (_jsxs("div", { className: "rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm", children: [_jsx("div", { className: "h-4 w-3/4 rounded bg-foreground/10" }), _jsx("div", { className: "mt-3 h-2 w-full rounded-full bg-foreground/5" })] }, index))) })) : isError ? (_jsxs("div", { className: "flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground", children: [_jsx(AlertTriangle, { className: "h-6 w-6 text-orange-400" }), "Failed to fetch downloads. The API may be offline."] })) : (data?.length ? _jsx(DownloadsList, { items: data }) : _jsx(EmptyDownloads, {})) })] }) }));
}
function EmptyDownloads() {
    return (_jsxs("div", { className: "flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground", children: [_jsx(PauseIcon, { className: "h-8 w-8 text-muted-foreground" }), _jsx("p", { children: "No active downloads right now." })] }));
}
function DownloadsList({ items }) {
    return (_jsx(ScrollArea, { className: "h-full rounded-3xl border border-border/40 bg-background/40", children: _jsx("div", { className: "space-y-4 p-6", children: items.map((item) => {
                const percent = Math.round((item.progress ?? 0) * 100);
                return (_jsxs("div", { className: "space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm", children: [_jsxs("div", { className: "flex items-start justify-between gap-3", children: [_jsxs("div", { className: "min-w-0 flex-1", children: [_jsx("h3", { className: "truncate text-sm font-semibold text-foreground", children: item.name ?? 'Unknown download' }), _jsx("p", { className: "text-xs text-muted-foreground", children: item.save_path ? item.save_path : '—' })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx(Badge, { variant: "outline", children: formatDownloadStatus(item.status) }), _jsx(DownloadActions, { item: item })] })] }), _jsx(Progress, { value: percent }), _jsxs("div", { className: "flex items-center justify-between text-xs text-muted-foreground", children: [_jsx("span", { children: formatProgress(item) }), _jsx("span", { children: formatDownloadSpeed(item.dlspeed) }), _jsx("span", { children: formatDownloadEta(item.eta) })] })] }, item.id));
            }) }) }));
}
export default DownloadsDrawer;
