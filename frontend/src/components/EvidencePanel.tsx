'use client';

import type { EvidenceItem } from '@/lib/api';
import { formatDate, humanizeFieldName } from '@/lib/format';

export function evidenceId(index: number): string {
  return `evidence-${index}`;
}

export function EvidencePanel({
  evidence,
  activeIndex,
}: {
  evidence: EvidenceItem[];
  activeIndex: number | null;
}) {
  if (evidence.length === 0) {
    return (
      <div className="sticky top-6 border border-hairline p-4">
        <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
          Evidence
        </h3>
        <p className="text-xs text-[#6B6B66]">
          No verified spans yet — nothing has been extracted from this case&apos;s orders.
        </p>
      </div>
    );
  }

  return (
    <div className="sticky top-6 border border-hairline p-4 max-h-[calc(100vh-3rem)] overflow-y-auto">
      <h3 className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-3">
        Evidence
      </h3>
      <ul className="space-y-4">
        {evidence.map((e, i) => (
          <li
            key={i}
            id={evidenceId(i)}
            className={`text-xs border-l-2 pl-3 py-0.5 transition-colors ${
              activeIndex === i ? 'border-ink' : 'border-hairline'
            }`}
          >
            <p className="text-[10px] font-mono uppercase tracking-wider text-[#6B6B66] mb-1">
              {humanizeFieldName(e.field_name)}
            </p>
            <p className="leading-relaxed">
              <span style={{ backgroundColor: '#FDF3C7' }}>{e.quote}</span>
            </p>
            <p className="mt-1 text-[10px] font-mono text-[#9A9892] tabular-nums">
              Page {e.page_number} · Order {formatDate(e.order_date)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
