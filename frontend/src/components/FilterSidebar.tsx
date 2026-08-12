'use client';

import type { BenchStat, Outcome, OutcomeCount } from '@/lib/api';
import { outcomeColor, outcomeLabel } from './StatusPill';

const OUTCOMES: Outcome[] = [
  'admitted',
  'cirp_ongoing',
  'resolution_approved',
  'liquidation',
  'dissolved',
  'withdrawn',
  'unclassified',
];

const YEARS = Array.from({ length: 2026 - 2016 + 1 }, (_, i) => 2026 - i);

export interface FilterState {
  outcome?: Outcome;
  bench?: string;
  year?: number;
  min_amount?: number;
}

export function FilterSidebar({
  filters,
  onChange,
  outcomeCounts,
  benchStats,
}: {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  outcomeCounts: OutcomeCount[];
  benchStats: BenchStat[];
}) {
  const countFor = (outcome: Outcome) =>
    outcomeCounts.find((c) => c.outcome === outcome)?.count ?? 0;

  return (
    <aside className="w-56 shrink-0 border-r border-hairline pr-5">
      <section className="mb-6">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
          Outcome
        </h3>
        <ul className="space-y-1">
          {OUTCOMES.map((outcome) => {
            const active = filters.outcome === outcome;
            return (
              <li key={outcome}>
                <button
                  type="button"
                  onClick={() => onChange({ ...filters, outcome: active ? undefined : outcome })}
                  className={`w-full flex items-center gap-2 text-left text-xs py-1 px-1 -mx-1 focus:outline-none focus-visible:ring-1 focus-visible:ring-ink ${
                    active ? 'bg-ink/[0.06] font-medium' : 'hover:bg-ink/[0.03]'
                  }`}
                >
                  <span
                    className="inline-block w-2.5 h-2.5 shrink-0"
                    style={{ backgroundColor: outcomeColor(outcome) }}
                    aria-hidden
                  />
                  <span className="flex-1 truncate">{outcomeLabel(outcome)}</span>
                  <span className="font-mono text-[#9A9892]">{countFor(outcome)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="mb-6">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
          Bench
        </h3>
        <select
          value={filters.bench ?? ''}
          onChange={(e) =>
            onChange({ ...filters, bench: e.target.value === '' ? undefined : e.target.value })
          }
          className="w-full text-xs border border-hairline bg-cream py-1.5 px-2 font-mono focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        >
          <option value="">All benches</option>
          {benchStats.map((b) => (
            <option key={b.bench} value={b.bench}>
              {b.bench} ({b.case_count})
            </option>
          ))}
        </select>
      </section>

      <section className="mb-6">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
          Year
        </h3>
        <select
          value={filters.year ?? ''}
          onChange={(e) =>
            onChange({
              ...filters,
              year: e.target.value === '' ? undefined : Number(e.target.value),
            })
          }
          className="w-full text-xs border border-hairline bg-cream py-1.5 px-2 font-mono focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        >
          <option value="">All years</option>
          {YEARS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </section>

      <section>
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
          Minimum claim amount
        </h3>
        <input
          type="number"
          min={0}
          inputMode="numeric"
          placeholder="e.g. 1000000"
          value={filters.min_amount ?? ''}
          onChange={(e) =>
            onChange({
              ...filters,
              min_amount: e.target.value === '' ? undefined : Number(e.target.value),
            })
          }
          className="w-full text-xs border border-hairline bg-cream py-1.5 px-2 font-mono tabular-nums focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        />
      </section>
    </aside>
  );
}
