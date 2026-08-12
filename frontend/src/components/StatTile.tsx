export function StatTile({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="border border-hairline p-4">
      <p className="text-[10px] font-mono uppercase tracking-[0.14em] text-[#6B6B66] mb-2">
        {label}
      </p>
      <p className="text-2xl font-serif tabular-nums text-ink">
        {value}
        {unit && <span className="text-sm font-sans text-[#6B6B66] ml-1">{unit}</span>}
      </p>
    </div>
  );
}
