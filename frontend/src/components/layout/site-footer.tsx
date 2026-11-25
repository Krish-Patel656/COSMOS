import Link from "next/link";

const LINKS = [
  { href: "/explore", label: "Explorer" },
  { href: "/map", label: "Stellar map" },
  { href: "/compare", label: "Compare" },
  { href: "/simulator", label: "Simulator" },
  { href: "/methodology", label: "Methodology" },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-void-800 bg-void-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 lg:flex-row lg:items-start lg:justify-between lg:px-8">
        <div className="max-w-md">
          <p className="font-display text-lg font-semibold text-starlight-50">COSMOS</p>
          <p className="mt-2 text-sm leading-relaxed text-starlight-400">
            An interactive scientific universe over real NASA exoplanet data. Scores are
            explained, surfaces are labelled as art, and unknown values are shown as unknown.
          </p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-starlight-300 hover:text-aurora-300"
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://exoplanetarchive.ipac.caltech.edu/"
            className="text-starlight-300 hover:text-aurora-300"
            target="_blank"
            rel="noreferrer"
          >
            NASA Exoplanet Archive
          </a>
        </nav>
      </div>
      <div className="border-t border-void-800/80 py-4 text-center text-xs text-starlight-500">
        Catalogue parameters from the NASA Exoplanet Archive. Habitable-zone limits follow
        Kopparapu et al. (2013); ESI follows Schulze-Makuch et al. (2011).
      </div>
    </footer>
  );
}
