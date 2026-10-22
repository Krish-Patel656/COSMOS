/**
 * Types mirroring the COSMOS API schemas.
 *
 * Kept hand-written rather than generated from OpenAPI so that the comments
 * explaining units and provenance live where the fields are consumed. Unit
 * suffixes are preserved from the API deliberately: `radius_earth` and
 * `radius_jupiter` differ by a factor of 11, and mixing them silently is the
 * most common bug in astronomical code.
 */

export type HabitabilityVerdict =
  | "ideal"
  | "favourable"
  | "marginal"
  | "poor"
  | "hostile"
  | "unknown";

export type HabitabilityBand =
  | "exceptional candidate"
  | "promising candidate"
  | "plausible candidate"
  | "marginal"
  | "unlikely"
  | "hostile"
  | "insufficient data";

export type SurfaceType =
  | "lava"
  | "scorched"
  | "desert"
  | "terrestrial"
  | "ocean"
  | "tundra"
  | "ice"
  | "sub_neptune"
  | "gas_giant"
  | "unknown";

export interface HabitableZone {
  recent_venus_au: number;
  runaway_greenhouse_au: number;
  maximum_greenhouse_au: number;
  early_mars_au: number;
  recent_venus_flux: number;
  runaway_greenhouse_flux: number;
  maximum_greenhouse_flux: number;
  early_mars_flux: number;
  stellar_temp_k: number;
  stellar_luminosity_solar: number;
  /** True when the host star falls outside the model's 2600–7200 K calibration. */
  extrapolated: boolean;
}

export interface HabitabilityFactor {
  key: string;
  label: string;
  /** 0–1, or null when the factor could not be evaluated. */
  score: number | null;
  weight: number;
  value: number | null;
  unit: string;
  verdict: HabitabilityVerdict;
  explanation: string;
  /** True when the input value was modelled rather than measured. */
  estimated: boolean;
}

export interface Habitability {
  score: number | null;
  band: HabitabilityBand;
  /** 0–1. Reported separately from the score so uncertainty is never hidden inside it. */
  confidence: number;
  summary: string;
  size_class: string | null;
  thermal_class: string | null;
  in_conservative_hz: boolean | null;
  in_optimistic_hz: boolean | null;
  habitable_zone: HabitableZone | null;
  factors: HabitabilityFactor[];
  caveats: string[];
}

export interface EsiComponent {
  key: string;
  label: string;
  value: number | null;
  earth_value: number;
  unit: string;
  weight: number;
  similarity: number | null;
  estimated: boolean;
  note: string;
}

export interface Esi {
  overall: number | null;
  interior: number | null;
  surface: number | null;
  data_completeness: number;
  components: EsiComponent[];
}

export interface Appearance {
  surface_type: SurfaceType;
  base_color: string;
  accent_color: string;
  atmosphere_color: string;
  atmosphere_opacity: number;
  cloud_coverage: number;
  roughness: number;
  metalness: number;
  emissive_intensity: number;
  has_rings: boolean;
  banded: boolean;
  /** Which measured properties drove the look, for the UI's disclosure. */
  basis: string[];
  /** Always true — no exoplanet surface has been imaged. */
  is_artistic: boolean;
}

export interface StarMapPoint {
  slug: string;
  name: string;
  /** Equatorial cartesian coordinates in parsecs, Sun at the origin. */
  x_pc: number | null;
  y_pc: number | null;
  z_pc: number | null;
  distance_ly: number | null;
  spectral_class: string | null;
  effective_temp_k: number | null;
  radius_solar: number | null;
  color_hex: string | null;
  planet_count: number;
  best_habitability_score: number | null;
  best_esi: number | null;
  is_solar_system: boolean;
}

export interface StarSummary extends StarMapPoint {
  spectral_type: string | null;
  mass_solar: number | null;
  luminosity_solar: number | null;
  age_gyr: number | null;
  distance_pc: number | null;
  naked_eye_visible: boolean;
  v_magnitude: number | null;
}

export interface StarDetail extends StarSummary {
  aliases: string[] | null;
  right_ascension_deg: number | null;
  declination_deg: number | null;
  metallicity_dex: number | null;
  surface_gravity_log: number | null;
  rotation_period_days: number | null;
  gaia_magnitude: number | null;
  stellar_count: number;
  habitable_zone: HabitableZone | null;
  description: string | null;
}

export interface PlanetSummary {
  slug: string;
  name: string;
  letter: string | null;

  radius_earth: number | null;
  mass_earth: number | null;
  orbital_period_days: number | null;
  semi_major_axis_au: number | null;
  eccentricity: number | null;
  equilibrium_temp_k: number | null;
  insolation_earth: number | null;
  density_g_cm3: number | null;

  esi: number | null;
  habitability_score: number | null;
  habitability_band: HabitabilityBand | null;
  habitability_confidence: number | null;
  in_conservative_hz: boolean | null;
  in_optimistic_hz: boolean | null;
  size_class: string | null;
  thermal_class: string | null;

  discovery_method: string | null;
  discovery_year: number | null;
  is_solar_system: boolean;

  radius_is_estimated: boolean;
  mass_is_estimated: boolean;
  temp_is_estimated: boolean;
  axis_is_estimated: boolean;

  appearance: Appearance | null;
}

export interface PlanetWithStar extends PlanetSummary {
  star: StarSummary;
}

