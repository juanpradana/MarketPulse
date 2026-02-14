import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

export const metadata: Metadata = {
  title: "MarketPulse - Investment Intelligence Platform",
  description: "Next-gen investment intelligence platform with real-time market insights",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#09090b",
};

import { FilterProvider } from "@/context/filter-context";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className="font-sans bg-zinc-950 text-zinc-100 overflow-hidden"
        suppressHydrationWarning
      >
        <FilterProvider>
          <div className="flex h-screen">
            {/* Desktop Sidebar */}
            <div className="hidden lg:block">
              <Sidebar />
            </div>

            {/* Mobile Navigation */}
            <div className="lg:hidden">
              <Sidebar mobile />
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-auto w-full pt-14 lg:pt-8 lg:px-8 lg:pb-8">
              {children}
            </main>
          </div>
        </FilterProvider>
      </body>
    </html>
  );
}
