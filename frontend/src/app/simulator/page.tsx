"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { EsiBreakdown } from "@/components/score/esi-breakdown";
import { HabitabilityBreakdown } from "@/components/score/habitability-breakdown";
import { ScoreRing } from "@/components/score/score-ring";
import { PlanetViewer } from "@/components/three/planet-viewer";
import { Button } from "@/components/ui/button";
import { ErrorNotice, Panel, SectionHeading, Stat } from "@/components/ui/primitives";
import { deriveAppearance } from "@/lib/appearance";
import { api } from "@/lib/api";
import { formatEsi, formatPeriod, formatScaled, formatTemperature } from "@/lib/format";
import { bandForScore } from "@/lib/scores";
import type { SimulationRequest } from "@/lib/types";

type SimValues = {
  radius_earth: number;
  mass_earth: number;
  semi_major_axis_au: number;
  eccentricity: number;
  star_effective_temp_k: number;
  star_radius_solar: number;
  star_mass_solar: number;
  star_age_gyr: number;
};

const DEFAULTS: SimValues = {
  radius_earth: 1,
  mass_earth: 1,
  semi_major_axis_au: 1,
  eccentricity: 0.0167,
  star_effective_temp_k: 5772,
  star_radius_solar: 1,
  star_mass_solar: 1,
  star_age_gyr: 4.6,
};

export default function SimulatorPage() {
  return (
    <Suspense fallback={<PageShell><p className="text-starlight-400">Loading simulator…</p></PageShell>}>
      <SimulatorClient />
    </Suspense>
  );
}

