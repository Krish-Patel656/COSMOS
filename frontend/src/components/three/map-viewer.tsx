"use client";

import { useState } from "react";

import { CanvasShell } from "@/components/three/canvas-shell";
import { StellarMapScene } from "@/components/three/stellar-map-scene";
import { clsx, formatDistance, pluralise } from "@/lib/format";
import { useScenePaused } from "@/lib/hooks/use-reduced-motion";
import { bandStyle, bandForScore } from "@/lib/scores";
import { usePreferences } from "@/lib/store/preferences";
import type { StarMapPoint } from "@/lib/types";

export function MapViewer({
  stars,
  selectedSlug,
  onSelect,
}: {
  stars: StarMapPoint[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}) {
  const paused = useScenePaused();
  const quality = usePreferences((state) => state.renderQuality);
  const [colorByHabitability, setColorByHabitability] = useState(false);
  const [showShells, setShowShells] = useState(true);

  return (
    <div className="relative">
      <CanvasShell
        className="h-[min(78vh,48rem)] overflow-hidden rounded-panel border border-void-700 bg-void-950"
        label="Interactive 3D map of nearby stars with known planets. Directions on the sky are preserved; radial distances are compressed. Use the star list to select a system."
        camera={{ position: [8, 16, 38], fov: 50, near: 0.2, far: 800 }}
        fallback={<MapFallback stars={stars} selectedSlug={selectedSlug} onSelect={onSelect} />}
      >
        <StellarMapScene
          stars={stars}
          selectedSlug={selectedSlug}
          onSelect={onSelect}
          colorByHabitability={colorByHabitability}
          showShells={showShells}
          paused={paused}
          quality={quality}
        />
      </CanvasShell>

      <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-wrap justify-end gap-2 p-4">
        <button
          type="button"
          className={clsx(
            "pointer-events-auto rounded-full px-3 py-1 text-xs font-medium backdrop-blur",
            colorByHabitability
              ? "bg-biosphere-400 text-void-950"
              : "border border-void-600 bg-void-950/70 text-starlight-200",
          )}
          aria-pressed={colorByHabitability}
          onClick={() => setColorByHabitability((value) => !value)}
        >
          Colour by habitability
        </button>
        <button
          type="button"
          className={clsx(
            "pointer-events-auto rounded-full px-3 py-1 text-xs font-medium backdrop-blur",
            showShells
              ? "bg-aurora-500/90 text-void-950"
              : "border border-void-600 bg-void-950/70 text-starlight-200",
          )}
          aria-pressed={showShells}
          onClick={() => setShowShells((value) => !value)}
        >
          Distance shells
        </button>
      </div>
    </div>
  );
}

function MapFallback({
  stars,
  selectedSlug,
  onSelect,
}: {
  stars: StarMapPoint[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}) {
  const placed = stars
    .filter((star) => star.x_pc !== null && star.y_pc !== null)
    .slice(0, 80);

  return (
    <div className="rounded-panel border border-void-700 bg-void-900/70 p-4">
      <p className="mb-3 text-sm text-starlight-300">
        Flat projection of nearby systems. {pluralise(stars.length, "star")} loaded.
      </p>
      <ul className="grid max-h-[36rem] gap-2 overflow-auto sm:grid-cols-2 lg:grid-cols-3">
        {placed.map((star) => {
          const style = bandStyle(bandForScore(star.best_habitability_score));
          return (
            <li key={star.slug}>
              <button
                type="button"
                onClick={() => onSelect(star.slug)}
                className={clsx(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm",
                  selectedSlug === star.slug ? "bg-void-700" : "hover:bg-void-800/80",
                )}
              >
                <span>
                  <span className="block font-medium text-starlight-100">{star.name}</span>
                  <span className="block text-xs text-starlight-400">
                    {formatDistance(star.distance_ly)} · {pluralise(star.planet_count, "planet")}
                  </span>
                </span>
                <span className={clsx("text-xs font-semibold", style.text)}>
                  {star.best_habitability_score?.toFixed(0) ?? "—"}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
