'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { getCase } from '@/lib/api';
import { StatusPill } from '@/components/StatusPill';
import { OrderTimeline } from '@/components/OrderTimeline';
import { FieldRow } from '@/components/FieldRow';
import { EvidencePanel } from '@/components/EvidencePanel';
import { formatDate } from '@/lib/format';

export default function CaseDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const caseId = Number(params.id);
  const [activeEvidenceIndex, setActiveEvidenceIndex] = useState<number | null>(null);

  const caseQuery = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => getCase(caseId),
    enabled: Number.isFinite(caseId),
  });

  if (caseQuery.isLoading) {
    return <p className="text-sm text-[#6B6B66] py-16 text-center">Loading…</p>;
  }

  if (caseQuery.isError || !caseQuery.data) {
    return (
      <div className="text-center py-16">
        <p className="text-sm text-[#A0432B] mb-3">Case not found.</p>
        <Link href="/" className="text-xs underline">
          Back to search
        </Link>
      </div>
    );
  }

  const c = caseQuery.data;

  return (
    <div className="max-w-6xl mx-auto">
      <Link
        href="/"
        className="text-[11px] font-mono uppercase tracking-wider text-[#6B6B66] hover:text-ink"
      >
        ← Back to search
      </Link>

      <div className="mt-4 flex items-start justify-between gap-6 pb-5 border-b border-hairline">
        <div>
          <h2 className="text-2xl font-serif font-semibold text-ink">
            {c.corporate_debtor_name}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-[#6B6B66]">
            <span className="tabular-nums">{c.canonical_case_number ?? 'No case number'}</span>
            {c.bench && <span>Bench: {c.bench}</span>}
            <span className="tabular-nums">
              {formatDate(c.first_order_date)} – {formatDate(c.latest_order_date)}
            </span>
            <span>
              {c.orders.length} order{c.orders.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>
        {c.current_outcome && <StatusPill outcome={c.current_outcome} />}
      </div>

      <div className="py-6 border-b border-hairline">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-3">
          Order Timeline
        </h3>
        <OrderTimeline orders={c.orders} />
      </div>

      <div className="mt-6 flex gap-8">
        <div className="flex-1 min-w-0">
          <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
            Extracted Fields
          </h3>
          {c.evidence.length === 0 ? (
            <p className="text-sm text-[#6B6B66] py-8 border-t border-hairline">
              No fields have been extracted from this case&apos;s orders yet.
            </p>
          ) : (
            <div>
              {c.evidence.map((e, i) => (
                <FieldRow
                  key={i}
                  evidence={e}
                  index={i}
                  onSelect={setActiveEvidenceIndex}
                />
              ))}
            </div>
          )}
        </div>

        <div className="w-80 shrink-0">
          <EvidencePanel evidence={c.evidence} activeIndex={activeEvidenceIndex} />
        </div>
      </div>
    </div>
  );
}
