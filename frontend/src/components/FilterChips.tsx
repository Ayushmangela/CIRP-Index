'use client';

import type { FilterState } from './FilterSidebar';
import { outcomeLabel } from './StatusPill';
import { formatRupees } from '@/lib/format';

export function FilterChips({
  filters,
  q,
  onRemove,
  onClearSearch,
}: {
  filters: FilterState;
  q: string;
  onRemove: (key: keyof FilterState) => void;
  onClearSearch: () => void;
}) {
  const chips: { key: keyof FilterState | 'q'; label: string }[] = [];

  if (q) chips.push({ key: 'q', label: `Search: "${q}"` });
  if (filters.outcome) chips.push({ key: 'outcome', label: outcomeLabel(filters.outcome) });
  if (filters.bench) chips.push({ key: 'bench', label: `Bench: ${filters.bench}` });
  if (filters.year) chips.push({ key: 'year', label: `Year: ${filters.year}` });
  if (filters.min_amount)
    chips.push({ key: 'min_amount', label: `Min: ${formatRupees(filters.min_amount)}` });

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-4" aria-label="Active filters">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={() => (chip.key === 'q' ? onClearSearch() : onRemove(chip.key as keyof FilterState))}
          className="inline-flex items-center gap-1.5 text-[11px] font-mono border border-hairline px-2 py-1 hover:border-ink/40 focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        >
          {chip.label}
          <span aria-hidden>×</span>
        </button>
      ))}
    </div>
  );
}
