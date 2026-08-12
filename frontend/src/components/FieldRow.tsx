'use client';

import type { EvidenceItem } from '@/lib/api';
import { formatRupees, humanizeFieldName } from '@/lib/format';
import { evidenceId } from './EvidencePanel';

export function FieldRow({
  evidence,
  index,
  onSelect,
}: {
  evidence: EvidenceItem;
  index: number;
  onSelect: (index: number) => void;
}) {
  const value =
    evidence.value_numeric !== null
      ? formatRupees(evidence.value_numeric)
      : (evidence.value_text ?? '—');

  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5 border-b border-hairline">
      <span className="text-[11px] font-mono uppercase tracking-wider text-[#6B6B66] shrink-0">
        {humanizeFieldName(evidence.field_name)}
      </span>
      <span className="text-sm text-right">
        {value}
        <a
          href={`#${evidenceId(index)}`}
          onClick={(e) => {
            e.preventDefault();
            onSelect(index);
            document
              .getElementById(evidenceId(index))
              ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }}
          className="ml-1.5 align-super text-[10px] text-[#4A6FA5] hover:underline focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
          aria-label={`View source for ${humanizeFieldName(evidence.field_name)}`}
        >
          [{index + 1}]
        </a>
      </span>
    </div>
  );
}
