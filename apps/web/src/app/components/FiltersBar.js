import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo } from 'react';
import { ChevronDown, RotateCw } from 'lucide-react';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger, } from '@/app/components/ui/dropdown-menu';
const SORT_OPTIONS = [
    { value: 'trending', label: 'Trending' },
    { value: 'popular', label: 'Popular' },
    { value: 'new', label: 'New' },
    { value: 'az', label: 'A-Z' },
];
const DEFAULT_GENRES = {
    movie: ['Action', 'Drama', 'Comedy', 'Sci-Fi', 'Thriller'],
    tv: ['Drama', 'Reality', 'Documentary', 'Animation'],
    music: ['Rock', 'Electronic', 'Hip-Hop', 'Jazz'],
};
function FiltersBar({ kind, filters, onChange }) {
    const years = useMemo(() => {
        const current = new Date().getFullYear();
        return Array.from({ length: 21 }).map((_, index) => String(current - index));
    }, []);
    const genres = DEFAULT_GENRES[kind] ?? [];
    return (_jsxs("div", { className: "flex flex-col gap-3 rounded-3xl border border-border/60 bg-background/50 p-4 shadow-sm md:flex-row md:items-center md:justify-between", children: [_jsxs("div", { className: "flex flex-1 items-center gap-3", children: [_jsx(Input, { value: filters.search ?? '', onChange: (event) => onChange({ search: event.target.value }), placeholder: `Search ${kind === 'music' ? 'albums or artists' : kind}s`, className: "h-11 rounded-full border-border/70 bg-background/70" }), _jsxs(DropdownMenu, { children: [_jsx(DropdownMenuTrigger, { asChild: true, children: _jsxs(Button, { variant: "ghost", className: "rounded-full border border-border/60 px-4", children: ["Sort: ", SORT_OPTIONS.find((option) => option.value === filters.sort)?.label ?? 'Trending', _jsx(ChevronDown, { className: "ml-2 h-4 w-4" })] }) }), _jsxs(DropdownMenuContent, { align: "start", className: "min-w-[12rem]", children: [_jsx(DropdownMenuLabel, { children: "Sort by" }), _jsx(DropdownMenuSeparator, {}), SORT_OPTIONS.map((option) => (_jsx(DropdownMenuItem, { onSelect: () => onChange({ sort: option.value }), children: option.label }, option.value)))] })] }), _jsxs(DropdownMenu, { children: [_jsx(DropdownMenuTrigger, { asChild: true, children: _jsxs(Button, { variant: "ghost", className: "rounded-full border border-border/60 px-4", children: [filters.year ? `Year: ${filters.year}` : 'Year', _jsx(ChevronDown, { className: "ml-2 h-4 w-4" })] }) }), _jsxs(DropdownMenuContent, { className: "max-h-72 min-w-[10rem] overflow-y-auto", children: [_jsx(DropdownMenuItem, { onSelect: () => onChange({ year: undefined }), children: "Any year" }), years.map((year) => (_jsx(DropdownMenuItem, { onSelect: () => onChange({ year }), children: year }, year)))] })] }), _jsxs(DropdownMenu, { children: [_jsx(DropdownMenuTrigger, { asChild: true, children: _jsxs(Button, { variant: "ghost", className: "rounded-full border border-border/60 px-4", children: [filters.genre ? `Genre: ${filters.genre}` : 'Genre', _jsx(ChevronDown, { className: "ml-2 h-4 w-4" })] }) }), _jsxs(DropdownMenuContent, { className: "min-w-[12rem]", children: [_jsx(DropdownMenuItem, { onSelect: () => onChange({ genre: undefined }), children: "All genres" }), genres.map((genre) => (_jsx(DropdownMenuItem, { onSelect: () => onChange({ genre }), children: genre }, genre)))] })] }), kind === 'music' ? (_jsxs(DropdownMenu, { children: [_jsx(DropdownMenuTrigger, { asChild: true, children: _jsxs(Button, { variant: "ghost", className: "rounded-full border border-border/60 px-4", children: [filters.type ? `Type: ${filters.type}` : 'Type', _jsx(ChevronDown, { className: "ml-2 h-4 w-4" })] }) }), _jsxs(DropdownMenuContent, { children: [_jsx(DropdownMenuItem, { onSelect: () => onChange({ type: undefined }), children: "All types" }), ['album', 'ep', 'single'].map((type) => (_jsx(DropdownMenuItem, { onSelect: () => onChange({ type: type }), children: type.toUpperCase() }, type)))] })] })) : null] }), _jsx("div", { className: "flex items-center gap-2", children: _jsxs(Button, { variant: "ghost", className: "rounded-full border border-border/60 px-4", onClick: () => onChange({ search: '', genre: undefined, year: undefined, sort: 'trending', type: undefined }), children: [_jsx(RotateCw, { className: "mr-2 h-4 w-4" }), " Reset"] }) })] }));
}
export default FiltersBar;
