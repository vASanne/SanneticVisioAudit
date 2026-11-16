import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "./providers";

import "./globals.css";
import "../styles/fonts/fonts.css";
import "../styles/sannetic-styleguide.css";
import "../styles/sannetic-components.css";
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

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
