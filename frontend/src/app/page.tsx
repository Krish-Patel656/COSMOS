"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PlanetCard, PlanetCardSkeleton } from "@/components/planets/planet-card";
import { HeroScene } from "@/components/three/hero-scene";
import { Button, ButtonLink } from "@/components/ui/button";
import { ErrorNotice, SectionHeading, Skeleton } from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import { formatCompact, formatInteger, pluralise } from "@/lib/format";

export default function HomePage() {
  const router = useRouter();
  const stats = useQuery({ queryKey: ["stats"], queryFn: ({ signal }) => api.stats(signal) });
  const highlights = useQuery({
    queryKey: ["highlights"],
    queryFn: ({ signal }) => api.highlights(6, signal),
  });

  async function surprise() {
    try {
      const planet = await api.randomPlanet();
      router.push(`/planets/${planet.slug}`);
    } catch (error) {
      if (error instanceof ApiError) return;
    }
  }

  const catalogue = stats.data;

  return (
    <div>
      <section className="relative isolate min-h-[88vh] overflow-hidden">
        <HeroScene />
        <div className="absolute inset-0 bg-gradient-to-t from-void-950 via-void-950/55 to-void-950/20" />
        <div className="relative mx-auto flex min-h-[88vh] max-w-7xl flex-col justify-end px-4 pb-16 pt-28 sm:px-6 lg:px-8">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-aurora-300">
            Interactive 3D exoplanet explorer
          </p>
          <h1 className="max-w-3xl font-display text-4xl font-semibold leading-[1.05] text-starlight-50 sm:text-6xl">
            Which worlds beyond the Solar System could support life?
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-starlight-200 sm:text-lg">
            COSMOS is not a catalogue dump. Search a star, fly into its system, pick a planet, and
            read the factor-by-factor reasoning behind its Earth Similarity and habitability scores.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/systems/trappist-1" variant="primary" size="lg">
              Enter TRAPPIST-1
            </ButtonLink>
            <ButtonLink href="/explore" variant="secondary" size="lg">
              Browse the explorer
            </ButtonLink>
            <Button variant="ghost" size="lg" onClick={() => void surprise()}>
              Surprise me
            </Button>
          </div>
        </div>
      </section>

      <section className="cosmic-bg border-y border-void-800">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
          <StatBlock
            label="Confirmed worlds"
            value={catalogue ? formatInteger(catalogue.planet_count) : null}
            hint="Scored with the same engine, including the Solar System"
          />
          <StatBlock
            label="Planetary systems"
            value={catalogue ? formatInteger(catalogue.star_count) : null}
            hint="Mapped in 3D from measured sky coordinates"
          />
          <StatBlock
            label="Conservative HZ"
            value={catalogue ? formatInteger(catalogue.conservative_hz_count) : null}
            hint="Inside the Kopparapu runaway-to-maximum greenhouse belt"
          />
          <StatBlock
            label="ESI ≥ 0.8"
            value={catalogue ? formatInteger(catalogue.earth_like_count) : null}
            hint="Physically Earth-like — not a claim of life"
          />
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-16 px-4 py-16 sm:px-6 lg:px-8">
        {stats.isError ? (
          <ErrorNotice message="The catalogue API is unreachable. Start the FastAPI backend and ingest data to populate COSMOS." />
        ) : null}

        {(highlights.data?.sections ?? []).map((section) => (
          <section key={section.key}>
            <SectionHeading
              eyebrow="Collections"
              title={section.title}
              description={section.description}
              action={
                <Link
                  href={hrefForSection(section.key)}
                  className="text-sm font-medium text-aurora-300 hover:text-aurora-200"
                >
                  Open in explorer
                </Link>
              }
            />
            {highlights.isLoading ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <PlanetCardSkeleton key={index} />
                ))}
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {section.planets.map((planet) => (
                  <PlanetCard key={planet.slug} planet={planet} compact />
                ))}
              </div>
            )}
          </section>
        ))}

        <section className="grid gap-6 lg:grid-cols-3">
          <Feature
            title="3D systems"
            body="Zoom from a map of nearby stars into orbits, habitable-zone rings, and individual worlds. Motion follows Kepler, compressed so inner and outer planets both stay visible."
            href="/map"
          />
          <Feature
            title="Explained scores"
            body="Every habitability and ESI figure ships with the value used, the weight applied, and a sentence for why. Estimated inputs are marked, never hidden inside the number."
            href="/methodology"
          />
          <Feature
            title="What-if laboratory"
            body="Change mass, radius, orbit or host star and watch the identical scoring engine recompute in real time — the same model that ranked the catalogue."
            href="/simulator"
          />
        </section>

        {catalogue?.last_ingest ? (
          <p className="text-center text-xs text-starlight-500">
            {pluralise(catalogue.planet_count, "planet")} from {catalogue.data_source}. Last ingest:{" "}
            {String(catalogue.last_ingest.source)} ({formatCompact(catalogue.last_ingest.planets as number)} worlds).
          </p>
        ) : null}
      </div>
    </div>
  );
}

function StatBlock({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | null;
  hint: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-starlight-400">{label}</p>
      {value === null ? (
        <Skeleton className="mt-2 h-9 w-24" />
      ) : (
        <p className="mt-1 font-display text-3xl font-semibold tabular-nums text-starlight-50">{value}</p>
      )}
      <p className="mt-1 text-xs text-starlight-500">{hint}</p>
    </div>
  );
}

function Feature({ title, body, href }: { title: string; body: string; href: string }) {
  return (
    <Link
      href={href}
      className="rounded-panel border border-void-700 bg-void-850/60 p-6 transition-colors hover:border-aurora-600/40"
    >
      <h2 className="font-display text-xl text-starlight-50">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-starlight-300">{body}</p>
    </Link>
  );
}

function hrefForSection(key: string): string {
  const map: Record<string, string> = {
    "most-earth-like": "/explore?sort=esi&min_esi=0.7&include_solar_system=false",
    "potentially-habitable": "/explore?in_conservative_hz=true&max_radius=1.8&include_solar_system=false",
    nearby: "/explore?sort=distance&order=asc&max_distance_ly=40&include_solar_system=false",
    temperate: "/explore?min_temp=200&max_temp=320&include_solar_system=false",
    extremes: "/explore?sort=temperature&order=desc&include_solar_system=false",
    recent: "/explore?sort=discovery_year&order=desc&include_solar_system=false",
    "solar-system": "/systems/sun",
  };
  return map[key] ?? "/explore";
}
