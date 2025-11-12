import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import CatalogGrid from '@/app/components/CatalogGrid';
import FiltersBar from '@/app/components/FiltersBar';
import { useQueryParams } from '@/app/hooks/useQueryParams';
import { useDiscover, useSearch } from '@/app/lib/api';
const defaults = { sort: 'trending', year: '', genre: '', search: '' };
function TvPage() {
    const [filters, setFilters] = useQueryParams(defaults);
    const discoverParams = {
        sort: filters.sort,
        year: filters.year || undefined,
        genre: filters.genre || undefined,
    };
    const discoverQuery = useDiscover('tv', discoverParams);
    const searchQuery = useSearch({ q: filters.search ?? '', kind: 'tv' });
    const activeQuery = filters.search ? searchQuery : discoverQuery;
    const items = activeQuery.data?.pages.flatMap((page) => page.items) ?? [];
    return (_jsxs("div", { className: "space-y-10", children: [_jsx("h1", { className: "text-2xl font-semibold text-foreground", children: "TV Shows" }), _jsx(FiltersBar, { kind: "tv", filters: filters, onChange: (next) => setFilters({ ...filters, ...next }) }), _jsx(CatalogGrid, { items: items, loading: activeQuery.isLoading || activeQuery.isFetching, hasNextPage: Boolean(activeQuery.hasNextPage), fetchNextPage: activeQuery.fetchNextPage })] }));
}
export default TvPage;
