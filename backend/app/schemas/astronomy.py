"""Response schemas for stars, planets and systems.

Three levels of detail exist for deliberate reasons:

* ``StarMapPoint`` — the absolute minimum for plotting thousands of stars in the
  3D map. Sending full star records instead would multiply the payload by ~20.
* ``PlanetSummary`` / ``StarSummary`` — list and card views.
* ``PlanetDetail`` / ``SystemDetail`` — everything, including the score
  breakdowns that justify the numbers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Score breakdowns -----------------------------------------------------


class HabitableZoneOut(BaseModel):
    recent_venus_au: float = Field(description="Optimistic inner edge (empirical, Venus analogy)")
    runaway_greenhouse_au: float = Field(description="Conservative inner edge (model)")
    maximum_greenhouse_au: float = Field(description="Conservative outer edge (model)")
    early_mars_au: float = Field(description="Optimistic outer edge (empirical, Mars analogy)")
    recent_venus_flux: float
    runaway_greenhouse_flux: float
    maximum_greenhouse_flux: float
    early_mars_flux: float
    stellar_temp_k: float
    stellar_luminosity_solar: float
    extrapolated: bool = Field(
        description="True when the host star falls outside the model's 2600-7200 K calibration"
    )


class HabitabilityFactorOut(BaseModel):
    key: str
    label: str
    score: float | None = Field(description="0-1, or null when not evaluable")
    weight: float
    value: float | None
    unit: str
    verdict: str
    explanation: str
    estimated: bool


class HabitabilityOut(BaseModel):
    score: float | None
    band: str
    confidence: float
    summary: str
    size_class: str | None
    thermal_class: str | None
    in_conservative_hz: bool | None
    in_optimistic_hz: bool | None
    habitable_zone: HabitableZoneOut | None
    factors: list[HabitabilityFactorOut]
    caveats: list[str]


class EsiComponentOut(BaseModel):
    key: str
    label: str
    value: float | None
    earth_value: float
    unit: str
    weight: float
    similarity: float | None
    estimated: bool
    note: str


class EsiOut(BaseModel):
    overall: float | None
    interior: float | None
    surface: float | None
    data_completeness: float
    components: list[EsiComponentOut]


class AppearanceOut(BaseModel):
    surface_type: str
    base_color: str
    accent_color: str
    atmosphere_color: str
    atmosphere_opacity: float
    cloud_coverage: float
    roughness: float
    metalness: float
    emissive_intensity: float
    has_rings: bool
    banded: bool
    basis: list[str]
    is_artistic: bool


# --- Stars ----------------------------------------------------------------


class StarMapPoint(ORMModel):
    """Minimal star record for the 3D stellar map."""

    slug: str
    name: str
    x_pc: float | None
    y_pc: float | None
    z_pc: float | None
    distance_ly: float | None
    spectral_class: str | None
    effective_temp_k: float | None
    radius_solar: float | None
    color_hex: str | None
    planet_count: int
    best_habitability_score: float | None
    best_esi: float | None
    is_solar_system: bool


class StarSummary(StarMapPoint):
    spectral_type: str | None
    mass_solar: float | None
    luminosity_solar: float | None
    age_gyr: float | None
    distance_pc: float | None
    naked_eye_visible: bool
    v_magnitude: float | None


class StarDetail(StarSummary):
    aliases: list[str] | None
    right_ascension_deg: float | None
    declination_deg: float | None
    metallicity_dex: float | None
    surface_gravity_log: float | None
    rotation_period_days: float | None
    gaia_magnitude: float | None
    stellar_count: int
    habitable_zone: HabitableZoneOut | None
    description: str | None


# --- Planets --------------------------------------------------------------


class PlanetSummary(ORMModel):
    slug: str
    name: str
    letter: str | None

    radius_earth: float | None
    mass_earth: float | None
    orbital_period_days: float | None
    semi_major_axis_au: float | None
    eccentricity: float | None
    equilibrium_temp_k: float | None
    insolation_earth: float | None
    density_g_cm3: float | None

    esi: float | None
    habitability_score: float | None
    habitability_band: str | None
    habitability_confidence: float | None
    in_conservative_hz: bool | None
    in_optimistic_hz: bool | None
    size_class: str | None
    thermal_class: str | None

    discovery_method: str | None
    discovery_year: int | None
    is_solar_system: bool

    radius_is_estimated: bool
    mass_is_estimated: bool
    temp_is_estimated: bool
    axis_is_estimated: bool

    appearance: AppearanceOut | None


class PlanetWithStar(PlanetSummary):
    """Planet plus enough host context for a standalone card or list row."""

    star: StarSummary


class PlanetDetail(PlanetWithStar):
    radius_jupiter: float | None
    mass_jupiter: float | None
    mass_is_minimum: bool
    mass_provenance: str | None
    inclination_deg: float | None
    surface_gravity_ms2: float | None
    escape_velocity_km_s: float | None
    tidal_locking_likelihood: float | None
    discovery_facility: str | None
    is_controversial: bool
    reference: str | None
    last_updated_source: str | None
    notes: str | None

    habitability: HabitabilityOut | None = Field(
        default=None, description="Full factor-by-factor habitability breakdown"
    )
    esi_detail: EsiOut | None = Field(
        default=None, description="Per-property Earth Similarity Index breakdown"
    )


class SystemDetail(StarDetail):
    """A star with all of its planets — the payload the 3D system scene consumes."""

    planets: list[PlanetSummary]


# --- Collections of planets ----------------------------------------------


class PlanetPage(BaseModel):
    items: list[PlanetWithStar]
    total: int
    limit: int
    offset: int
    has_more: bool


class StarPage(BaseModel):
    items: list[StarSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class SearchHit(BaseModel):
    kind: str = Field(description="'planet' or 'star'")
    slug: str
    name: str
    subtitle: str
    system_slug: str
    habitability_score: float | None = None
    esi: float | None = None
    distance_ly: float | None = None
    score: float = Field(description="Relevance, higher is better")


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class HighlightSection(BaseModel):
    key: str
    title: str
    description: str
    planets: list[PlanetWithStar]


class HighlightsResponse(BaseModel):
    sections: list[HighlightSection]


class ComparisonRow(BaseModel):
    """One property compared across the selected planets."""

    key: str
    label: str
    unit: str
    values: list[float | None]
    display: list[str | None]
    better: str = Field(description="'higher', 'lower', 'closer_to_earth' or 'none'")
    earth_value: float | None = None


class ComparisonResponse(BaseModel):
    planets: list[PlanetDetail]
    rows: list[ComparisonRow]
    notes: list[str]


class CatalogueStats(BaseModel):
    planet_count: int
    star_count: int
    scored_planet_count: int
    conservative_hz_count: int
    optimistic_hz_count: int
    earth_like_count: int = Field(description="Planets with ESI >= 0.8")
    nearest_system_ly: float | None
    farthest_system_ly: float | None
    discovery_year_range: list[int | None]
    by_discovery_method: dict[str, int]
    by_size_class: dict[str, int]
    by_spectral_class: dict[str, int]
    by_discovery_year: dict[str, int]
    ranges: dict[str, dict[str, float | None]] = Field(
        description="min/max for each numeric filter, so the UI can build sliders"
    )
    data_source: str
    last_ingest: dict[str, Any] | None
