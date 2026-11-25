"use client";

import { useState } from "react";

import { CanvasShell } from "@/components/three/canvas-shell";
import { SystemScene } from "@/components/three/system-scene";
import { ArtisticNotice, Badge } from "@/components/ui/primitives";
import { clsx, formatPeriod, formatScaled, humanise } from "@/lib/format";
import { useScenePaused } from "@/lib/hooks/use-reduced-motion";
import { bandStyle } from "@/lib/scores";
import { usePreferences } from "@/lib/store/preferences";
import type { SystemDetail } from "@/lib/types";

export function SystemViewer({
  system,
  selectedSlug,
  onSelect,
}: {
  system: SystemDetail;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}) {
  const paused = useScenePaused();
  const quality = usePreferences((state) => state.renderQuality);
  const [showHabitableZone, setShowHabitableZone] = useState(true);
  const [showOrbits, setShowOrbits] = useState(true);

  return (
    <div className="relative">
      <CanvasShell
        className="h-[min(72vh,44rem)] overflow-hidden rounded-panel border border-void-700 bg-void-950"
        label={`Interactive 3D view of the ${system.name} planetary system. Orbits are not to scale. Use the planet list beside the scene to select a world.`}
        camera={{ position: [0, 11, 26], fov: 42, near: 0.1, far: 400 }}
        fallback={
          <SystemFallback system={system} selectedSlug={selectedSlug} onSelect={onSelect} />
        }
      >
        <SystemScene
          system={system}
          selectedSlug={selectedSlug}
          onSelect={onSelect}
          showHabitableZone={showHabitableZone}
          showOrbits={showOrbits}
          paused={paused}
          quality={quality}
        />
      </CanvasShell>

      <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-wrap items-start justify-between gap-3 p-4">
        <div className="pointer-events-auto rounded-lg border border-void-700 bg-void-950/80 px-3 py-2 backdrop-blur">
          <p className="font-display text-sm font-semibold text-starlight-50">{system.name}</p>
          <p className="text-[0.65rem] uppercase tracking-wider text-starlight-400">
            {system.spectral_type ?? system.spectral_class ?? "Unknown type"} · not to scale
          </p>
        </div>
        <div className="pointer-events-auto flex flex-wrap gap-2">
          <ToggleChip
            pressed={showHabitableZone}
            onClick={() => setShowHabitableZone((value) => !value)}
            label="Habitable zone"
          />
          <ToggleChip
            pressed={showOrbits}
            onClick={() => setShowOrbits((value) => !value)}
            label="Orbits"
          />
        </div>
      </div>

      <ArtisticNotice
        className="mt-3"
        basis={["measured radius, mass, temperature and insolation"]}
      />
    </div>
  );
}

function ToggleChip({
  pressed,
  onClick,
  label,
}: {
  pressed: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={clsx(
        "rounded-full px-3 py-1 text-xs font-medium backdrop-blur",
        pressed
          ? "bg-aurora-500/90 text-void-950"
          : "border border-void-600 bg-void-950/70 text-starlight-200",
      )}
    >
      {label}
    </button>
  );
}

function SystemFallback({
  system,
  selectedSlug,
  onSelect,
}: {
  system: SystemDetail;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}) {
  const planets = system.planets;
  const maxAu = Math.max(
    ...planets.map((planet) => planet.semi_major_axis_au ?? 0),
    system.habitable_zone?.early_mars_au ?? 1,
    1,
  );

  return (
    <div className="rounded-panel border border-void-700 bg-void-900/70 p-6">
      <p className="mb-4 text-sm text-starlight-300">
        Flat view of {system.name}. Distances are compressed; click a world to select it.
      </p>
      <div className="relative mx-auto aspect-square max-w-xl">
        <div
          className="absolute left-1/2 top-1/2 size-8 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            background: system.color_hex ?? "#fff4ea",
            boxShadow: `0 0 24px ${system.color_hex ?? "#fff4ea"}`,
          }}
        />
        {planets.map((planet) => {
          const au = planet.semi_major_axis_au ?? 0.5;
          const t = Math.log10(au + 0.05) / Math.log10(maxAu + 0.05);
          const radius = 12 + t * 38;
          const selected = selectedSlug === planet.slug;
          return (
            <button
              key={planet.slug}
              type="button"
              onClick={() => onSelect(planet.slug)}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-void-600"
              style={{ width: `${radius * 2}%`, height: `${radius * 2}%` }}
              aria-label={`${planet.name}, period ${formatPeriod(planet.orbital_period_days)}`}
            >
              <span
                className={clsx(
                  "absolute left-1/2 top-0 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full",
                  selected ? "ring-2 ring-aurora-300" : "",
                )}
                style={{ background: planet.appearance?.base_color ?? "#9badd4" }}
              />
            </button>
          );
        })}
      </div>
      <ul className="mt-6 grid gap-2 sm:grid-cols-2">
        {planets.map((planet) => {
          const style = bandStyle(planet.habitability_band);
          return (
            <li key={planet.slug}>
              <button
                type="button"
                onClick={() => onSelect(planet.slug)}
                className={clsx(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm",
                  selectedSlug === planet.slug ? "bg-void-700" : "hover:bg-void-800/80",
                )}
              >
                <span>
                  {planet.name}
                  <span className="ml-2 text-xs text-starlight-400">
                    {formatScaled(planet.semi_major_axis_au, "AU")}
                  </span>
                </span>
                <Badge className={style.badge}>{humanise(planet.size_class)}</Badge>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
