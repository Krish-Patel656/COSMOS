/**
 * Display formatting.
 *
 * Every formatter returns an em dash for missing data rather than "0", "null" or
 * "N/A". Roughly a tenth of catalogue temperatures and half of its masses are
 * absent or modelled, so "unknown" is a first-class state throughout the UI and
 * must never be confusable with a measured zero.
 */

export const EM_DASH = "—";

export function clsx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

function isMissing(value: number | null | undefined): boolean {
  return value === null || value === undefined || !Number.isFinite(value);
}

export function formatNumber(
  value: number | null | undefined,
  digits = 2,
  unit?: string,
): string {
  if (isMissing(value)) return EM_DASH;
  const formatted = (value as number).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatInteger(value: number | null | undefined, unit?: string): string {
  if (isMissing(value)) return EM_DASH;
  const formatted = Math.round(value as number).toLocaleString();
  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatCompact(value: number | null | undefined): string {
  if (isMissing(value)) return EM_DASH;
  return (value as number).toLocaleString(undefined, {
    notation: "compact",
    maximumFractionDigits: 1,
  });
}

/**
 * Format a value that can span many orders of magnitude.
 *
 * Orbital periods run from hours to millennia and insolation from 10⁻⁵ to 10⁴
 * Earth fluxes, so a fixed decimal count would render most of the catalogue as
 * either "0.00" or an unreadable wall of digits.
 */
export function formatScaled(value: number | null | undefined, unit?: string): string {
  if (isMissing(value)) return EM_DASH;
  const magnitude = Math.abs(value as number);
  let digits = 2;
  if (magnitude === 0) digits = 0;
  else if (magnitude < 0.001) digits = 5;
  else if (magnitude < 0.01) digits = 4;
  else if (magnitude < 1) digits = 3;
  else if (magnitude >= 1000) digits = 0;
  return formatNumber(value, digits, unit);
}

export function formatDistance(lightYears: number | null | undefined): string {
  if (isMissing(lightYears)) return EM_DASH;
  const value = lightYears as number;
  if (value === 0) return "Our own system";
  if (value < 10) return `${formatNumber(value, 2)} light years`;
  if (value < 1000) return `${formatNumber(value, 1)} light years`;
  return `${formatCompact(value)} light years`;
}

export function formatPeriod(days: number | null | undefined): string {
  if (isMissing(days)) return EM_DASH;
  const value = days as number;
  if (value < 1) return `${formatNumber(value * 24, 1)} hours`;
  if (value < 400) return `${formatNumber(value, value < 10 ? 2 : 1)} days`;
  return `${formatNumber(value / 365.25, 2)} years`;
}

export function formatTemperature(kelvin: number | null | undefined): string {
  if (isMissing(kelvin)) return EM_DASH;
  const k = kelvin as number;
  return `${Math.round(k)} K (${Math.round(k - 273.15)} °C)`;
}

export function formatPercent(fraction: number | null | undefined, digits = 0): string {
  if (isMissing(fraction)) return EM_DASH;
  return `${((fraction as number) * 100).toFixed(digits)}%`;
}

export function formatScore(score: number | null | undefined): string {
  if (isMissing(score)) return EM_DASH;
  return Math.round(score as number).toString();
}

export function formatEsi(esi: number | null | undefined): string {
  if (isMissing(esi)) return EM_DASH;
  return (esi as number).toFixed(3);
}

export function formatYear(year: number | null | undefined): string {
  if (isMissing(year)) return EM_DASH;
  return String(Math.round(year as number));
}

/** Pluralise a count with its noun: `pluralise(1, "planet")` → "1 planet". */
export function pluralise(count: number, noun: string, plural?: string): string {
  const word = count === 1 ? noun : (plural ?? `${noun}s`);
  return `${count.toLocaleString()} ${word}`;
}

/**
 * Human-readable mass, switching to Jupiter units for giants.
 *
 * 318 Earth masses is a less useful statement than 1 Jupiter mass.
 */
export function formatMass(massEarth: number | null | undefined): string {
  if (isMissing(massEarth)) return EM_DASH;
  const value = massEarth as number;
  if (value >= 50) return `${formatNumber(value / 317.83, 2)} M♃`;
  return `${formatScaled(value)} M⊕`;
}

export function formatRadius(radiusEarth: number | null | undefined): string {
  if (isMissing(radiusEarth)) return EM_DASH;
  const value = radiusEarth as number;
  if (value >= 8) return `${formatNumber(value / 11.209, 2)} R♃`;
  return `${formatNumber(value, 2)} R⊕`;
}

/** Title-case a catalogue token like "radius_valley_world". */
export function humanise(token: string | null | undefined): string {
  if (!token) return EM_DASH;
  const spaced = token.replace(/[_-]+/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
