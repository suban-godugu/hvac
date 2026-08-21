import type { Metadata } from "next";
import { Suspense } from "react";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./design-tokens.css";
import "./theme.css";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { LiveTelemetryProvider } from "@/components/providers/LiveTelemetryProvider";
import { ErrorBoundary } from "@/components/hvac/ErrorBoundary";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  fallback: ["Segoe UI", "system-ui", "sans-serif"],
  adjustFontFallback: true,
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  fallback: ["Consolas", "ui-monospace", "monospace"],
  adjustFontFallback: true,
});

export const metadata: Metadata = {
  title: "HVAC AI Control Center",
  description: "Premium HVAC engineering control and optimization platform (O1–O20).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${jakarta.variable} ${jetbrains.variable}`} style={{ colorScheme: "dark" }}>
      <head>
        <link rel="stylesheet" href="/hvac-shell.css" />
      </head>
      <body className="hvac-shell text-slate-100 min-h-screen flex flex-col font-sans selection:bg-cyan-700/80 selection:text-white antialiased">
        <QueryProvider>
          <LiveTelemetryProvider>
            <Header />
            <div className="hvac-body flex flex-1 min-h-0">
            <Suspense
              fallback={
                <aside className="hvac-sidebar w-72 bg-[#080e18] border-r border-white/[0.07] h-[calc(100vh-4rem)] sticky top-16" />
              }
            >
              <Sidebar />
            </Suspense>
            <main className="hvac-main flex-1 px-6 py-7 lg:px-9 lg:py-8 overflow-y-auto w-full">
              <div className="max-w-[1600px] mx-auto w-full space-y-0">
                <ErrorBoundary>{children}</ErrorBoundary>
              </div>
            </main>
            </div>
          </LiveTelemetryProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
