/**
 * Pure geometry and scaling for the 3D scenes.
 *
 * Everything here is deliberately framework-free so it can be unit tested: a
 * WebGL canvas cannot run in jsdom, but all of the logic that can actually be
 * *wrong* — scale compression, Kepler's equation, orbit sampling — lives in this
 * file rather than inside a render loop.
 *
 * The central problem these functions solve is dynamic range. A real system
 * spans TRAPPIST-1 b at 0.011 AU to planets beyond 30 AU; drawn to linear scale,
 * the inner planets collapse into the star. Planetary radii span 0.3 to 87 Earth
 * radii, so a gas giant drawn to scale makes an Earth-sized world a sub-pixel
 * dot. Both are therefore compressed, which is a deliberate and documented
 * departure from physical accuracy that the UI labels as "not to scale".
 */

export const SCENE_INNER_RADIUS = 3.2;
export const SCENE_OUTER_RADIUS = 24;

export const MIN_PLANET_RADIUS = 0.16;
export const MAX_PLANET_RADIUS = 1.15;

export const MIN_STAR_RADIUS = 0.9;
export const MAX_STAR_RADIUS = 2.4;

/** Earth radii. The largest planet in the catalogue is ~87 R⊕. */
const RADIUS_REFERENCE = 1;

export interface OrbitScale {
  /** Smallest semi-major axis in the system, in AU. */
  minAu: number;
  /** Largest semi-major axis in the system, in AU. */
  maxAu: number;
  toScene: (au: number) => number;
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}

/**
 * Build a logarithmic mapping from AU to scene units for one system.
 *
 * Log spacing is what makes a compact system like TRAPPIST-1 (seven planets
 * inside 0.07 AU) and a sprawling one like the Solar System both legible with the
 * same camera. A system whose planets all share one orbital distance, or that has
 * a single planet, degenerates gracefully to a mid-range ring.
 */
export function createOrbitScale(semiMajorAxesAu: readonly (number | null)[]): OrbitScale {
  const axes = semiMajorAxesAu.filter(
    (au): au is number => typeof au === "number" && Number.isFinite(au) && au > 0,
  );

  if (axes.length === 0) {
    const mid = (SCENE_INNER_RADIUS + SCENE_OUTER_RADIUS) / 2;
    return { minAu: 1, maxAu: 1, toScene: () => mid };
  }

  const minAu = Math.min(...axes);
  const maxAu = Math.max(...axes);

  if (axes.length === 1 || maxAu / minAu < 1.02) {
    const mid = (SCENE_INNER_RADIUS + SCENE_OUTER_RADIUS) / 2;
    return { minAu, maxAu, toScene: () => mid };
  }

  const logMin = Math.log10(minAu);
  const logMax = Math.log10(maxAu);
  const span = logMax - logMin;

  return {
    minAu,
    maxAu,
    toScene(au: number) {
      if (!Number.isFinite(au) || au <= 0) return SCENE_INNER_RADIUS;
      const t = (Math.log10(au) - logMin) / span;
      // Allow a little overshoot so habitable-zone rings that fall outside the
      // planets' own range still render in a sensible place instead of clamping
      // onto the innermost orbit.
      return (
        SCENE_INNER_RADIUS +
        clamp(t, -0.35, 1.35) * (SCENE_OUTER_RADIUS - SCENE_INNER_RADIUS)
      );
    },
  };
}

/**
 * Compress planetary radius for display.
 *
 * A cube root means the rendered volume is proportional to the real radius,
 * which keeps a Jupiter visibly far larger than an Earth without letting it
 * dominate the frame by a factor of eleven.
 */
export function planetDisplayRadius(radiusEarth: number | null | undefined): number {
  if (!radiusEarth || !Number.isFinite(radiusEarth) || radiusEarth <= 0) {
    return MIN_PLANET_RADIUS * 1.4;
  }
  const scaled = 0.33 * Math.cbrt(radiusEarth / RADIUS_REFERENCE);
  return clamp(scaled, MIN_PLANET_RADIUS, MAX_PLANET_RADIUS);
}

/** Compress stellar radius the same way. Stars range from 0.1 to 1000+ R☉. */
export function starDisplayRadius(radiusSolar: number | null | undefined): number {
  if (!radiusSolar || !Number.isFinite(radiusSolar) || radiusSolar <= 0) {
    return MIN_STAR_RADIUS * 1.2;
  }
  const scaled = 1.25 * Math.cbrt(radiusSolar);
  return clamp(scaled, MIN_STAR_RADIUS, MAX_STAR_RADIUS);
}

/**
 * Solve Kepler's equation M = E - e·sin(E) for the eccentric anomaly.
 *
 * Newton-Raphson converges in a handful of iterations for the eccentricities
 * found in the catalogue (e < 0.95). Doing this properly rather than sweeping the
 * true anomaly linearly is what makes an eccentric orbit visibly speed up at
 * periapsis, which is the whole point of showing eccentricity at all.
 */
