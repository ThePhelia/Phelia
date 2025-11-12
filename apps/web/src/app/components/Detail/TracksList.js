import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
function formatDuration(seconds) {
    if (!seconds)
        return '';
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    return `${minutes}:${remainder.toString().padStart(2, '0')}`;
}
function TracksList({ tracks = [] }) {
    if (!tracks.length) {
        return _jsx("p", { className: "text-sm text-muted-foreground", children: "Tracklist unavailable." });
    }
    return (_jsx("ol", { className: "space-y-2", children: tracks.map((track) => (_jsxs("li", { className: "flex items-center justify-between rounded-2xl border border-border/40 bg-background/50 px-4 py-3 text-sm", children: [_jsxs("span", { className: "flex items-center gap-3 text-foreground", children: [_jsx("span", { className: "text-xs text-muted-foreground", children: track.index }), track.title] }), _jsx("span", { className: "text-xs text-muted-foreground", children: formatDuration(track.length) })] }, track.index))) }));
}
export default TracksList;
