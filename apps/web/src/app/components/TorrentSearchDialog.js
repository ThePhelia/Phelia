import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { AlertTriangle, DownloadCloud, ExternalLink, Info, Loader2, Magnet, X } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/app/components/ui/dialog';
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { useTorrentSearch } from '@/app/stores/torrent-search';
import { useCreateDownload } from '@/app/lib/api';
function TorrentSearchDialog() {
    const { open, setOpen, isLoading, results, message, error, metaError, activeItem, query, } = useTorrentSearch();
    const description = activeItem?.title
        ? `Aggregated torrent results for "${activeItem.title}"`
        : 'Aggregated torrent results from configured providers.';
    return (_jsx(Dialog, { open: open, onOpenChange: setOpen, children: _jsxs(DialogContent, { className: "max-w-5xl", children: [_jsxs(DialogHeader, { className: "relative", children: [_jsxs(DialogTitle, { className: "flex items-center gap-2 text-2xl font-semibold", children: [_jsx(DownloadCloud, { className: "h-6 w-6 text-[color:var(--accent)]" }), " Torrent results"] }), _jsx(DialogDescription, { className: "text-sm text-muted-foreground", children: description }), _jsxs(DialogClose, { className: "absolute right-6 top-6 flex h-9 w-9 items-center justify-center rounded-full border border-border/60 bg-background/80 text-muted-foreground transition hover:text-foreground", children: [_jsx(X, { className: "h-4 w-4" }), _jsx("span", { className: "sr-only", children: "Close" })] })] }), _jsxs("div", { className: "space-y-4 px-8 pb-8", children: [query ? (_jsxs("p", { className: "text-xs text-muted-foreground", children: ["Search query: ", _jsx("span", { className: "font-mono text-foreground/80", children: query })] })) : null, message ? _jsx(MessageBanner, { message: message }) : null, metaError ? _jsx(WarningBanner, { message: metaError }) : null, isLoading ? (_jsx(LoadingState, {})) : error ? (_jsx(ErrorState, { message: error })) : results.length ? (_jsx(ResultsList, { items: results })) : (_jsx(EmptyState, {}))] })] }) }));
}
function LoadingState() {
    return (_jsxs("div", { className: "space-y-4", children: [_jsxs("div", { className: "flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/60 bg-background/60 p-8 text-sm text-muted-foreground", children: [_jsx(Loader2, { className: "h-6 w-6 animate-spin text-[color:var(--accent)]" }), _jsx("p", { children: "Fetching torrents\u2026" })] }), Array.from({ length: 3 }).map((_, index) => (_jsxs("div", { className: "animate-pulse space-y-3 rounded-2xl border border-border/60 bg-background/60 p-4 shadow-sm", children: [_jsx("div", { className: "h-5 w-2/3 rounded bg-foreground/10" }), _jsx("div", { className: "h-3 w-full rounded bg-foreground/5" }), _jsx("div", { className: "h-3 w-3/4 rounded bg-foreground/5" })] }, index)))] }));
}
function MessageBanner({ message }) {
    return (_jsxs("div", { className: "flex flex-wrap items-start gap-3 rounded-2xl border border-border/60 bg-muted/10 p-4 text-sm text-muted-foreground", children: [_jsx(Info, { className: "mt-0.5 h-5 w-5 text-[color:var(--accent)]" }), _jsx("div", { className: "space-y-2", children: _jsx("p", { children: message }) })] }));
}
function WarningBanner({ message }) {
    return (_jsxs("div", { className: "flex flex-wrap items-start gap-3 rounded-2xl border border-orange-300/40 bg-orange-400/10 p-4 text-sm text-orange-200", children: [_jsx(AlertTriangle, { className: "mt-0.5 h-5 w-5" }), _jsx("div", { className: "space-y-2", children: _jsx("p", { children: message }) })] }));
}
function ErrorState({ message }) {
    return (_jsxs("div", { className: "flex flex-col items-center justify-center gap-3 rounded-2xl border border-destructive/40 bg-destructive/10 p-8 text-center text-sm text-destructive", children: [_jsx(AlertTriangle, { className: "h-8 w-8" }), _jsx("p", { children: message })] }));
}
function EmptyState() {
    return (_jsxs("div", { className: "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/60 bg-background/60 p-8 text-center text-sm text-muted-foreground", children: [_jsx(DownloadCloud, { className: "h-8 w-8 text-muted-foreground" }), _jsx("p", { children: "No torrents were returned for this query." })] }));
}
function ResultsList({ items }) {
    return (_jsx(ScrollArea, { className: "max-h-[60vh] pr-2", children: _jsx("div", { className: "space-y-4", children: items.map((item, index) => (_jsx(TorrentResultCard, { item: item }, `${item.id}-${index}`))) }) }));
}
function TorrentResultCard({ item }) {
    const meta = item.meta ?? {};
    const providers = Array.isArray(meta.providers) ? meta.providers.filter((provider) => provider.used) : [];
    const sourceExtras = providers
        .map((provider) => provider.extra)
        .filter((extra) => extra != null && typeof extra === 'object');
    const sources = Array.isArray(meta.sources)
        ? meta.sources.filter((entry) => entry != null && typeof entry === 'object')
        : [];
    const mergedSources = [...sourceExtras, ...sources];
    const magnetLink = findFirstString(mergedSources, 'magnet');
    const downloadUrl = findFirstString(mergedSources, 'url');
    const tracker = findFirstString(mergedSources, 'tracker') ??
        findFirstString(mergedSources, 'provider') ??
        findFirstString(mergedSources, 'indexer');
    const category = findFirstString(mergedSources, 'category');
    const sizeLabel = formatSizeLabel(findFirstValue(mergedSources, 'size'));
    const seeders = findFirstNumber(mergedSources, 'seeders');
    const leechers = findFirstNumber(mergedSources, 'leechers');
    const confidence = typeof meta.confidence === 'number' ? Math.round(Math.max(0, Math.min(meta.confidence, 1)) * 100) : undefined;
    const reasons = Array.isArray(meta.reasons) ? meta.reasons : [];
    const needsConfirmation = meta.needs_confirmation === true;
    const sourceKind = typeof meta.source_kind === 'string' ? meta.source_kind : item.kind;
    const { mutateAsync, isPending, error, reset } = useCreateDownload();
    const hasDownloadSource = Boolean(magnetLink || downloadUrl);
    const errorMessage = error instanceof Error ? error.message : undefined;
    const handleAddDownload = async () => {
        if (!hasDownloadSource || isPending)
            return;
        const payload = magnetLink ? { magnet: magnetLink } : downloadUrl ? { url: downloadUrl } : undefined;
        if (!payload)
            return;
        reset();
        try {
            await mutateAsync(payload);
            toast.success(`Added "${item.title}" to the download queue.`);
        }
        catch {
            // Error is surfaced via mutation state for the user.
        }
    };
    return (_jsxs("div", { className: "space-y-4 rounded-2xl border border-border/60 bg-background/60 p-5 shadow-sm", children: [_jsx("div", { className: "flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between", children: _jsxs("div", { children: [_jsx("h3", { className: "text-base font-semibold text-foreground", children: item.title }), _jsxs("div", { className: "mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground", children: [_jsx(Badge, { variant: "outline", className: "uppercase tracking-wide text-foreground/80", children: sourceKind }), typeof confidence === 'number' ? _jsxs(Badge, { variant: "accent", children: [confidence, "% match"] }) : null, needsConfirmation ? (_jsx(Badge, { variant: "outline", className: "border-orange-400 text-orange-300", children: "Needs confirmation" })) : null, tracker ? (_jsx(Badge, { variant: "outline", className: "text-foreground/70", children: tracker })) : null] }), sizeLabel ? _jsx("p", { className: "text-sm text-muted-foreground", children: sizeLabel }) : null] }) }), _jsxs("div", { className: "flex flex-wrap items-center gap-4 text-xs text-muted-foreground", children: [seeders !== undefined ? _jsxs("span", { children: ["Seeders: ", seeders] }) : null, leechers !== undefined ? _jsxs("span", { children: ["Leechers: ", leechers] }) : null, category ? _jsxs("span", { children: ["Category: ", category] }) : null] }), providers.length ? (_jsxs("div", { className: "flex flex-wrap items-center gap-2 text-xs text-muted-foreground", children: [_jsx("span", { className: "font-semibold text-foreground/80", children: "Providers:" }), providers.map((provider) => (_jsx(Badge, { variant: "default", className: "bg-foreground/10 text-foreground/80", children: provider.name }, provider.name)))] })) : null, _jsxs("div", { className: "space-y-2", children: [_jsxs("div", { className: "flex flex-wrap gap-2", children: [_jsxs(Button, { size: "sm", onClick: handleAddDownload, disabled: !hasDownloadSource || isPending, variant: "default", children: [isPending ? (_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" })) : (_jsx(DownloadCloud, { className: "mr-2 h-4 w-4" })), isPending ? 'Adding…' : 'Download'] }), magnetLink ? (_jsxs(Button, { size: "sm", variant: "secondary", onClick: () => void copyToClipboard(magnetLink), children: [_jsx(Magnet, { className: "mr-2 h-4 w-4" }), " Copy magnet"] })) : null, downloadUrl ? (_jsx(Button, { asChild: true, size: "sm", variant: "outline", children: _jsxs("a", { href: downloadUrl, target: "_blank", rel: "noreferrer", children: [_jsx(ExternalLink, { className: "mr-2 h-4 w-4" }), " Open source"] }) })) : null] }), errorMessage ? (_jsxs("p", { className: "text-xs text-destructive", children: ["Failed to add download: ", errorMessage] })) : null, !hasDownloadSource ? (_jsx("p", { className: "text-xs text-muted-foreground", children: "No download sources are available for this torrent." })) : null] }), reasons.length ? (_jsxs("div", { className: "text-xs text-muted-foreground", children: [_jsx("span", { className: "font-semibold text-foreground/80", children: "Notes:" }), " ", reasons.join(', ')] })) : null] }));
}
function findFirstString(objects, key) {
    for (const obj of objects) {
        const value = obj[key];
        if (typeof value === 'string') {
            const trimmed = value.trim();
            if (trimmed.length > 0) {
                return trimmed;
            }
        }
    }
    return undefined;
}
function findFirstNumber(objects, key) {
    for (const obj of objects) {
        const value = obj[key];
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === 'string') {
            const parsed = Number(value);
            if (!Number.isNaN(parsed)) {
                return parsed;
            }
        }
    }
    return undefined;
}
function findFirstValue(objects, key) {
    for (const obj of objects) {
        if (key in obj) {
            return obj[key];
        }
    }
    return undefined;
}
function formatSizeLabel(value) {
    if (value === null || value === undefined)
        return undefined;
    if (typeof value === 'string') {
        const trimmed = value.trim();
        return trimmed.length ? trimmed : undefined;
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let num = value;
        let unitIndex = 0;
        while (num >= 1024 && unitIndex < units.length - 1) {
            num /= 1024;
            unitIndex += 1;
        }
        const precision = num >= 10 || Number.isInteger(num) ? 0 : 1;
        return `${num.toFixed(precision)} ${units[unitIndex]}`;
    }
    return undefined;
}
async function copyToClipboard(value) {
    try {
        await navigator.clipboard.writeText(value);
        toast.success('Magnet link copied to clipboard.');
    }
    catch (error) {
        toast.error('Unable to copy magnet link.');
    }
}
export default TorrentSearchDialog;
