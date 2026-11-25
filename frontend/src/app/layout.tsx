import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { Providers } from "@/components/providers";
import { CompareTray } from "@/components/compare/compare-tray";
import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "COSMOS — Interactive 3D Exoplanet Explorer",
    template: "%s · COSMOS",
  },
  description:
    "Explore real stars and exoplanets in 3D, and see exactly why each world scores the way it does on habitability and Earth similarity.",
  keywords: ["exoplanets", "habitability", "astronomy", "NASA Exoplanet Archive", "3D"],
  openGraph: {
    title: "COSMOS — Interactive 3D Exoplanet Explorer",
    description:
      "Six thousand real worlds, scored for habitability and Earth similarity, with the reasoning shown.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#04060d",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
      <html lang="en" data-scroll-behavior="smooth" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-screen bg-void-950 text-starlight-100 antialiased">
        <Providers>
          <a href="#main" className="sr-focusable">
            Skip to main content
          </a>
          <SiteHeader />
          <main id="main" className="min-h-[70vh] pb-20">
            {children}
          </main>
          <SiteFooter />
          <CompareTray />
        </Providers>
      </body>
    </html>
  );
}
