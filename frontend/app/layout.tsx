import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'CIRP Index — Evidence-linked IBBI Orders',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#FAF9F6] text-[#1A1A1A] antialiased min-h-screen">
        <Providers>
          <div className="min-h-screen flex flex-col justify-between p-6 max-w-6xl mx-auto border-x border-[#E5E5E0]">
            <header className="border-b border-[#E5E5E0] pb-4 flex justify-between items-center">
              <div>
                <h1 className="text-xl font-bold tracking-tight text-[#0A192F]">
                  CIRP INDEX
                </h1>
                <p className="text-xs text-gray-500 font-mono">
                  IBBI Order Intelligence &amp; Evidence Resolution
                </p>
              </div>
              <div className="text-xs font-mono text-gray-500 border border-[#E5E5E0] px-3 py-1 rounded-sm">
                System Status: Operational
              </div>
            </header>

            <main className="py-12 my-auto">{children}</main>

            <footer className="border-t border-[#E5E5E0] pt-4 text-center">
              <p className="text-xs italic text-gray-500">
                Orders are facilitation copies sourced from the public IBBI
                order listing and are not certified copies issued by any
                judicial authority. Verify against the original before
                relying on any figure.
              </p>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
