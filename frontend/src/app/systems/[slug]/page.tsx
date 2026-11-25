"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { PlanetActions } from "@/components/planets/planet-actions";
import { SystemViewer } from "@/components/three/system-viewer";
import { FavoriteStarButton } from "@/components/stars/favorite-star-button";
import { ButtonLink } from "@/components/ui/button";
import {
  Badge,
  EmptyState,
  ErrorNotice,
  Panel,
  SectionHeading,
  Stat,
} from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import {
  formatDistance,
  formatEsi,
  formatPeriod,
  formatRadius,
  formatScaled,
  formatScore,
  formatTemperature,
  humanise,
} from "@/lib/format";
import { SPECTRAL_DESCRIPTIONS, bandStyle } from "@/lib/scores";

export default function SystemPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["system", slug],
    queryFn: ({ signal }) => api.system(slug, signal),
  });

  if (query.isError) {
    const message =
      query.error instanceof ApiError && query.error.isNotFound
        ? `No system named ${slug}.`
        : "Could not load this system.";
    return (
      <PageShell>
        <EmptyState title="System not found" description={message} action={<ButtonLink href="/map">Stellar map</ButtonLink>} />
      </PageShell>
    );
  }

  if (!query.data) {
    return (
      <PageShell>
        <p className="text-starlight-400">Loading system…</p>
      </PageShell>
    );
  }

  const system = query.data;
  const selected =
    system.planets.find((planet) => planet.slug === selectedSlug) ?? system.planets[0] ?? null;
  const zone = system.habitable_zone;

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Planetary system"
        title={system.name}
        description={
          system.description ??
          `${SPECTRAL_DESCRIPTIONS[system.spectral_class ?? ""] ?? system.spectral_type ?? "Host star"} · ${formatDistance(system.distance_ly)}`
        }
        action={
          <div className="flex gap-2">
            <FavoriteStarButton slug={system.slug} />
            <ButtonLink href="/map">Back to map</ButtonLink>
          </div>
        }
      />

      {query.isError ? <ErrorNotice message="Failed to refresh this system." className="mb-4" /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <SystemViewer
          system={system}
          selectedSlug={selected?.slug ?? null}
          onSelect={setSelectedSlug}
        />

        <Panel className="p-5">
          <dl className="grid grid-cols-2 gap-4">
            <Stat label="Spectral type" value={system.spectral_type ?? system.spectral_class ?? "—"} />
            <Stat label="Temperature" value={formatTemperature(system.effective_temp_k)} />
            <Stat label="Mass" value={formatScaled(system.mass_solar, "M☉")} />
            <Stat label="Radius" value={formatScaled(system.radius_solar, "R☉")} />
            <Stat label="Distance" value={formatDistance(system.distance_ly)} />
            <Stat label="Age" value={formatScaled(system.age_gyr, "Gyr")} />
          </dl>
          {zone ? (
            <p className="mt-4 text-xs leading-relaxed text-starlight-400">
              Conservative habitable zone: {formatScaled(zone.runaway_greenhouse_au, "AU")} to{" "}
              {formatScaled(zone.maximum_greenhouse_au, "AU")}
              {zone.extrapolated ? " (extrapolated beyond the model’s calibration)." : "."}
            </p>
          ) : null}

          <h3 className="mt-6 font-display text-sm font-semibold uppercase tracking-wider text-starlight-300">
            Planets
          </h3>
          <ul className="mt-3 space-y-2">
            {system.planets.map((planet) => {
              const style = bandStyle(planet.habitability_band);
              const active = selected?.slug === planet.slug;
              return (
                <li key={planet.slug}>
                  <button
                    type="button"
                    onClick={() => setSelectedSlug(planet.slug)}
                    className={`w-full rounded-lg px-3 py-2 text-left ${active ? "bg-void-700" : "hover:bg-void-800/70"}`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="font-medium text-starlight-50">{planet.name}</span>
                      <Badge className={style.badge}>{formatScore(planet.habitability_score)}</Badge>
                    </span>
                    <span className="mt-1 block text-xs text-starlight-400">
                      {formatScaled(planet.semi_major_axis_au, "AU")} · {formatPeriod(planet.orbital_period_days)} ·{" "}
                      {humanise(planet.size_class)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      {selected ? (
        <Panel className="mt-8 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl text-starlight-50">{selected.name}</h2>
              <p className="text-sm text-starlight-400">
                {humanise(selected.size_class)} · ESI {formatEsi(selected.esi)}
              </p>
            </div>
            <PlanetActions slug={selected.slug} name={selected.name} starSlug={system.slug} />
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Radius" value={formatRadius(selected.radius_earth)} estimated={selected.radius_is_estimated} />
            <Stat label="Temperature" value={formatTemperature(selected.equilibrium_temp_k)} estimated={selected.temp_is_estimated} />
            <Stat label="Orbit" value={formatPeriod(selected.orbital_period_days)} />
            <Stat label="Habitability" value={formatScore(selected.habitability_score)} />
          </dl>
          <ButtonLink href={`/planets/${selected.slug}`} variant="primary" className="mt-6">
            Open planet dossier
          </ButtonLink>
        </Panel>
      ) : null}

      <p className="mt-6 text-center text-sm text-starlight-500">
        Prefer a list?{" "}
        <Link href={`/explore?q=${encodeURIComponent(system.name)}`} className="text-aurora-300">
          Filter the explorer for this host
        </Link>
      </p>
    </PageShell>
  );
}
