import CatalogGrid from '@/app/components/CatalogGrid';
import FiltersBar from '@/app/components/FiltersBar';
import { useQueryParams } from '@/app/hooks/useQueryParams';
import { useDiscover, useSearch } from '@/app/lib/api';
import type { DiscoverParams } from '@/app/lib/types';
import { safeString } from '@/app/utils/safe';

type FilterState = {
  sort: NonNullable<DiscoverParams['sort']>;
  year: string;
  genre: string;
  search: string;
};

const defaults: FilterState = { sort: 'trending', year: '', genre: '', search: '' };

function MoviesPage() {
  const [filters, setFilters] = useQueryParams<FilterState>(defaults);
  const normalizedSearch = safeString(filters.search);
  const normalizedYear = safeString(filters.year);
  const normalizedGenre = safeString(filters.genre);

  const discoverParams = {
    sort: filters.sort,
    year: normalizedYear || undefined,
    genre: normalizedGenre || undefined,
  };

  const discoverQuery = useDiscover('movie', discoverParams);
  const searchQuery = useSearch({ q: normalizedSearch, kind: 'movie' });

  const activeQuery = normalizedSearch ? searchQuery : discoverQuery;
  const items = activeQuery.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold text-foreground">Movies</h1>
      <FiltersBar
        kind="movie"
        filters={filters}
        onChange={(next) => setFilters({ ...filters, ...next })}
      />
      <CatalogGrid
        items={items}
        loading={activeQuery.isLoading || activeQuery.isFetching}
        hasNextPage={Boolean(activeQuery.hasNextPage)}
        fetchNextPage={activeQuery.fetchNextPage}
      />
    </div>
  );
}

export default MoviesPage;
