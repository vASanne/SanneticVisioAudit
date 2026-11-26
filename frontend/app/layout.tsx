import type { Metadata } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import { MatrixRain } from "@/components/matrix-rain";

import { Providers } from "./providers";

import "./globals.css";
import "../styles/fonts/fonts.css";
import "../styles/sannetic-styleguide.css";
import "../styles/sannetic-components.css";
import "../styles/matrix-rain.css";
import "../styles/product.css";

export const metadata: Metadata = {
  title: "Sannetic Vision Audit",
  description: "SEO- und GEO-Audits mit priorisierten Empfehlungen.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
    ],
  },
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Reading the per-request nonce opts the document into dynamic rendering so
  // Next can attach that nonce to its scripts. Without it, static HTML cannot
  // satisfy a nonce CSP.
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <html lang="de" nonce={nonce}>
      <body nonce={nonce}>
        <MatrixRain />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
