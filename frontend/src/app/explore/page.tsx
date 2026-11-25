"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { PlanetCard, PlanetCardSkeleton } from "@/components/planets/planet-card";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorNotice, SectionHeading } from "@/components/ui/primitives";
import { api, buildQuery } from "@/lib/api";
import { pluralise } from "@/lib/format";
import type { PlanetFilters, PlanetSortField } from "@/lib/types";

const SORTS: { value: PlanetSortField; label: string }[] = [
  { value: "habitability", label: "Habitability" },
  { value: "esi", label: "Earth similarity" },
  { value: "distance", label: "Distance" },
  { value: "temperature", label: "Temperature" },
  { value: "radius", label: "Radius" },
  { value: "mass", label: "Mass" },
  { value: "discovery_year", label: "Discovery year" },
  { value: "name", label: "Name" },
];

const SPECTRAL = ["F", "G", "K", "M"];
const SIZES = ["Earth-sized", "Super-Earth", "Sub-Neptune", "Neptune-like", "Gas giant"];
const PAGE_SIZE = 24;

export default function ExplorePage() {
  return (
    <Suspense fallback={<PageShell><p className="text-starlight-400">Loading explorer…</p></PageShell>}>
      <ExploreClient />
    </Suspense>
  );
}

function ExploreClient() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filters = useMemo(() => parseFilters(params), [params]);

  const stats = useQuery({ queryKey: ["stats"], queryFn: ({ signal }) => api.stats(signal) });
  const planets = useQuery({
    queryKey: ["planets", filters],
    queryFn: ({ signal }) => api.planets(filters, signal),
  });

  function patch(next: Partial<PlanetFilters>, resetOffset = true) {
    const merged: PlanetFilters = { ...filters, ...next };
    if (resetOffset) merged.offset = 0;
    router.replace(`${pathname}${buildQuery(merged as Record<string, unknown>)}`);
  }

  const total = planets.data?.total ?? 0;
  const offset = filters.offset ?? 0;

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Catalogue"
        title="Exoplanet explorer"
        description="Filter the scored catalogue by the properties astronomers actually measure. Unknown values never sort first, and modelled masses stay marked as estimates."
      />

      <div className="grid gap-8 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-starlight-400">Search</span>
            <input
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3 text-sm"
              defaultValue={filters.q ?? ""}
              placeholder="Name or host star"
              onBlur={(event) => patch({ q: event.target.value || undefined })}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  patch({ q: (event.target as HTMLInputElement).value || undefined });
                }
              }}
            />
          </label>

          <label className="block">
            <span className="text-xs uppercase tracking-wider text-starlight-400">Sort</span>
            <select
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3 text-sm"
              value={filters.sort ?? "habitability"}
              onChange={(event) => patch({ sort: event.target.value as PlanetSortField })}
            >
              {SORTS.map((sort) => (
                <option key={sort.value} value={sort.value}>
                  {sort.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-starlight-400">Order</span>
            <select
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3 text-sm"
              value={filters.order ?? "desc"}
              onChange={(event) => patch({ order: event.target.value as "asc" | "desc" })}
            >
              <option value="desc">High to low</option>
              <option value="asc">Low to high</option>
            </select>
          </label>

          <RangeField
            label="Habitability"
            min={0}
            max={100}
            value={filters.min_habitability}
            onChange={(value) => patch({ min_habitability: value })}
          />
          <RangeField
            label="ESI"
            min={0}
            max={1}
            step={0.05}
            value={filters.min_esi}
            onChange={(value) => patch({ min_esi: value })}
          />
          <RangeField
            label="Max distance (ly)"
            min={1}
            max={Math.min(stats.data?.farthest_system_ly ?? 500, 2000)}
            value={filters.max_distance_ly}
            onChange={(value) => patch({ max_distance_ly: value })}
          />
          <RangeField
            label="Max radius (R⊕)"
            min={0.3}
            max={20}
            step={0.1}
            value={filters.max_radius}
            onChange={(value) => patch({ max_radius: value })}
          />

          <fieldset>
            <legend className="text-xs uppercase tracking-wider text-starlight-400">Host star</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {SPECTRAL.map((klass) => {
                const selected = filters.spectral_class?.includes(klass);
                return (
                  <button
                    key={klass}
                    type="button"
                    aria-pressed={selected}
                    className={`rounded-full px-3 py-1 text-xs ${selected ? "bg-aurora-500 text-void-950" : "bg-void-800 text-starlight-200"}`}
                    onClick={() =>
                      patch({
                        spectral_class: toggleList(filters.spectral_class, klass),
                      })
                    }
                  >
                    {klass}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-xs uppercase tracking-wider text-starlight-400">Size class</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {SIZES.map((klass) => {
                const selected = filters.size_class?.includes(klass);
                return (
                  <button
                    key={klass}
                    type="button"
                    aria-pressed={selected}
                    className={`rounded-full px-3 py-1 text-xs ${selected ? "bg-aurora-500 text-void-950" : "bg-void-800 text-starlight-200"}`}
                    onClick={() => patch({ size_class: toggleList(filters.size_class, klass) })}
                  >
                    {klass}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="flex items-center gap-2 text-sm text-starlight-200">
            <input
              type="checkbox"
              checked={filters.in_conservative_hz === true}
              onChange={(event) =>
                patch({ in_conservative_hz: event.target.checked ? true : undefined })
              }
            />
            Conservative habitable zone
          </label>
          <label className="flex items-center gap-2 text-sm text-starlight-200">
            <input
              type="checkbox"
              checked={filters.has_habitability_score === true}
              onChange={(event) =>
                patch({ has_habitability_score: event.target.checked ? true : undefined })
              }
            />
            Has a habitability score
          </label>
          <label className="flex items-center gap-2 text-sm text-starlight-200">
            <input
              type="checkbox"
              checked={filters.include_solar_system === false}
              onChange={(event) => patch({ include_solar_system: event.target.checked ? false : true })}
            />
            Hide Solar System
          </label>

          <Button
            variant="ghost"
            className="w-full"
            onClick={() => router.replace("/explore")}
          >
            Reset filters
          </Button>
        </aside>

        <div>
          <p className="mb-4 text-sm text-starlight-400">
            {planets.data ? pluralise(total, "world") : "Loading…"}
          </p>
          {planets.isError ? (
            <ErrorNotice message="Could not load planets. Is the API running?" />
          ) : planets.isLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              {Array.from({ length: 6 }).map((_, index) => (
                <PlanetCardSkeleton key={index} />
              ))}
            </div>
          ) : planets.data && planets.data.items.length === 0 ? (
            <EmptyState
              title="Nothing matches those filters"
              description="Widen a range, or reset to see the full scored catalogue."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {planets.data?.items.map((planet) => (
                <PlanetCard key={planet.slug} planet={planet} />
              ))}
            </div>
          )}

          {total > PAGE_SIZE ? (
            <div className="mt-8 flex items-center justify-between">
              <Button
                disabled={offset <= 0}
                onClick={() => patch({ offset: Math.max(0, offset - PAGE_SIZE) }, false)}
              >
                Previous
              </Button>
              <p className="text-xs text-starlight-400">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </p>
              <Button
                disabled={!planets.data?.has_more}
                onClick={() => patch({ offset: offset + PAGE_SIZE }, false)}
              >
                Next
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </PageShell>
  );
}

function RangeField({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step?: number;
  value?: number;
  onChange: (value: number | undefined) => void;
}) {
  const current = value ?? min;
  return (
    <label className="block">
      <span className="flex justify-between text-xs uppercase tracking-wider text-starlight-400">
        {label}
        <span className="tabular-nums text-starlight-200">{value ?? "any"}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={current}
        className="range-input mt-2"
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(next === min ? undefined : next);
        }}
      />
    </label>
  );
}

function toggleList(current: string[] | undefined, value: string): string[] | undefined {
  const set = new Set(current ?? []);
  if (set.has(value)) set.delete(value);
  else set.add(value);
  const next = [...set];
  return next.length ? next : undefined;
}

function parseFilters(params: URLSearchParams): PlanetFilters {
  const num = (key: string) => {
    const raw = params.get(key);
    if (raw === null || raw === "") return undefined;
    const value = Number(raw);
    return Number.isFinite(value) ? value : undefined;
  };
  const bool = (key: string) => {
    const raw = params.get(key);
    if (raw === "true") return true;
    if (raw === "false") return false;
    return undefined;
  };
  const list = (key: string) => {
    const values = params.getAll(key);
    return values.length ? values : undefined;
  };

  return {
    q: params.get("q") || undefined,
    min_radius: num("min_radius"),
    max_radius: num("max_radius"),
    min_mass: num("min_mass"),
    max_mass: num("max_mass"),
    min_temp: num("min_temp"),
    max_temp: num("max_temp"),
    min_distance_ly: num("min_distance_ly"),
    max_distance_ly: num("max_distance_ly"),
    min_esi: num("min_esi"),
    max_esi: num("max_esi"),
    min_habitability: num("min_habitability"),
    max_habitability: num("max_habitability"),
    spectral_class: list("spectral_class"),
    size_class: list("size_class"),
    in_conservative_hz: bool("in_conservative_hz"),
    has_habitability_score: bool("has_habitability_score"),
    include_solar_system: bool("include_solar_system") ?? true,
    exclude_controversial: bool("exclude_controversial"),
    sort: (params.get("sort") as PlanetSortField | null) ?? "habitability",
    order: params.get("order") === "asc" ? "asc" : "desc",
    limit: PAGE_SIZE,
    offset: num("offset") ?? 0,
  };
}
