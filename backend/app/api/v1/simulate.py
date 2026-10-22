"""Habitability simulator.

Runs an arbitrary hypothetical planet through the identical scoring engine used
for the catalogue. That identity matters: if the simulator used a simplified
model, a user could tune a world to score 90 and then be misled about why a real
planet with the same properties scores differently.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Planet
from app.schemas.astronomy import EsiOut, HabitabilityOut
from app.schemas.simulate import (
    DerivedQuantities,
    SimulationBaseline,
    SimulationPreset,
    SimulationPresetList,
    SimulationRequest,
    SimulationResponse,
)
from app.science import astro
from app.science.constants import EARTH_SURFACE_GRAVITY_MS2
from app.science.esi import compute_esi
from app.science.habitability import PlanetInput, compute_habitability

router = APIRouter(prefix="/simulate", tags=["simulate"])


PRESETS: list[SimulationPreset] = [
    SimulationPreset(
        key="earth",
        label="Earth",
        description="The reference world. Every slider starts here.",
        request=SimulationRequest(
            radius_earth=1.0,
            mass_earth=1.0,
            semi_major_axis_au=1.0,
            eccentricity=0.0167,
            star_effective_temp_k=5772.0,
            star_radius_solar=1.0,
            star_mass_solar=1.0,
            star_age_gyr=4.6,
        ),
    ),
    SimulationPreset(
        key="venus",
        label="Venus",
        description=(
            "Nearly Earth's twin, 0.28 AU closer in. Watch the habitable-zone factor collapse "
            "while everything else stays Earth-like."
        ),
        request=SimulationRequest(
            radius_earth=0.949,
            mass_earth=0.815,
            semi_major_axis_au=0.723,
            eccentricity=0.0068,
            star_effective_temp_k=5772.0,
            star_radius_solar=1.0,
            star_mass_solar=1.0,
            star_age_gyr=4.6,
        ),
    ),
    SimulationPreset(
        key="mars",
        label="Mars",
        description=(
            "Inside the habitable zone but only 0.11 Earth masses. Shows how atmospheric "
            "retention alone can sink an otherwise well-placed planet."
        ),
        request=SimulationRequest(
            radius_earth=0.532,
            mass_earth=0.107,
            semi_major_axis_au=1.524,
            eccentricity=0.0934,
            star_effective_temp_k=5772.0,
            star_radius_solar=1.0,
            star_mass_solar=1.0,
            star_age_gyr=4.6,
        ),
    ),
    SimulationPreset(
        key="trappist-1e",
        label="TRAPPIST-1 e",
        description=(
            "An Earth-sized world in the habitable zone of an ultra-cool M8 dwarf, orbiting "
            "every six days. Try raising the star's temperature and watch the orbit become "
            "uninhabitable."
        ),
        request=SimulationRequest(
            radius_earth=0.920,
            mass_earth=0.692,
            semi_major_axis_au=0.02925,
            eccentricity=0.005,
            star_effective_temp_k=2566.0,
            star_radius_solar=0.1192,
            star_mass_solar=0.0898,
            star_age_gyr=7.6,
        ),
        ),
    SimulationPreset(
        key="super-earth",
        label="Habitable super-Earth",
        description=(
            "A 1.5 R⊕, 5 M⊕ world around a K dwarf — the configuration many astronomers "
            "consider the most promising target class of all."
        ),
        request=SimulationRequest(
            radius_earth=1.5,
            mass_earth=5.0,
            semi_major_axis_au=0.55,
            eccentricity=0.02,
            star_effective_temp_k=4500.0,
            star_radius_solar=0.68,
            star_mass_solar=0.72,
            star_age_gyr=6.0,
        ),
    ),
    SimulationPreset(
        key="hot-jupiter",
        label="Hot Jupiter",
        description=(
            "A gas giant three days from its star. Useful for seeing what a thoroughly hostile "
            "world looks like in the breakdown."
        ),
        request=SimulationRequest(
            radius_earth=11.2,
            mass_earth=300.0,
            semi_major_axis_au=0.045,
            eccentricity=0.0,
            star_effective_temp_k=6100.0,
            star_radius_solar=1.2,
            star_mass_solar=1.1,
            star_age_gyr=3.0,
        ),
    ),
]


@router.get("/presets", response_model=SimulationPresetList, summary="Simulator starting points")
async def presets() -> SimulationPresetList:
    return SimulationPresetList(presets=PRESETS)


@router.post("", response_model=SimulationResponse, summary="Score a hypothetical planet")
async def simulate(payload: SimulationRequest, session: SessionDep) -> SimulationResponse:
    """Score an arbitrary world, returning the full breakdown and derived physics.

    Either an orbital distance or an orbital period may be supplied; whichever is
    missing is derived from the other via Kepler's third law, so the UI can offer
    users whichever slider makes more intuitive sense.
    """
    axis = payload.semi_major_axis_au
    period = payload.orbital_period_days

    if axis is None and period is not None:
        axis = astro.semi_major_axis_au(period, payload.star_mass_solar)
    elif period is None and axis is not None and payload.star_mass_solar:
        # Inverse of Kepler's third law: P = sqrt(a^3 / M) in years.
        period = ((axis**3) / payload.star_mass_solar) ** 0.5 * 365.25

    if axis is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "supply either semi_major_axis_au or orbital_period_days together with star_mass_solar",
        )

    luminosity = astro.stellar_luminosity_solar(
        payload.star_radius_solar, payload.star_effective_temp_k
    )
    temperature = payload.equilibrium_temp_k or astro.equilibrium_temperature_k(
        payload.star_effective_temp_k,
        payload.star_radius_solar,
        axis,
        payload.bond_albedo if payload.bond_albedo is not None else 0.3,
    )

    planet_input = PlanetInput(
        radius_earth=payload.radius_earth,
        mass_earth=payload.mass_earth,
        equilibrium_temp_k=temperature,
        orbital_period_days=period,
        semi_major_axis_au=axis,
        eccentricity=payload.eccentricity,
        bond_albedo=payload.bond_albedo,
        star_effective_temp_k=payload.star_effective_temp_k,
        star_radius_solar=payload.star_radius_solar,
        star_mass_solar=payload.star_mass_solar,
        star_luminosity_solar=luminosity,
        star_age_gyr=payload.star_age_gyr,
    )

    habitability = compute_habitability(planet_input)
    esi = compute_esi(payload.radius_earth, payload.mass_earth, temperature)

    gravity = astro.surface_gravity_ms2(payload.mass_earth, payload.radius_earth)
    derived = DerivedQuantities(
        semi_major_axis_au=axis,
        orbital_period_days=period,
        equilibrium_temp_k=temperature,
        insolation_earth=astro.insolation_earth_units(luminosity, axis),
        density_g_cm3=astro.density_g_cm3(payload.mass_earth, payload.radius_earth),
        surface_gravity_ms2=gravity,
        surface_gravity_g=gravity / EARTH_SURFACE_GRAVITY_MS2 if gravity else None,
        escape_velocity_km_s=astro.escape_velocity_km_s(
            payload.mass_earth, payload.radius_earth
        ),
        star_luminosity_solar=luminosity,
        star_spectral_class=astro.classify_spectral_type(payload.star_effective_temp_k),
        tidal_locking_likelihood=astro.transit_tidal_locking_likelihood(
            period, payload.star_mass_solar
        ),
    )

    baseline: SimulationBaseline | None = None
    if payload.baseline_slug:
        planet = (
            await session.execute(
                select(Planet).where(Planet.slug == payload.baseline_slug.lower())
            )
        ).scalars().first()
        if planet is not None:
            baseline = SimulationBaseline(
                slug=planet.slug,
                name=planet.name,
                habitability_score=planet.habitability_score,
                esi=planet.esi,
                delta_habitability=(
                    round(habitability.score - planet.habitability_score, 1)
                    if habitability.score is not None and planet.habitability_score is not None
                    else None
                ),
                delta_esi=(
                    round(esi.overall - planet.esi, 3)
                    if esi.overall is not None and planet.esi is not None
                    else None
                ),
            )

    return SimulationResponse(
        habitability=HabitabilityOut.model_validate(habitability.as_dict()),
        esi=EsiOut.model_validate(esi.as_dict()),
        derived=derived,
        baseline=baseline,
    )