function SimulatorClient() {
  const params = useSearchParams();
  const baselineSlug = params.get("baseline");
  const [values, setValues] = useState(DEFAULTS);

  const presets = useQuery({
    queryKey: ["sim-presets"],
    queryFn: ({ signal }) => api.simulationPresets(signal),
  });

  const simulate = useMutation({
    mutationFn: (payload: SimulationRequest) => api.simulate(payload),
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      simulate.mutate({ ...values, baseline_slug: baselineSlug });
    }, 120);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, baselineSlug]);

  function update<K extends keyof typeof values>(key: K, value: number) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  const result = simulate.data;
  const appearance = useMemo(
    () =>
      deriveAppearance({
        radiusEarth: values.radius_earth,
        massEarth: values.mass_earth,
        temperatureK: result?.derived.equilibrium_temp_k,
        insolationEarth: result?.derived.insolation_earth,
        density: result?.derived.density_g_cm3,
      }),
    [values.radius_earth, values.mass_earth, result],
  );

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Laboratory"
        title="Habitability simulator"
        description="The sliders feed the identical scoring engine used for the catalogue. If a real planet with these properties exists, it will receive the same numbers."
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {(presets.data?.presets ?? []).map((preset) => (
          <Button
            key={preset.key}
            size="sm"
            onClick={() => {
              const next: SimValues = {
                radius_earth: preset.request.radius_earth ?? DEFAULTS.radius_earth,
                mass_earth: preset.request.mass_earth ?? DEFAULTS.mass_earth,
                semi_major_axis_au: preset.request.semi_major_axis_au ?? DEFAULTS.semi_major_axis_au,
                eccentricity: preset.request.eccentricity ?? 0,
                star_effective_temp_k:
                  preset.request.star_effective_temp_k ?? DEFAULTS.star_effective_temp_k,
                star_radius_solar: preset.request.star_radius_solar ?? DEFAULTS.star_radius_solar,
                star_mass_solar: preset.request.star_mass_solar ?? DEFAULTS.star_mass_solar,
                star_age_gyr: preset.request.star_age_gyr ?? DEFAULTS.star_age_gyr,
              };
              setValues(next);
            }}
          >
            {preset.label}
          </Button>
        ))}
      </div>

      {simulate.isError ? (
        <ErrorNotice message="Simulation failed. Check the API, then try a preset." className="mb-4" />
      ) : null}

      <div className="grid gap-8 xl:grid-cols-[22rem_minmax(0,1fr)_22rem]">
        <Panel className="space-y-5 p-5">
          <Slider
            label="Radius"
            unit="R⊕"
            min={0.2}
            max={16}
            step={0.01}
            value={values.radius_earth}
            onChange={(value) => update("radius_earth", value)}
          />
          <Slider
            label="Mass"
            unit="M⊕"
            min={0.05}
            max={400}
            step={0.01}
            value={values.mass_earth}
            onChange={(value) => update("mass_earth", value)}
          />
          <Slider
            label="Orbital distance"
            unit="AU"
            min={0.01}
            max={5}
            step={0.001}
            value={values.semi_major_axis_au}
            onChange={(value) => update("semi_major_axis_au", value)}
          />
          <Slider
            label="Eccentricity"
            unit=""
            min={0}
            max={0.6}
            step={0.001}
            value={values.eccentricity}
            onChange={(value) => update("eccentricity", value)}
          />
          <Slider
            label="Star temperature"
            unit="K"
            min={2500}
            max={7500}
            step={10}
            value={values.star_effective_temp_k}
            onChange={(value) => update("star_effective_temp_k", value)}
          />
          <Slider
            label="Star radius"
            unit="R☉"
            min={0.1}
            max={2.5}
            step={0.01}
            value={values.star_radius_solar}
            onChange={(value) => update("star_radius_solar", value)}
          />
          <Slider
            label="Star mass"
            unit="M☉"
            min={0.08}
            max={2}
            step={0.01}
            value={values.star_mass_solar}
            onChange={(value) => update("star_mass_solar", value)}
          />
          <Slider
            label="Star age"
            unit="Gyr"
            min={0.1}
            max={12}
            step={0.1}
            value={values.star_age_gyr}
            onChange={(value) => update("star_age_gyr", value)}
          />
        </Panel>

        <div>
          <PlanetViewer slug="simulated-world" appearance={appearance} />
          {result ? (
            <dl className="mt-6 grid grid-cols-2 gap-4">
              <Stat label="Equilibrium T" value={formatTemperature(result.derived.equilibrium_temp_k)} />
              <Stat label="Period" value={formatPeriod(result.derived.orbital_period_days)} />
              <Stat label="Insolation" value={formatScaled(result.derived.insolation_earth, "S⊕")} />
              <Stat label="Gravity" value={formatScaled(result.derived.surface_gravity_g, "g")} />
              <Stat label="Density" value={formatScaled(result.derived.density_g_cm3, "g/cm³")} />
              <Stat label="Star class" value={result.derived.star_spectral_class ?? "—"} />
            </dl>
          ) : null}
        </div>

        <Panel className="flex flex-col items-center p-5">
          {result ? (
            <>
              <ScoreRing
                size="lg"
                score={result.habitability.score}
                band={result.habitability.band || bandForScore(result.habitability.score)}
                confidence={result.habitability.confidence}
              />
              <p className="mt-3 text-sm text-starlight-300">ESI {formatEsi(result.esi.overall)}</p>
              {result.baseline ? (
                <p className="mt-2 text-xs text-starlight-400">
                  vs {result.baseline.name}: habitability{" "}
                  {signed(result.baseline.delta_habitability)} · ESI{" "}
                  {signed(result.baseline.delta_esi, 3)}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-starlight-400">Scoring…</p>
          )}
        </Panel>
      </div>

      {result ? (
        <div className="mt-10 grid gap-8 lg:grid-cols-2">
          <Panel className="p-6">
            <h2 className="mb-4 font-display text-xl">Habitability breakdown</h2>
            <HabitabilityBreakdown habitability={result.habitability} />
          </Panel>
          <Panel className="p-6">
            <h2 className="mb-4 font-display text-xl">ESI breakdown</h2>
            <EsiBreakdown esi={result.esi} />
          </Panel>
        </div>
      ) : null}
    </PageShell>
  );
}

function Slider({
  label,
  unit,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="flex justify-between text-xs uppercase tracking-wider text-starlight-400">
        {label}
        <span className="tabular-nums text-starlight-100">
          {value.toFixed(step < 0.01 ? 3 : step < 0.1 ? 2 : 1)} {unit}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        className="range-input mt-2"
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function signed(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const formatted = value.toFixed(digits);
  return value > 0 ? `+${formatted}` : formatted;
}
