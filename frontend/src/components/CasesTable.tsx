'use client';

import Link from 'next/link';
import type { CaseSummary } from '@/lib/api';
import { StatusPill } from './StatusPill';
import { formatDate } from '@/lib/format';

export function CasesTable({ cases }: { cases: CaseSummary[] }) {
  if (cases.length === 0) {
    return (
      <p className="text-sm text-[#6B6B66] py-10 text-center border-t border-hairline">
        No cases match these filters.
      </p>
    );
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b border-hairline text-left">
          <th className="py-2 pr-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal">
            Corporate Debtor
          </th>
          <th className="py-2 pr-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal">
            Case No.
          </th>
          <th className="py-2 pr-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal">
            Bench
          </th>
          <th className="py-2 pr-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal">
            Outcome
          </th>
          <th className="py-2 pr-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal">
            Latest Order
          </th>
          <th className="py-2 pl-3 text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] font-normal text-right">
            Orders
          </th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <tr key={c.id} className="border-b border-hairline hover:bg-ink/[0.02]">
            <td className="py-2.5 pr-3">
              <Link href={`/cases/${c.id}`} className="hover:underline focus:outline-none focus-visible:ring-1 focus-visible:ring-ink">
                {c.corporate_debtor_name}
              </Link>
            </td>
            <td className="py-2.5 pr-3 font-mono text-xs text-[#6B6B66] tabular-nums">
              {c.canonical_case_number ?? '—'}
            </td>
            <td className="py-2.5 pr-3 font-mono text-xs">{c.bench ?? '—'}</td>
            <td className="py-2.5 pr-3">
              {c.current_outcome ? <StatusPill outcome={c.current_outcome} /> : '—'}
            </td>
            <td className="py-2.5 pr-3 font-mono text-xs tabular-nums">
              {formatDate(c.latest_order_date)}
            </td>
            <td className="py-2.5 pl-3 font-mono text-xs tabular-nums text-right">
              {c.order_count}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
