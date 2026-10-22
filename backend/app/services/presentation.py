"""Shaping ORM rows into API responses.

Score breakdowns are stored as JSON on the planet row at ingest time. Re-reading
them here (rather than recomputing) guarantees that a planet's displayed
explanation always matches the score it was ranked by.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from app.models import Planet
from app.schemas.astronomy import (
    AppearanceOut,
    ComparisonRow,
    EsiOut,
    HabitabilityOut,
    PlanetDetail,
    PlanetSummary,
    PlanetWithStar,
    SearchHit,
)
from app.science.appearance import derive_appearance
from app.science.constants import (
    EARTH_DENSITY_G_CM3,
    EARTH_EQUILIBRIUM_TEMP_K,
    EARTH_ESCAPE_VELOCITY_KM_S,
    EARTH_SURFACE_GRAVITY_MS2,
)


def live_appearance(planet: Planet) -> AppearanceOut:
    """Recompute the render recipe from stored measurements.

    Appearance is artistic and cheap to derive. Serving it live means a formula
    change (Jupiter must not grow Saturn's rings) takes effect without re-ingest.
    """
    return AppearanceOut.model_validate(
        derive_appearance(
            planet.radius_earth,
            planet.mass_earth,
            planet.equilibrium_temp_k,
            planet.insolation_earth,
            planet.density_g_cm3,
        ).as_dict()
    )


def to_planet_summary(planet: Planet) -> PlanetSummary:
    summary = PlanetSummary.model_validate(planet)
    summary.appearance = live_appearance(planet)
    return summary


def to_planet_detail(planet: Planet) -> PlanetDetail:
    """Full planet payload, including the stored score breakdowns."""
    detail = PlanetDetail.model_validate(planet)
    detail.appearance = live_appearance(planet)
    if planet.habitability_breakdown:
        detail.habitability = HabitabilityOut.model_validate(planet.habitability_breakdown)
    if planet.esi_breakdown:
        detail.esi_detail = EsiOut.model_validate(planet.esi_breakdown)
    return detail


def to_planet_card(planet: Planet) -> PlanetWithStar:
    card = PlanetWithStar.model_validate(planet)
    card.appearance = live_appearance(planet)
    return card


def planet_subtitle(planet: Planet) -> str:
    """One-line descriptor used in search results and cards."""
    pieces: list[str] = []
    if planet.size_class:
        pieces.append(planet.size_class)
    if planet.star and planet.star.name:
        pieces.append(f"orbiting {planet.star.name}")
    if planet.star and planet.star.distance_ly:
        pieces.append(f"{planet.star.distance_ly:.0f} ly away")
    return " · ".join(pieces) or "Exoplanet"


def star_subtitle(star: Any) -> str:
    pieces: list[str] = []
    if star.spectral_type:
        pieces.append(star.spectral_type)
    elif star.spectral_class:
        pieces.append(f"{star.spectral_class}-type star")
    count = star.planet_count or 0
    pieces.append(f"{count} known planet{'s' if count != 1 else ''}")
    if star.distance_ly:
        pieces.append(f"{star.distance_ly:.0f} ly away")
    return " · ".join(pieces) or "Star"


def to_search_hit_planet(planet: Planet, relevance: float) -> SearchHit:
    return SearchHit(
        kind="planet",
        slug=planet.slug,
        name=planet.name,
        subtitle=planet_subtitle(planet),
        system_slug=planet.star.slug if planet.star else "",
        habitability_score=planet.habitability_score,
        esi=planet.esi,
        distance_ly=planet.star.distance_ly if planet.star else None,
        score=relevance,
    )


def to_search_hit_star(star: Any, relevance: float) -> SearchHit:
    return SearchHit(
        kind="star",
        slug=star.slug,
        name=star.name,
        subtitle=star_subtitle(star),
        system_slug=star.slug,
        habitability_score=star.best_habitability_score,
        esi=star.best_esi,
        distance_ly=star.distance_ly,
        score=relevance,
    )


# --- Comparison -----------------------------------------------------------


def _fmt(value: float | None, digits: int, suffix: str = "") -> str | None:
    if value is None:
        return None
    return f"{value:,.{digits}f}{suffix}"


def _gravity_g(planet: Planet) -> float | None:
    if planet.surface_gravity_ms2 is None:
        return None
    return planet.surface_gravity_ms2 / EARTH_SURFACE_GRAVITY_MS2


# (key, label, unit, accessor, better, earth_value, digits)
_COMPARISON_PROPERTIES: Sequence[
    tuple[str, str, str, Callable[[Planet], float | None], str, float | None, int]
] = (
    ("radius_earth", "Radius", "R⊕", lambda p: p.radius_earth, "closer_to_earth", 1.0, 2),
    ("mass_earth", "Mass", "M⊕", lambda p: p.mass_earth, "closer_to_earth", 1.0, 2),
    (
        "density",
        "Bulk density",
        "g/cm³",
        lambda p: p.density_g_cm3,
        "closer_to_earth",
        EARTH_DENSITY_G_CM3,
        2,
    ),
    ("gravity", "Surface gravity", "g", _gravity_g, "closer_to_earth", 1.0, 2),
    (
        "escape_velocity",
        "Escape velocity",
        "km/s",
        lambda p: p.escape_velocity_km_s,
        "closer_to_earth",
        EARTH_ESCAPE_VELOCITY_KM_S,
        1,
    ),
    (
        "equilibrium_temp",
        "Equilibrium temperature",
        "K",
        lambda p: p.equilibrium_temp_k,
        "closer_to_earth",
        EARTH_EQUILIBRIUM_TEMP_K,
        0,
    ),
    (
        "insolation",
        "Starlight received",
        "S⊕",
        lambda p: p.insolation_earth,
        "closer_to_earth",
        1.0,
        2,
    ),
    (
        "semi_major_axis",
        "Orbital distance",
        "AU",
        lambda p: p.semi_major_axis_au,
        "none",
        1.0,
        3,
    ),
    (
        "orbital_period",
        "Orbital period",
        "days",
        lambda p: p.orbital_period_days,
        "none",
        365.25,
        1,
    ),
    ("eccentricity", "Eccentricity", "e", lambda p: p.eccentricity, "lower", 0.0167, 3),
    ("esi", "Earth Similarity Index", "", lambda p: p.esi, "higher", 1.0, 3),
    (
        "habitability",
        "Habitability score",
        "/100",
        lambda p: p.habitability_score,
        "higher",
        100.0,
        1,
    ),
    (
        "confidence",
        "Score confidence",
        "",
        lambda p: p.habitability_confidence,
        "higher",
        1.0,
        2,
    ),
    (
        "distance",
        "Distance from Earth",
        "ly",
        lambda p: p.star.distance_ly if p.star else None,
        "lower",
        0.0,
        1,
    ),
    (
        "star_temp",
        "Host star temperature",
        "K",
        lambda p: p.star.effective_temp_k if p.star else None,
        "none",
        5772.0,
        0,
    ),
)


def comparison_rows(planets: Sequence[Planet]) -> list[ComparisonRow]:
    """Build the property-by-property comparison table."""
    rows: list[ComparisonRow] = []
    for key, label, unit, accessor, better, earth_value, digits in _COMPARISON_PROPERTIES:
        values = [accessor(planet) for planet in planets]
        if all(value is None for value in values):
            # Hide rows where nothing is known for any selected planet, rather
            # than showing a row of dashes.
            continue
        rows.append(
            ComparisonRow(
                key=key,
                label=label,
                unit=unit,
                values=values,
                display=[_fmt(value, digits) for value in values],
                better=better,
                earth_value=earth_value,
            )
        )
    return rows


def comparison_notes(planets: Sequence[Planet]) -> list[str]:
    """Caveats that apply to the comparison as a whole."""
    notes: list[str] = []

    estimated = [p.name for p in planets if p.mass_is_estimated or p.radius_is_estimated]
    if estimated:
        notes.append(
            "Mass or radius comes from a mass-radius relationship rather than a measurement for "
            + ", ".join(estimated)
            + ", so density, surface gravity and escape velocity for those planets are "
            "statistical expectations rather than observations."
        )

    minimum_mass = [p.name for p in planets if p.mass_is_minimum]
    if minimum_mass:
        notes.append(
            "The mass shown for "
            + ", ".join(minimum_mass)
            + " is a minimum mass from radial velocity; the true mass is higher by an "
            "unknown factor set by the orbital inclination."
        )

    solar = [p.name for p in planets if p.is_solar_system]
    if solar and len(solar) < len(planets):
        notes.append(
            "Solar System planets have measured surface temperatures, whereas exoplanets have "
            "only equilibrium temperatures. The temperature row compares equilibrium values "
            "throughout so the figures are like for like."
        )

    unscored = [p.name for p in planets if p.habitability_score is None]
    if unscored:
        notes.append(
            "No habitability score is available for "
            + ", ".join(unscored)
            + " because neither its temperature nor its habitable-zone position is constrained."
        )

    return notes
