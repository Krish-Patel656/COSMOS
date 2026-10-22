/**
 * Presentation rules for habitability and similarity scores.
 *
 * The thresholds here mirror `backend/app/science/habitability.py` exactly
 * (`score_band` and `_VERDICT_BANDS`). They are duplicated rather than derived
 * because the backend already sends the band string with every planet — this
 * module only needs to colour it, and colouring a band the UI invented itself
 * would be worse than colouring the one the science engine actually assigned.
 */

import type { HabitabilityBand, HabitabilityVerdict } from "./types";

export interface BandStyle {
  /** Tailwind classes for a filled badge. */
  badge: string;
  /** Tailwind classes for a progress/meter fill. */
  meter: string;
  /** Text-only accent. */
  text: string;
  /** Raw hex, for 3D materials and canvas work where classes do not apply. */
  hex: string;
  label: string;
}

const BAND_STYLES: Record<HabitabilityBand, BandStyle> = {
  "exceptional candidate": {
    badge: "bg-biosphere-500/15 text-biosphere-300 ring-1 ring-biosphere-500/40",
    meter: "bg-biosphere-400",
    text: "text-biosphere-300",
    hex: "#34d399",
    label: "Exceptional candidate",
  },
  "promising candidate": {
    badge: "bg-aurora-500/15 text-aurora-300 ring-1 ring-aurora-500/40",
    meter: "bg-aurora-400",
    text: "text-aurora-300",
    hex: "#38bdf8",
    label: "Promising candidate",
  },
  "plausible candidate": {
    badge: "bg-nebula-500/15 text-nebula-300 ring-1 ring-nebula-500/40",
    meter: "bg-nebula-400",
    text: "text-nebula-300",
    hex: "#c084fc",
    label: "Plausible candidate",
  },
  marginal: {
    badge: "bg-solar-500/15 text-solar-300 ring-1 ring-solar-500/40",
    meter: "bg-solar-400",
    text: "text-solar-300",
    hex: "#fbbf24",
    label: "Marginal",
  },
  unlikely: {
    badge: "bg-ember-500/10 text-ember-300 ring-1 ring-ember-500/30",
    meter: "bg-ember-400",
    text: "text-ember-300",
    hex: "#f87171",
    label: "Unlikely",
  },
  hostile: {
    badge: "bg-ember-500/15 text-ember-300 ring-1 ring-ember-500/40",
    meter: "bg-ember-500",
    text: "text-ember-300",
    hex: "#ef4444",
    label: "Hostile",
  },
  "insufficient data": {
    badge: "bg-void-700/60 text-starlight-300 ring-1 ring-void-600",
    meter: "bg-void-500",
    text: "text-starlight-300",
    hex: "#3b4a73",
    label: "Insufficient data",
  },
};

const UNKNOWN_BAND = BAND_STYLES["insufficient data"];

export function bandStyle(band: HabitabilityBand | null | undefined): BandStyle {
  if (!band) return UNKNOWN_BAND;
  return BAND_STYLES[band] ?? UNKNOWN_BAND;
}

/** Derive the band from a bare score, for the simulator's live readout. */
export function bandForScore(score: number | null | undefined): HabitabilityBand {
  if (score === null || score === undefined || !Number.isFinite(score)) {
    return "insufficient data";
  }
  if (score >= 80) return "exceptional candidate";
  if (score >= 65) return "promising candidate";
  if (score >= 50) return "plausible candidate";
  if (score >= 30) return "marginal";
  if (score >= 15) return "unlikely";
  return "hostile";
}

const VERDICT_STYLES: Record<HabitabilityVerdict, { text: string; dot: string; label: string }> = {
  ideal: { text: "text-biosphere-300", dot: "bg-biosphere-400", label: "Ideal" },
  favourable: { text: "text-aurora-300", dot: "bg-aurora-400", label: "Favourable" },
  marginal: { text: "text-solar-300", dot: "bg-solar-400", label: "Marginal" },
  poor: { text: "text-ember-300", dot: "bg-ember-400", label: "Poor" },
  hostile: { text: "text-ember-400", dot: "bg-ember-500", label: "Hostile" },
  unknown: { text: "text-starlight-400", dot: "bg-void-500", label: "Not evaluated" },
};

export function verdictStyle(verdict: HabitabilityVerdict | string | null | undefined) {
  if (!verdict) return VERDICT_STYLES.unknown;
  return VERDICT_STYLES[verdict as HabitabilityVerdict] ?? VERDICT_STYLES.unknown;
}

/**
 * Plain-language gloss for the confidence figure.
 *
 * Confidence is the fraction of the scoring weight backed by measured values. It
 * is reported next to the score, never folded into it: a planet can be
 * genuinely Earth-like on every property we can measure while half of those
 * properties are estimates, and conflating the two would hide which is the case.
 */
export function confidenceLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined || !Number.isFinite(confidence)) {
    return "Unknown data coverage";
  }
  if (confidence >= 0.85) return "Well characterised";
  if (confidence >= 0.65) return "Reasonably characterised";
  if (confidence >= 0.45) return "Partially characterised";
  return "Sparse data";
}

export function esiLabel(esi: number | null | undefined): string {
  if (esi === null || esi === undefined || !Number.isFinite(esi)) return "Not computable";
  if (esi >= 0.9) return "Very Earth-like";
  if (esi >= 0.8) return "Earth-like";
  if (esi >= 0.6) return "Broadly Earth-like";
  if (esi >= 0.4) return "Loosely comparable";
  return "Unlike Earth";
}

/**
 * Approximate blackbody colour for a temperature, as a CSS hex string.
 *
 * Used for star glyphs and the temperature legend. The buckets follow the
 * Planckian locus closely enough for a UI; the backend sends a per-star
 * `color_hex` derived the same way, so this is only the fallback for simulated
 * or user-constructed stars.
 */
export function temperatureColor(kelvin: number | null | undefined): string {
  if (!kelvin || !Number.isFinite(kelvin)) return "#9badd4";
  if (kelvin >= 30000) return "#9bb0ff";
  if (kelvin >= 10000) return "#aabfff";
  if (kelvin >= 7500) return "#cad7ff";
  if (kelvin >= 6000) return "#f8f7ff";
  if (kelvin >= 5200) return "#fff4ea";
  if (kelvin >= 3700) return "#ffd2a1";
  if (kelvin >= 2400) return "#ffb56c";
  return "#ff9966";
}

/** Spectral class description, for tooltips and legends. */
export const SPECTRAL_DESCRIPTIONS: Record<string, string> = {
  O: "Blue supergiant — extremely hot, short-lived, hostile to stable biospheres",
  B: "Blue-white — very hot and short-lived",
  A: "White — hot, typically under a billion years old",
  F: "Yellow-white — slightly hotter and shorter-lived than the Sun",
  G: "Yellow dwarf — the Sun's class, long-lived and stable",
  K: "Orange dwarf — cooler than the Sun, long-lived, often considered optimal",
  M: "Red dwarf — cool, extremely long-lived, but prone to flares and close-in tidal locking",
};
