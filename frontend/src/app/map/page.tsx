"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { MapViewer } from "@/components/three/map-viewer";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState, ErrorNotice, Panel, SectionHeading, Stat } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EM_DASH, formatDistance, formatInteger, formatScore, pluralise } from "@/lib/format";
import { SPECTRAL_DESCRIPTIONS, bandStyle, bandForScore } from "@/lib/scores";

export default function MapPage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>("sun");
  const [maxDistance, setMaxDistance] = useState(120);

  const map = useQuery({
    queryKey: ["stellar-map", maxDistance],
    queryFn: ({ signal }) =>
      api.stellarMap({ max_distance_ly: maxDistance, limit: 800, require_planets: true }, signal),
  });

  const selected = useMemo(
    () => map.data?.find((star) => star.slug === selectedSlug) ?? map.data?.[0] ?? null,
    [map.data, selectedSlug],
  );

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Nearby sky"
        title="Stellar map"
        description="Real equatorial coordinates, compressed radially so nearby systems stay clickable. The Sun sits at the origin. Colour is photospheric temperature unless you switch to habitability."
      />

      {map.isError ? <ErrorNotice message="Could not load the stellar map." className="mb-6" /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        {map.isPending ? (
          <p className="text-starlight-400">Loading nearby systems…</p>
        ) : map.data && map.data.length > 0 ? (
          <MapViewer
            stars={map.data}
            selectedSlug={selected?.slug ?? null}
            onSelect={setSelectedSlug}
          />
        ) : (
          <EmptyState title="No mapped stars yet" description="Ingest the catalogue to plot systems." />
        )}

        <Panel className="p-5">
          <label className="block text-sm">
            <span className="flex justify-between text-xs uppercase tracking-wider text-starlight-400">
              Horizon
              <span>{maxDistance} ly</span>
            </span>
            <input
              type="range"
              min={15}
              max={400}
              value={maxDistance}
              className="range-input mt-2"
              onChange={(event) => setMaxDistance(Number(event.target.value))}
            />
          </label>

          {selected ? (
            <div className="mt-6 space-y-4">
              <div>
                <p className="font-display text-2xl text-starlight-50">{selected.name}</p>
                <p className="text-sm text-starlight-400">
                  {selected.spectral_class
                    ? SPECTRAL_DESCRIPTIONS[selected.spectral_class] ?? selected.spectral_class
                    : "Spectral type unknown"}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-4">
                <Stat label="Distance" value={formatDistance(selected.distance_ly)} />
                <Stat label="Planets" value={formatInteger(selected.planet_count)} />
                <Stat
                  label="Best habitability"
                  value={formatScore(selected.best_habitability_score)}
                />
                <Stat
                  label="Band"
                  value={
                    <span className={bandStyle(bandForScore(selected.best_habitability_score)).text}>
                      {bandStyle(bandForScore(selected.best_habitability_score)).label}
                    </span>
                  }
                />
              </dl>
              <ButtonLink href={`/systems/${selected.slug}`} variant="primary" className="w-full">
                Enter this system
              </ButtonLink>
            </div>
          ) : (
            <p className="mt-6 text-sm text-starlight-400">Select a star in the map.</p>
          )}

          <p className="mt-6 text-xs text-starlight-500">
            {map.data ? pluralise(map.data.length, "system") : EM_DASH} plotted. Directions on the
            sky are exact; only distance is compressed.
          </p>

          <ul className="mt-4 max-h-64 space-y-1 overflow-auto text-sm">
            {(map.data ?? [])
              .slice()
              .sort((a, b) => (a.distance_ly ?? 1e9) - (b.distance_ly ?? 1e9))
              .slice(0, 24)
              .map((star) => (
                <li key={star.slug}>
                  <button
                    type="button"
                    onClick={() => setSelectedSlug(star.slug)}
                    className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-void-800/80"
                  >
                    <span>{star.name}</span>
                    <span className="text-xs text-starlight-400">{formatDistance(star.distance_ly)}</span>
                  </button>
                </li>
              ))}
          </ul>
          <Link href="/explore" className="mt-4 inline-block text-xs text-aurora-300">
            Open the full explorer
          </Link>
        </Panel>
      </div>
    </PageShell>
  );
}
