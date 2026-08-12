import type { Outcome } from '@/lib/api';

const LABELS: Record<Outcome, string> = {
  admitted: 'Admitted',
  cirp_ongoing: 'CIRP Ongoing',
  resolution_approved: 'Resolution Approved',
  liquidation: 'Liquidation',
  dissolved: 'Dissolved',
  withdrawn: 'Withdrawn',
  unclassified: 'Unclassified',
};

const COLORS: Record<Outcome, string> = {
  admitted: '#4A6FA5',
  cirp_ongoing: '#B8860B',
  resolution_approved: '#2D5F3F',
  liquidation: '#A0432B',
  dissolved: '#7A7873',
  withdrawn: '#6B5B7B',
  unclassified: '#9A9892',
};

export function outcomeLabel(outcome: Outcome): string {
  return LABELS[outcome];
}

export function outcomeColor(outcome: Outcome): string {
  return COLORS[outcome];
}

export function StatusPill({ outcome }: { outcome: Outcome }) {
  const color = COLORS[outcome];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider whitespace-nowrap"
      style={{ border: `1px solid ${color}`, color }}
    >
      {LABELS[outcome]}
    </span>
  );
}