export function solveEccentricAnomaly(
  meanAnomaly: number,
  eccentricity: number,
  tolerance = 1e-6,
  maxIterations = 12,
): number {
  const e = clamp(eccentricity, 0, 0.99);
  let E = meanAnomaly;
  for (let i = 0; i < maxIterations; i += 1) {
    const delta = E - e * Math.sin(E) - meanAnomaly;
    if (Math.abs(delta) < tolerance) break;
    const derivative = 1 - e * Math.cos(E);
    // Guard against a vanishing derivative at extreme eccentricity.
    E -= delta / (Math.abs(derivative) < 1e-9 ? 1e-9 : derivative);
  }
  return E;
}

export interface OrbitPosition {
  x: number;
  z: number;
  /** True anomaly in radians, useful for orienting a tidally locked planet. */
  trueAnomaly: number;
  /** Current distance from the focus, in the same units as `semiMajorAxis`. */
  radius: number;
}

/**
 * Position on an elliptical orbit at a given phase.
 *
 * `phase` is the mean anomaly normalised to [0, 1), so callers can drive it from
 * elapsed time divided by the orbital period. The star sits at the focus, not the
 * centre, which is what makes an eccentric orbit look correct.
 */
export function orbitPosition(
  semiMajorAxis: number,
  eccentricity: number,
  phase: number,
): OrbitPosition {
  const e = clamp(eccentricity ?? 0, 0, 0.95);
  const meanAnomaly = phase * Math.PI * 2;
  const E = solveEccentricAnomaly(meanAnomaly, e);

  // Position in the orbital plane relative to the ellipse centre, then shifted so
  // the focus is at the origin.
  const semiMinor = semiMajorAxis * Math.sqrt(1 - e * e);
  const x = semiMajorAxis * (Math.cos(E) - e);
  const z = semiMinor * Math.sin(E);

  const radius = Math.hypot(x, z);
  const trueAnomaly = Math.atan2(z, x);
  return { x, z, trueAnomaly, radius };
}

/**
 * Sample an elliptical orbit into a closed polyline for rendering.
 *
 * Points are evenly spaced in eccentric anomaly rather than true anomaly, which
 * distributes vertices more densely near periapsis where the curvature is
 * highest — fewer points for the same visual smoothness.
 */
export function sampleOrbit(
  semiMajorAxis: number,
  eccentricity: number,
  segments = 128,
): [number, number, number][] {
  const e = clamp(eccentricity ?? 0, 0, 0.95);
  const semiMinor = semiMajorAxis * Math.sqrt(1 - e * e);
  const points: [number, number, number][] = [];

  for (let i = 0; i <= segments; i += 1) {
    const E = (i / segments) * Math.PI * 2;
    points.push([semiMajorAxis * (Math.cos(E) - e), 0, semiMinor * Math.sin(E)]);
  }
  return points;
}

/**
 * Animation speed for a planet, in orbits per second of wall-clock time.
 *
 * Real periods span 0.09 days to 400,000 days — a factor of four million — so
 * true relative speeds would leave outer planets apparently frozen. Compressing
 * logarithmically preserves the *ordering* (inner planets visibly faster) while
 * keeping everything in motion. Returns 0 when the period is unknown so the
 * planet holds a static position rather than defaulting to some arbitrary speed.
 */
export function orbitSpeed(periodDays: number | null | undefined): number {
  if (!periodDays || !Number.isFinite(periodDays) || periodDays <= 0) return 0;
  const compressed = Math.log10(periodDays + 1) + 1;
  return clamp(0.12 / compressed, 0.004, 0.2);
}

/**
 * Map parsecs to scene units for the stellar map.
 *
 * A square root keeps the nearby stars — the ones with characterised planets and
 * therefore the ones worth clicking — spread out, while still fitting distant
 * systems inside the same frustum.
 */
export function mapScale(distancePc: number, spread = 1.6): number {
  if (!Number.isFinite(distancePc) || distancePc <= 0) return 0;
  return Math.sqrt(distancePc) * spread;
}

export interface MapPosition {
  x: number;
  y: number;
  z: number;
}

/**
 * Rescale a star's cartesian position for the map.
 *
 * The direction is preserved exactly — constellations stay recognisable — and
 * only the radial distance is compressed.
 */
export function mapPosition(
  xPc: number | null,
  yPc: number | null,
  zPc: number | null,
  spread = 1.6,
): MapPosition | null {
  if (xPc === null || yPc === null || zPc === null) return null;
  if (!Number.isFinite(xPc) || !Number.isFinite(yPc) || !Number.isFinite(zPc)) return null;

  const distance = Math.hypot(xPc, yPc, zPc);
  if (distance === 0) return { x: 0, y: 0, z: 0 };

  const scaled = mapScale(distance, spread);
  const factor = scaled / distance;
  // Three.js is Y-up while the equatorial frame is Z-up (towards the north
  // celestial pole), so the two vertical axes are swapped here.
  return { x: xPc * factor, y: zPc * factor, z: yPc * factor };
}

/** Point size for a star in the map, driven by its radius and brightness. */
export function mapPointSize(
  radiusSolar: number | null,
  planetCount: number,
  isSolarSystem: boolean,
): number {
  if (isSolarSystem) return 0.42;
  const base = radiusSolar && radiusSolar > 0 ? 0.1 * Math.cbrt(radiusSolar) + 0.1 : 0.14;
  // Systems with more known planets are more interesting to click, so they get a
  // small size bonus. This is a UI affordance, not a physical property.
  return clamp(base + Math.min(planetCount, 8) * 0.012, 0.1, 0.34);
}
