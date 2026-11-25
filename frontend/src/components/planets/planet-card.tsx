"use client";

import Link from "next/link";

import { PlanetActions } from "@/components/planets/planet-actions";
import { Badge, EstimatedMark } from "@/components/ui/primitives";
import {
  clsx,
  formatDistance,
  formatEsi,
  formatRadius,
  formatScore,
  formatTemperature,
  humanise,
} from "@/lib/format";
import { bandStyle } from "@/lib/scores";
import type { PlanetWithStar } from "@/lib/types";

export function PlanetCard({
  planet,
  compact = false,
}: {
  planet: PlanetWithStar;
  compact?: boolean;
}) {
  const style = bandStyle(planet.habitability_band);
  const color = planet.appearance?.base_color ?? "#3b4a73";

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-panel border border-void-700 bg-void-850/70 transition-colors hover:border-void-500">
      <div className="h-1.5" style={{ background: color }} />
      <Link href={`/planets/${planet.slug}`} className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate font-display text-lg font-semibold text-starlight-50 group-hover:text-aurora-300">
              {planet.name}
            </h3>
            <p className="mt-0.5 truncate text-xs text-starlight-400">
              {planet.star.name}
              {planet.star.spectral_type ? ` · ${planet.star.spectral_type}` : ""}
            </p>
          </div>
          <Badge className={style.badge}>{style.label}</Badge>
        </div>

        <dl className={clsx("mt-4 grid gap-3", compact ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-4")}>
          <CardStat label="Habitability" value={formatScore(planet.habitability_score)} />
          <CardStat label="ESI" value={formatEsi(planet.esi)} />
          <CardStat
            label="Radius"
            value={formatRadius(planet.radius_earth)}
            estimated={planet.radius_is_estimated}
          />
          <CardStat
            label="Temperature"
            value={formatTemperature(planet.equilibrium_temp_k)}
            estimated={planet.temp_is_estimated}
          />
        </dl>

        <p className="mt-4 text-xs text-starlight-400">
          {formatDistance(planet.star.distance_ly)}
          {planet.size_class ? ` · ${humanise(planet.size_class)}` : ""}
          {planet.in_conservative_hz ? " · Conservative HZ" : planet.in_optimistic_hz ? " · Optimistic HZ" : ""}
        </p>
      </Link>
      <div className="border-t border-void-800 px-3 py-2">
        <PlanetActions slug={planet.slug} name={planet.name} starSlug={planet.star.slug} />
      </div>
    </article>
  );
}

function CardStat({
  label,
  value,
  estimated = false,
}: {
  label: string;
  value: string;
  estimated?: boolean;
}) {
  return (
    <div>
      <dt className="flex items-center gap-1 text-[0.65rem] uppercase tracking-wider text-starlight-500">
        {label}
        {estimated ? <EstimatedMark /> : null}
      </dt>
      <dd className="mt-0.5 text-sm tabular-nums text-starlight-100">{value}</dd>
    </div>
  );
}

export function PlanetCardSkeleton() {
  return (
    <div className="h-64 animate-pulse rounded-panel border border-void-800 bg-void-850/50" />
  );
}
