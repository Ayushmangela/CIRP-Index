import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { Inter, JetBrains_Mono, Source_Serif_4 } from 'next/font/google';
import { Providers } from './providers';
import './globals.css';

const sans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const serif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'CIRP Index — Evidence-linked IBBI Orders',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${serif.variable} ${mono.variable}`}
    >
      <body className="bg-cream text-[#1A1A1A] antialiased min-h-screen font-sans">
        <Providers>
          <div className="min-h-screen flex flex-col border-x border-hairline max-w-6xl mx-auto">
            <div className="h-[3px] bg-ink" />

            <header className="px-6 pt-6 pb-5 border-b border-hairline flex justify-between items-end">
              <div>
                <Link href="/">
                  <h1 className="text-2xl font-serif font-semibold tracking-tight text-ink">
                    CIRP Index
                  </h1>
                </Link>
                <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.14em] text-[#6B6B66]">
                  IBBI Order Intelligence &amp; Evidence Resolution
                </p>
              </div>
              <nav className="flex items-center gap-4 text-[11px] font-mono uppercase tracking-wider text-[#6B6B66]">
                <Link href="/" className="hover:text-ink">
                  Search
                </Link>
                <Link href="/analytics" className="hover:text-ink">
                  Bench Analytics
                </Link>
              </nav>
            </header>

            <main className="flex-1 px-6 py-8">{children}</main>

            <footer className="border-t border-hairline bg-cream-100 px-6 py-5 text-center">
              <p className="text-xs italic text-[#6B6B66] max-w-2xl mx-auto leading-relaxed">
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
