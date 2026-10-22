/**
 * Client-side appearance derivation for the simulator.
 *
 * Mirrors `backend/app/science/appearance.py` so a hypothetical planet the user
 * is tuning looks like the same world the catalogue would draw if those
 * properties were measured. The mapping is artistic in both places.
 */

import type { Appearance, SurfaceType } from "./types";

const ROCKY_RADIUS_CEILING = 1.6;

const PALETTES: Record<SurfaceType, [string, string, string]> = {
  lava: ["#c2410c", "#fbbf24", "#7c2d12"],
  scorched: ["#92400e", "#d97706", "#451a03"],
  desert: ["#c08552", "#e8c39e", "#d9bb94"],
  terrestrial: ["#2e7d5b", "#8fbf7f", "#7ec8f5"],
  ocean: ["#1d6fa5", "#4aa8d8", "#8ecbf0"],
  tundra: ["#7d8c7a", "#cfd8d1", "#bcd7e8"],
  ice: ["#cfe4f0", "#ffffff", "#d8ecf8"],
  sub_neptune: ["#6b8fd4", "#a8c4ec", "#b6cdf2"],
  gas_giant: ["#d07a32", "#f0b45a", "#e8a868"],
  unknown: ["#6b7280", "#9ca3af", "#94a3b8"],
};

const SATURN_PALETTE: [string, string, string] = ["#e6c99a", "#f7ead0", "#efe0c4"];
const EARTH_DENSITY = 5.513;
const SATURN_DENSITY = 1.0;
const RING_TEMP_MAX = 150;

export function deriveAppearance(input: {
  radiusEarth?: number | null;
  massEarth?: number | null;
  temperatureK?: number | null;
  insolationEarth?: number | null;
  density?: number | null;
}): Appearance {
  const basis: string[] = [];
  const radius = input.radiusEarth && input.radiusEarth > 0 ? input.radiusEarth : null;
  const temp = input.temperatureK && input.temperatureK > 0 ? input.temperatureK : null;

  if (radius) basis.push(`radius ${radius.toFixed(2)} R⊕`);
  if (temp) basis.push(`temperature ${Math.round(temp)} K`);
  if (input.density) basis.push(`density ${input.density.toFixed(1)} g/cm³`);
  if (input.insolationEarth) basis.push(`insolation ${input.insolationEarth.toFixed(2)} S⊕`);

  let surface: SurfaceType;
  if (radius && radius >= 8) surface = "gas_giant";
  else if (
    (radius && radius >= 4) ||
    (radius && radius > 2 && (input.density ?? 99) < 3)
  ) {
    surface = "sub_neptune";
  } else if (temp === null) surface = "unknown";
  else if (temp >= 1200) surface = "lava";
  else if (temp >= 600) surface = "scorched";
  else if (temp >= 330) surface = "desert";
  else if (temp >= 250) surface = (radius ?? 1) <= ROCKY_RADIUS_CEILING ? "terrestrial" : "ocean";
  else if (temp >= 190) surface = "tundra";
  else surface = "ice";

  let density = input.density && input.density > 0 ? input.density : null;
  if (density === null && input.massEarth && radius && input.massEarth > 0) {
    density = EARTH_DENSITY * input.massEarth / radius ** 3;
  }

  const saturnLike =
    surface === "gas_giant" &&
    density !== null &&
    density < SATURN_DENSITY &&
    (temp ?? 0) < RING_TEMP_MAX;

  const [base, accent, atmosphere] = saturnLike ? SATURN_PALETTE : PALETTES[surface];
  const banded = surface === "gas_giant" || surface === "sub_neptune";
  const hasRings = saturnLike;

  const look: Record<SurfaceType, [number, number, number, number, number]> = {
    lava: [0.35, 0.15, 0.85, 0.15, 0.45],
    scorched: [0.25, 0.1, 0.95, 0.1, 0.08],
    desert: [0.3, 0.2, 0.9, 0.05, 0],
    terrestrial: [0.55, 0.55, 0.7, 0.05, 0],
    ocean: [0.6, 0.65, 0.35, 0.1, 0],
    tundra: [0.4, 0.45, 0.8, 0.05, 0],
    ice: [0.3, 0.3, 0.45, 0.05, 0],
    sub_neptune: [0.8, 0.9, 0.5, 0, 0],
    gas_giant: [0.75, 0.95, 0.55, 0, 0],
    unknown: [0.25, 0.3, 0.85, 0.1, 0],
  };
  const [opacity, clouds, roughness, metalness, emissive] = look[surface];

  return {
    surface_type: surface,
    base_color: base,
    accent_color: accent,
    atmosphere_color: atmosphere,
    atmosphere_opacity: opacity,
    cloud_coverage: clouds,
    roughness,
    metalness,
    emissive_intensity: emissive,
    has_rings: hasRings,
    banded,
    basis,
    is_artistic: true,
  };
}
