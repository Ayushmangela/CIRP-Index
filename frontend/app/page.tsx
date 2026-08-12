export default function HomePage() {
  return (
    <div className="text-center max-w-xl mx-auto space-y-4">
      <h2 className="text-2xl font-serif text-[#1A1A1A]">
        Searchable, Evidence-Linked Insolvency Orders
      </h2>
      <p className="text-sm text-gray-600 leading-relaxed">
        Every structured fact displayed is traceable to a verbatim span in a
        source order published by the Insolvency and Bankruptcy Board of
        India.
      </p>
      <div className="pt-4">
        <span className="inline-block px-3 py-1 text-xs font-mono bg-[#3B5284]/10 text-[#3B5284] border border-[#3B5284]/20 rounded-full">
          Phase 1 — Monorepo Scaffolding Ready
        </span>
      </div>
    </div>
  );
}
