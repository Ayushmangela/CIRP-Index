'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  Legend,
} from 'recharts';
import { getBenchStats, getOutcomesByYear, type Outcome } from '@/lib/api';
import { StatTile } from '@/components/StatTile';
import { outcomeColor, outcomeLabel } from '@/components/StatusPill';

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export default function AnalyticsPage() {
  const benchQuery = useQuery({ queryKey: ['bench-stats'], queryFn: getBenchStats });
  const outcomesQuery = useQuery({
    queryKey: ['outcomes-by-year'],
    queryFn: getOutcomesByYear,
  });

  const barData = useMemo(
    () =>
      [...(benchQuery.data ?? [])]
        .filter((b) => b.median_duration_days !== null)
        .sort((a, b) => (b.median_duration_days ?? 0) - (a.median_duration_days ?? 0))
        .map((b) => ({ bench: b.bench, days: b.median_duration_days ?? 0 })),
    [benchQuery.data],
  );

  const outcomesPresent = useMemo(() => {
    const set = new Set<Outcome>();
    for (const row of outcomesQuery.data ?? []) set.add(row.outcome);
    return Array.from(set);
  }, [outcomesQuery.data]);

  const areaData = useMemo(() => {
    const byYear = new Map<number, Record<string, number>>();
    for (const row of outcomesQuery.data ?? []) {
      const entry = byYear.get(row.year) ?? {};
      entry[row.outcome] = row.count;
      byYear.set(row.year, entry);
    }
    return Array.from(byYear.entries())
      .sort(([a], [b]) => a - b)
      .map(([year, counts]) => ({ year, ...counts }));
  }, [outcomesQuery.data]);

  const totalCases = benchQuery.data?.reduce((sum, b) => sum + b.case_count, 0) ?? 0;
  const benchCount = benchQuery.data?.length ?? 0;
  const overallMedianDuration = median(
    (benchQuery.data ?? [])
      .map((b) => b.median_duration_days)
      .filter((v): v is number => v !== null),
  );
  const mostCommonOutcome = useMemo(() => {
    const totals = new Map<Outcome, number>();
    for (const row of outcomesQuery.data ?? []) {
      totals.set(row.outcome, (totals.get(row.outcome) ?? 0) + row.count);
    }
    let best: Outcome | null = null;
    let bestCount = -1;
    for (const [outcome, count] of totals) {
      if (count > bestCount) {
        best = outcome;
        bestCount = count;
      }
    }
    return best;
  }, [outcomesQuery.data]);

  if (benchQuery.isLoading || outcomesQuery.isLoading) {
    return <p className="text-sm text-[#6B6B66] py-16 text-center">Loading…</p>;
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h2 className="text-xl font-serif font-semibold text-ink mb-6">Bench Analytics</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatTile label="Total Cases" value={totalCases.toLocaleString('en-IN')} />
        <StatTile label="Benches Represented" value={String(benchCount)} />
        <StatTile
          label="Median Case Duration"
          value={overallMedianDuration !== null ? overallMedianDuration.toFixed(0) : '—'}
          unit="days"
        />
        <StatTile
          label="Most Common Outcome"
          value={mostCommonOutcome ? outcomeLabel(mostCommonOutcome) : '—'}
        />
      </div>

      <div className="mb-10">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-3">
          Median Case Duration by Bench (days)
        </h3>
        {barData.length === 0 ? (
          <p className="text-sm text-[#6B6B66] py-8 border-t border-hairline">
            No cases with more than one order yet — duration cannot be computed.
          </p>
        ) : (
          <div style={{ width: '100%', height: Math.max(240, barData.length * 28) }}>
            <ResponsiveContainer>
              <BarChart data={barData} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E3E1DA" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fontFamily: 'monospace' }} />
                <YAxis
                  type="category"
                  dataKey="bench"
                  tick={{ fontSize: 11, fontFamily: 'monospace' }}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    border: '1px solid #E3E1DA',
                    borderRadius: 0,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="days" fill="#1F3A5F" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-3">
          Outcome Mix by Year
        </h3>
        {areaData.length === 0 ? (
          <p className="text-sm text-[#6B6B66] py-8 border-t border-hairline">
            No dated orders yet.
          </p>
        ) : (
          <div style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer>
              <AreaChart data={areaData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E3E1DA" />
                <XAxis dataKey="year" tick={{ fontSize: 11, fontFamily: 'monospace' }} />
                <YAxis tick={{ fontSize: 11, fontFamily: 'monospace' }} />
                <Tooltip
                  contentStyle={{
                    border: '1px solid #E3E1DA',
                    borderRadius: 0,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'monospace' }} />
                {outcomesPresent.map((outcome) => (
                  <Area
                    key={outcome}
                    type="monotone"
                    dataKey={outcome}
                    name={outcomeLabel(outcome)}
                    stackId="1"
                    stroke={outcomeColor(outcome)}
                    fill={outcomeColor(outcome)}
                    fillOpacity={0.6}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
