"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { PlanetActions } from "@/components/planets/planet-actions";
import { PlanetCard } from "@/components/planets/planet-card";
import { EsiBreakdown } from "@/components/score/esi-breakdown";
import { HabitabilityBreakdown } from "@/components/score/habitability-breakdown";
import { ScoreRing } from "@/components/score/score-ring";
import { PlanetViewer } from "@/components/three/planet-viewer";
import { ButtonLink } from "@/components/ui/button";
import {
  Badge,
  EmptyState,
  Panel,
  SectionHeading,
  Stat,
} from "@/components/ui/primitives";
import { api, ApiError } from "@/lib/api";
import {
  EM_DASH,
  formatDistance,
  formatEsi,
  formatMass,
  formatPercent,
  formatPeriod,
  formatRadius,
  formatScaled,
  formatTemperature,
  formatYear,
  humanise,
} from "@/lib/format";
import { bandStyle, confidenceLabel, esiLabel } from "@/lib/scores";
import { usePreferences } from "@/lib/store/preferences";

export default function PlanetPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const showNotes = usePreferences((state) => state.showScienceNotes);

  const planetQuery = useQuery({
    queryKey: ["planet", slug],
    queryFn: ({ signal }) => api.planet(slug, signal),
  });
  const similar = useQuery({
    queryKey: ["similar", slug],
    queryFn: ({ signal }) => api.similarPlanets(slug, 4, signal),
    enabled: planetQuery.isSuccess,
  });
  const siblings = useQuery({
    queryKey: ["siblings", slug],
    queryFn: ({ signal }) => api.planetSiblings(slug, signal),
    enabled: planetQuery.isSuccess,
  });

  if (planetQuery.isError) {
    const missing = planetQuery.error instanceof ApiError && planetQuery.error.isNotFound;
    return (
      <PageShell>
        <EmptyState
          title={missing ? "Planet not in the catalogue" : "Could not load this planet"}
          description={missing ? `No record for ${slug}.` : "Check that the API is running."}
          action={<ButtonLink href="/explore">Explorer</ButtonLink>}
        />
      </PageShell>
    );
  }

  const planet = planetQuery.data;
  if (!planet) {
    return (
      <PageShell>
        <p className="text-starlight-400">Loading planet…</p>
      </PageShell>
    );
  }

  const style = bandStyle(planet.habitability_band);

  return (
    <PageShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-aurora-400">
            {planet.star.name}
          </p>
          <h1 className="font-display text-4xl text-starlight-50">{planet.name}</h1>
          <p className="mt-2 text-sm text-starlight-300">
            {humanise(planet.size_class)} · {humanise(planet.thermal_class)} ·{" "}
            {formatDistance(planet.star.distance_ly)}
          </p>
        </div>
        <PlanetActions slug={planet.slug} name={planet.name} starSlug={planet.star.slug} />
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <PlanetViewer
          slug={planet.slug}
          appearance={planet.appearance}
          starColor={planet.star.color_hex ?? undefined}
        />
        <Panel className="flex flex-col items-center justify-center gap-6 p-6 sm:flex-row sm:items-start">
          <ScoreRing
            size="lg"
            score={planet.habitability_score}
            band={planet.habitability_band}
            confidence={planet.habitability_confidence}
          />
          <div className="space-y-3 text-center sm:text-left">
            <Badge className={style.badge}>{style.label}</Badge>
            <p className="text-sm text-starlight-300">
              ESI {formatEsi(planet.esi)} · {esiLabel(planet.esi)}
            </p>
            <p className="text-xs text-starlight-400">
              {confidenceLabel(planet.habitability_confidence)} (
              {formatPercent(planet.habitability_confidence)})
            </p>
            {planet.in_conservative_hz ? (
              <p className="text-xs text-biosphere-300">Inside the conservative habitable zone</p>
            ) : planet.in_optimistic_hz ? (
              <p className="text-xs text-solar-300">Inside the optimistic habitable zone only</p>
            ) : (
              <p className="text-xs text-starlight-400">Outside the modelled habitable zone</p>
            )}
            <ButtonLink href={`/systems/${planet.star.slug}`}>View in system</ButtonLink>
          </div>
        </Panel>
      </div>

      <dl className="mt-10 grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
        <Stat label="Radius" value={formatRadius(planet.radius_earth)} estimated={planet.radius_is_estimated} />
        <Stat label="Mass" value={formatMass(planet.mass_earth)} estimated={planet.mass_is_estimated} />
        <Stat
          label="Equilibrium temperature"
          value={formatTemperature(planet.equilibrium_temp_k)}
          estimated={planet.temp_is_estimated}
        />
        <Stat label="Orbital period" value={formatPeriod(planet.orbital_period_days)} />
        <Stat
          label="Semi-major axis"
          value={formatScaled(planet.semi_major_axis_au, "AU")}
          estimated={planet.axis_is_estimated}
        />
        <Stat label="Eccentricity" value={formatScaled(planet.eccentricity, "")} />
        <Stat label="Insolation" value={formatScaled(planet.insolation_earth, "S⊕")} />
        <Stat label="Density" value={formatScaled(planet.density_g_cm3, "g/cm³")} />
        <Stat label="Gravity" value={formatScaled(planet.surface_gravity_ms2, "m/s²")} />
        <Stat label="Escape velocity" value={formatScaled(planet.escape_velocity_km_s, "km/s")} />
        <Stat
          label="Tidal locking"
          value={planet.tidal_locking_likelihood == null ? EM_DASH : formatPercent(planet.tidal_locking_likelihood)}
        />
        <Stat label="Discovery" value={`${planet.discovery_method ?? EM_DASH} · ${formatYear(planet.discovery_year)}`} />
      </dl>

      {planet.mass_is_minimum ? (
        <p className="mt-4 text-xs text-solar-300">
          The mass is a radial-velocity minimum (M sin i). The true mass is higher by an unknown
          inclination factor.
        </p>
      ) : null}

      {showNotes && planet.notes ? (
        <p className="mt-6 max-w-3xl text-sm leading-relaxed text-starlight-300">{planet.notes}</p>
      ) : null}

      <div className="mt-12 grid gap-8 lg:grid-cols-2">
        <Panel className="p-6">
          <h2 className="mb-4 font-display text-xl text-starlight-50">Habitability</h2>
          {planet.habitability ? (
            <HabitabilityBreakdown habitability={planet.habitability} />
          ) : (
            <p className="text-sm text-starlight-400">Not enough measurements to score this world.</p>
          )}
        </Panel>
        <Panel className="p-6">
          <h2 className="mb-4 font-display text-xl text-starlight-50">Earth similarity</h2>
          {planet.esi_detail ? (
            <EsiBreakdown esi={planet.esi_detail} />
          ) : (
            <p className="text-sm text-starlight-400">ESI could not be computed.</p>
          )}
        </Panel>
      </div>

      {siblings.data && siblings.data.length > 1 ? (
        <section className="mt-14">
          <SectionHeading title="Sibling worlds" description={`Other planets orbiting ${planet.star.name}.`} />
          <div className="flex flex-wrap gap-2">
            {siblings.data.map((sibling) => (
              <Link
                key={sibling.slug}
                href={`/planets/${sibling.slug}`}
                className={`rounded-full px-3 py-1.5 text-sm ${sibling.slug === planet.slug ? "bg-aurora-500 text-void-950" : "bg-void-800 text-starlight-200"}`}
              >
                {sibling.name}
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {similar.data && similar.data.length > 0 ? (
        <section className="mt-14">
          <SectionHeading title="Similar planets" description="Nearest neighbours in radius, temperature and ESI." />
          <div className="grid gap-4 md:grid-cols-2">
            {similar.data.map((item) => (
              <PlanetCard key={item.slug} planet={item} compact />
            ))}
          </div>
        </section>
      ) : null}

      <p className="mt-10 text-xs text-starlight-500">
        {planet.reference ?? "NASA Exoplanet Archive"} · last source date {planet.last_updated_source ?? EM_DASH}
        {planet.discovery_facility ? ` · ${planet.discovery_facility}` : ""}
        {planet.is_controversial ? " · flagged as controversial in the archive" : ""}
      </p>
    </PageShell>
  );
}
