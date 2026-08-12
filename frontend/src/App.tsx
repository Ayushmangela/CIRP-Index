import React from 'react';

export function App(): React.ReactElement {
  return (
    <div className="min-h-screen flex flex-col justify-between p-6 max-w-6xl mx-auto border-x border-[#E5E5E0]">
      <header className="border-b border-[#E5E5E0] pb-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[#0A192F]">CIRP INDEX</h1>
          <p className="text-xs text-gray-500 font-mono">IBBI Order Intelligence & Evidence Resolution</p>
        </div>
        <div className="text-xs font-mono text-gray-500 border border-[#E5E5E0] px-3 py-1 rounded-sm">
          System Status: Operational
        </div>
      </header>

      <main className="py-12 my-auto">
        <div className="text-center max-w-xl mx-auto space-y-4">
          <h2 className="text-2xl font-serif text-[#1A1A1A]">Searchable, Evidence-Linked Insolvency Orders</h2>
          <p className="text-sm text-gray-600 leading-relaxed">
            Every structured fact displayed is traceable to a verbatim span in a source order published by the Insolvency and Bankruptcy Board of India.
          </p>
          <div className="pt-4">
            <span className="inline-block px-3 py-1 text-xs font-mono bg-[#3B5284]/10 text-[#3B5284] border border-[#3B5284]/20 rounded-full">
              Phase 1 — Monorepo Scaffolding Ready
            </span>
          </div>
        </div>
      </main>

      <footer className="border-t border-[#E5E5E0] pt-4 text-center">
        <p className="text-xs italic text-gray-500">
          Orders are facilitation copies sourced from the public IBBI order listing and are not certified copies issued by any judicial authority. Verify against the original before relying on any figure.
        </p>
      </footer>
    </div>
  );
}

export default App;