export interface PlanetDetail extends PlanetWithStar {
  radius_jupiter: number | null;
  mass_jupiter: number | null;
  /** True when the mass is M·sin(i) from radial velocity: a lower bound. */
  mass_is_minimum: boolean;
  mass_provenance: string | null;
  inclination_deg: number | null;
  surface_gravity_ms2: number | null;
  escape_velocity_km_s: number | null;
  tidal_locking_likelihood: number | null;
  discovery_facility: string | null;
  is_controversial: boolean;
  reference: string | null;
  last_updated_source: string | null;
  notes: string | null;
  habitability: Habitability | null;
  esi_detail: Esi | null;
}

export interface SystemDetail extends StarDetail {
  planets: PlanetSummary[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export type PlanetPage = Page<PlanetWithStar>;
export type StarPage = Page<StarSummary>;

export interface SearchHit {
  kind: "planet" | "star";
  slug: string;
  name: string;
  subtitle: string;
  system_slug: string;
  habitability_score: number | null;
  esi: number | null;
  distance_ly: number | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  hits: SearchHit[];
}

export interface HighlightSection {
  key: string;
  title: string;
  description: string;
  planets: PlanetWithStar[];
}

export interface HighlightsResponse {
  sections: HighlightSection[];
}

export interface ComparisonRow {
  key: string;
  label: string;
  unit: string;
  values: (number | null)[];
  display: (string | null)[];
  better: "higher" | "lower" | "closer_to_earth" | "none";
  earth_value: number | null;
}

export interface ComparisonResponse {
  planets: PlanetDetail[];
  rows: ComparisonRow[];
  notes: string[];
}

export interface CatalogueStats {
  planet_count: number;
  star_count: number;
  scored_planet_count: number;
  conservative_hz_count: number;
  optimistic_hz_count: number;
  earth_like_count: number;
  nearest_system_ly: number | null;
  farthest_system_ly: number | null;
  discovery_year_range: (number | null)[];
  by_discovery_method: Record<string, number>;
  by_size_class: Record<string, number>;
  by_spectral_class: Record<string, number>;
  by_discovery_year: Record<string, number>;
  /** min/max for each numeric column, so sliders span the real data. */
  ranges: Record<string, { min: number | null; max: number | null }>;
  data_source: string;
  last_ingest: Record<string, unknown> | null;
}

// --- Simulator -------------------------------------------------------------

export interface SimulationRequest {
  radius_earth?: number | null;
  mass_earth?: number | null;
  orbital_period_days?: number | null;
  semi_major_axis_au?: number | null;
  eccentricity?: number | null;
  bond_albedo?: number | null;
  equilibrium_temp_k?: number | null;
  star_effective_temp_k?: number | null;
  star_radius_solar?: number | null;
  star_mass_solar?: number | null;
  star_age_gyr?: number | null;
  baseline_slug?: string | null;
}

export interface DerivedQuantities {
  semi_major_axis_au: number | null;
  orbital_period_days: number | null;
  equilibrium_temp_k: number | null;
  insolation_earth: number | null;
  density_g_cm3: number | null;
  surface_gravity_ms2: number | null;
  surface_gravity_g: number | null;
  escape_velocity_km_s: number | null;
  star_luminosity_solar: number | null;
  star_spectral_class: string | null;
  tidal_locking_likelihood: number | null;
}

export interface SimulationBaseline {
  slug: string;
  name: string;
  habitability_score: number | null;
  esi: number | null;
  delta_habitability: number | null;
  delta_esi: number | null;
}

export interface SimulationResponse {
  habitability: Habitability;
  esi: Esi;
  derived: DerivedQuantities;
  baseline: SimulationBaseline | null;
}

export interface SimulationPreset {
  key: string;
  label: string;
  description: string;
  request: SimulationRequest;
}

// --- Account ---------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  display_name: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type FavoriteTargetType = "planet" | "star";

export interface Favorite {
  id: number;
  target_type: FavoriteTargetType;
  target_slug: string;
  note: string | null;
  created_at: string;
}

export interface CollectionItem {
  id: number;
  target_type: FavoriteTargetType;
  target_slug: string;
  position: number;
  note: string | null;
}

export interface Collection {
  id: number;
  name: string;
  description: string | null;
  is_public: boolean;
  share_token: string | null;
  items: CollectionItem[];
  created_at: string;
  updated_at: string;
}

export interface SavedComparison {
  id: number;
  name: string;
  planet_slugs: string[];
  share_token: string | null;
  created_at: string;
}

// --- Explorer filters ------------------------------------------------------

export type PlanetSortField =
  | "habitability"
  | "esi"
  | "radius"
  | "mass"
  | "temperature"
  | "distance"
  | "period"
  | "insolation"
  | "density"
  | "discovery_year"
  | "name";

export interface PlanetFilters {
  q?: string;
  min_radius?: number;
  max_radius?: number;
  min_mass?: number;
  max_mass?: number;
  min_temp?: number;
  max_temp?: number;
  min_distance_ly?: number;
  max_distance_ly?: number;
  min_period_days?: number;
  max_period_days?: number;
  min_insolation?: number;
  max_insolation?: number;
  min_esi?: number;
  max_esi?: number;
  min_habitability?: number;
  max_habitability?: number;
  min_discovery_year?: number;
  max_discovery_year?: number;
  spectral_class?: string[];
  size_class?: string[];
  thermal_class?: string[];
  discovery_method?: string[];
  habitability_band?: string[];
  in_conservative_hz?: boolean;
  in_optimistic_hz?: boolean;
  has_measured_radius?: boolean;
  has_measured_mass?: boolean;
  has_habitability_score?: boolean;
  exclude_controversial?: boolean;
  include_solar_system?: boolean;
  sort?: PlanetSortField;
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}
