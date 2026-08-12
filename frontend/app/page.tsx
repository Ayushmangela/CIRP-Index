export default function HomePage() {
  return (
    <div className="text-center max-w-2xl mx-auto">
      <div className="w-10 h-px bg-ink mx-auto mb-6" aria-hidden />

      <h2 className="text-4xl font-serif leading-tight text-[#1A1A1A]">
        Searchable, Evidence-Linked
        <br />
        Insolvency Orders
      </h2>

      <p className="mt-5 text-sm text-[#6B6B66] leading-relaxed max-w-md mx-auto">
        Every structured fact displayed is traceable to a verbatim span in a
        source order published by the Insolvency and Bankruptcy Board of
        India.
      </p>

      <p className="mt-3 text-xs font-mono tabular-nums text-[#9A9892]">
        IBBI · NCLT · Facilitation Copies
      </p>

      <div className="w-10 h-px bg-ink mx-auto mt-8 mb-6" aria-hidden />

      <span className="inline-block px-3 py-1 text-[11px] font-mono uppercase tracking-wider text-ink border border-ink/25 bg-ink/[0.04]">
        Phase 1 — Monorepo Scaffolding Ready
      </span>
    </div>
  );
}
