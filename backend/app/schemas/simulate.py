"""Schemas for the habitability simulator.

The simulator takes an arbitrary hypothetical world and runs it through the same
scoring engine the catalogue uses, so a user dragging a slider sees exactly the
model that produced the real planets' scores — not a simplified imitation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.astronomy import EsiOut, HabitabilityOut


class SimulationRequest(BaseModel):
    """A hypothetical planet. Bounds are generous but finite to keep the
    underlying physical relations inside their domains of validity."""

    radius_earth: float | None = Field(default=1.0, gt=0, le=30)
    mass_earth: float | None = Field(default=1.0, gt=0, le=10000)
    orbital_period_days: float | None = Field(default=None, gt=0, le=4_000_000)
    semi_major_axis_au: float | None = Field(default=1.0, gt=0, le=500)
    eccentricity: float | None = Field(default=0.0, ge=0, lt=1)
    bond_albedo: float | None = Field(default=0.3, ge=0, lt=1)
    equilibrium_temp_k: float | None = Field(
        default=None,
        gt=0,
        le=10000,
        description="Omit to have it computed from the star and orbit",
    )

    star_effective_temp_k: float | None = Field(default=5772.0, gt=0, le=60000)
    star_radius_solar: float | None = Field(default=1.0, gt=0, le=2000)
    star_mass_solar: float | None = Field(default=1.0, gt=0, le=150)
    star_age_gyr: float | None = Field(default=4.6, ge=0, le=14)

    baseline_slug: str | None = Field(
        default=None,
        description="Planet slug to compare the result against, e.g. 'trappist-1-e'",
    )


class DerivedQuantities(BaseModel):
    """Everything the engine computed on the way to a score, exposed so the
    simulator can show cause and effect rather than just a moving number."""

    semi_major_axis_au: float | None
    orbital_period_days: float | None
    equilibrium_temp_k: float | None
    insolation_earth: float | None
    density_g_cm3: float | None
    surface_gravity_ms2: float | None
    surface_gravity_g: float | None
    escape_velocity_km_s: float | None
    star_luminosity_solar: float | None
    star_spectral_class: str | None
    tidal_locking_likelihood: float | None


class SimulationResponse(BaseModel):
    habitability: HabitabilityOut
    esi: EsiOut
    derived: DerivedQuantities
    baseline: SimulationBaseline | None = None


class SimulationBaseline(BaseModel):
    slug: str
    name: str
    habitability_score: float | None
    esi: float | None
    delta_habitability: float | None
    delta_esi: float | None


class SimulationPreset(BaseModel):
    key: str
    label: str
    description: str
    request: SimulationRequest


class SimulationPresetList(BaseModel):
    presets: list[SimulationPreset]


SimulationResponse.model_rebuild()
