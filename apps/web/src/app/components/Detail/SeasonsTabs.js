import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Badge } from '@/app/components/ui/badge';
function SeasonsTabs({ seasons = [] }) {
    if (!seasons.length) {
        return _jsx("p", { className: "text-sm text-muted-foreground", children: "No seasons available." });
    }
    const initial = String(seasons[0]?.season_number ?? 1);
    return (_jsxs(Tabs, { defaultValue: initial, className: "w-full", children: [_jsx(TabsList, { className: "mb-4", children: seasons.map((season) => (_jsxs(TabsTrigger, { value: String(season.season_number), children: ["Season ", season.season_number] }, season.season_number))) }), seasons.map((season) => (_jsx(TabsContent, { value: String(season.season_number), children: _jsx("div", { className: "space-y-3", children: season.episodes.map((episode) => (_jsxs("div", { className: "flex items-center justify-between rounded-2xl border border-border/60 bg-background/60 px-4 py-3 text-sm", children: [_jsx("div", { children: _jsxs("p", { className: "font-medium text-foreground", children: [episode.episode_number, ". ", episode.title] }) }), episode.watched ? _jsx(Badge, { variant: "success", children: "Watched" }) : _jsx(Badge, { variant: "outline", children: "Unwatched" })] }, episode.episode_number))) }) }, season.season_number)))] }));
}
export default SeasonsTabs;
