import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from 'react';
import { Skeleton } from '@/app/components/ui/skeleton';
import DownloadActions from '@/app/components/DownloadActions';
import { useDownloads } from '@/app/lib/api';
import { formatDownloadEta, formatDownloadProgress, formatDownloadSpeed, formatDownloadStatus, } from '@/app/lib/downloads';
import { useUiState } from '@/app/stores/ui';
function DownloadsPage() {
    const { data, isLoading, isError, refetch } = useDownloads(true);
    const setDownloadsOpen = useUiState((state) => state.setDownloadsOpen);
    useEffect(() => {
        void refetch();
    }, [refetch]);
    if (isLoading) {
        return (_jsxs("div", { className: "space-y-4", children: [_jsx(Skeleton, { className: "h-8 w-1/3 rounded-full" }), _jsx(Skeleton, { className: "h-48 w-full rounded-3xl" })] }));
    }
    if (isError) {
        return _jsx("p", { className: "text-sm text-muted-foreground", children: "Unable to load downloads." });
    }
    return (_jsxs("div", { className: "space-y-8", children: [_jsxs("div", { className: "flex items-center justify-between", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "Downloads" }), _jsx("button", { type: "button", onClick: () => setDownloadsOpen(true), className: "rounded-full border border-border/60 px-3 py-2 text-xs uppercase tracking-widest text-muted-foreground hover:border-[color:var(--accent)] hover:text-foreground", children: "Open drawer" })] }), _jsx("div", { className: "overflow-hidden rounded-3xl border border-border/60 bg-background/60", children: _jsxs("table", { className: "min-w-full divide-y divide-border/60 text-sm", children: [_jsx("thead", { className: "bg-background/70 text-muted-foreground", children: _jsxs("tr", { children: [_jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Title" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Location" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Progress" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Speed" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "ETA" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Status" }), _jsx("th", { className: "px-6 py-3 text-left font-semibold", children: "Actions" })] }) }), _jsx("tbody", { className: "divide-y divide-border/40", children: data?.map((item) => (_jsx(DownloadRow, { item: item }, item.id))) })] }) })] }));
}
function DownloadRow({ item }) {
    return (_jsxs("tr", { className: "bg-background/40", children: [_jsx("td", { className: "px-6 py-3 font-medium text-foreground", children: item.name ?? 'Unknown download' }), _jsx("td", { className: "px-6 py-3 text-muted-foreground", children: item.save_path ?? '—' }), _jsx("td", { className: "px-6 py-3 text-muted-foreground", children: formatDownloadProgress(item) }), _jsx("td", { className: "px-6 py-3 text-muted-foreground", children: formatDownloadSpeed(item.dlspeed) }), _jsx("td", { className: "px-6 py-3 text-muted-foreground", children: formatDownloadEta(item.eta) }), _jsx("td", { className: "px-6 py-3 text-muted-foreground", children: formatDownloadStatus(item.status) }), _jsx("td", { className: "px-4 py-3 text-muted-foreground", children: _jsx(DownloadActions, { item: item, className: "justify-end" }) })] }));
}
export default DownloadsPage;
