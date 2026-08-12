'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getBenchStats, listCases } from '@/lib/api';
import { FilterSidebar, type FilterState } from '@/components/FilterSidebar';
import { FilterChips } from '@/components/FilterChips';
import { CasesTable } from '@/components/CasesTable';
import { Pagination } from '@/components/Pagination';

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [qInput, setQInput] = useState('');
  const [filters, setFilters] = useState<FilterState>({});
  const [page, setPage] = useState(1);

  const casesQuery = useQuery({
    queryKey: ['cases', q, filters, page],
    queryFn: () =>
      listCases({ q: q || undefined, ...filters, page, page_size: PAGE_SIZE }),
    placeholderData: (prev) => prev,
  });

  const benchStatsQuery = useQuery({
    queryKey: ['bench-stats'],
    queryFn: getBenchStats,
  });

  const outcomeCounts = useMemo(
    () => casesQuery.data?.outcome_counts ?? [],
    [casesQuery.data],
  );

  function applyFilters(next: FilterState) {
    setFilters(next);
    setPage(1);
  }

  function removeFilter(key: keyof FilterState) {
    const next = { ...filters };
    delete next[key];
    applyFilters(next);
  }

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(qInput);
    setPage(1);
  }

  return (
    <div className="max-w-6xl mx-auto">
      <form onSubmit={submitSearch} className="mb-6">
        <input
          type="search"
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Search corporate debtor name…"
          className="w-full text-sm border border-hairline bg-cream py-2.5 px-3 focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        />
      </form>

      <div className="flex gap-6">
        <FilterSidebar
          filters={filters}
          onChange={applyFilters}
          outcomeCounts={outcomeCounts}
          benchStats={benchStatsQuery.data ?? []}
        />

        <div className="flex-1 min-w-0">
          <FilterChips
            filters={filters}
            q={q}
            onRemove={removeFilter}
            onClearSearch={() => {
              setQ('');
              setQInput('');
              setPage(1);
            }}
          />

          {casesQuery.isLoading ? (
            <p className="text-sm text-[#6B6B66] py-10 text-center border-t border-hairline">
              Loading…
            </p>
          ) : casesQuery.isError ? (
            <p className="text-sm text-[#A0432B] py-10 text-center border-t border-hairline">
              Could not reach the API. Is the backend running?
            </p>
          ) : (
            <>
              <CasesTable cases={casesQuery.data?.items ?? []} />
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={casesQuery.data?.total ?? 0}
                onChange={setPage}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
