import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Sannetic Vision Audit",
  description: "SEO- und GEO-Audits mit priorisierten Empfehlungen.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
