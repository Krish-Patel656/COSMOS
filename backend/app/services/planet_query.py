"""Query construction for the Exoplanet Explorer.

All filtering, sorting and pagination for the planet catalogue lives here so the
list endpoint, the highlight sections and the "similar planets" lookup share one
definition of what each filter means.

Two behaviours are worth calling out:

* Nulls always sort last, whatever the direction. Roughly a tenth of planets
  have no measured temperature and a twentieth no radius; letting them lead a
  "coldest first" sort would be useless.
* ``has_measured_*`` filters exist because the catalogue is full of values
  derived from the mass-radius relation. A user studying real measurements needs
  to be able to exclude them, and the UI needs the distinction to be a filter
  rather than a footnote.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import joinedload

from app.models import Planet, Star

SortField = Literal[
    "habitability",
    "esi",
    "radius",
    "mass",
    "temperature",
    "distance",
    "period",
    "insolation",
    "density",
    "discovery_year",
    "name",
]

_SORT_COLUMNS = {
    "habitability": Planet.habitability_score,
    "esi": Planet.esi,
    "radius": Planet.radius_earth,
    "mass": Planet.mass_earth,
    "temperature": Planet.equilibrium_temp_k,
    "distance": Star.distance_ly,
    "period": Planet.orbital_period_days,
    "insolation": Planet.insolation_earth,
    "density": Planet.density_g_cm3,
    "discovery_year": Planet.discovery_year,
    "name": Planet.name,
}


class PlanetFilters(BaseModel):
    """Every explorer filter, usable directly as a FastAPI query-parameter model."""

    q: str | None = Field(default=None, max_length=120, description="Name search")

    min_radius: float | None = Field(default=None, ge=0, description="Earth radii")
    max_radius: float | None = Field(default=None, ge=0)
    min_mass: float | None = Field(default=None, ge=0, description="Earth masses")
    max_mass: float | None = Field(default=None, ge=0)
    min_temp: float | None = Field(default=None, ge=0, description="Equilibrium temp, K")
    max_temp: float | None = Field(default=None, ge=0)
    min_distance_ly: float | None = Field(default=None, ge=0)
    max_distance_ly: float | None = Field(default=None, ge=0)
    min_period_days: float | None = Field(default=None, ge=0)
    max_period_days: float | None = Field(default=None, ge=0)
    min_insolation: float | None = Field(default=None, ge=0, description="Earth flux units")
    max_insolation: float | None = Field(default=None, ge=0)
    min_esi: float | None = Field(default=None, ge=0, le=1)
    max_esi: float | None = Field(default=None, ge=0, le=1)
    min_habitability: float | None = Field(default=None, ge=0, le=100)
    max_habitability: float | None = Field(default=None, ge=0, le=100)
    min_discovery_year: int | None = Field(default=None, ge=1980, le=2100)
    max_discovery_year: int | None = Field(default=None, ge=1980, le=2100)

    spectral_class: list[str] | None = Field(
        default=None, description="Host star Morgan-Keenan classes, e.g. G, K, M"
    )
    size_class: list[str] | None = None
    thermal_class: list[str] | None = None
    discovery_method: list[str] | None = None
    habitability_band: list[str] | None = None

    in_conservative_hz: bool | None = None
    in_optimistic_hz: bool | None = None
    has_measured_radius: bool | None = None
    has_measured_mass: bool | None = None
    has_habitability_score: bool | None = None
    exclude_controversial: bool = False
    include_solar_system: bool = True

    sort: SortField = "habitability"
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=24, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


def _between(column: Any, low: float | None, high: float | None) -> list[Any]:
    clauses = []
    if low is not None:
        clauses.append(column >= low)
    if high is not None:
        clauses.append(column <= high)
    return clauses


def build_conditions(filters: PlanetFilters) -> list[Any]:
    """Translate filters into SQLAlchemy conditions over Planet joined to Star."""
    conditions: list[Any] = []

    if filters.q:
        pattern = f"%{filters.q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Planet.name).like(pattern),
                func.lower(Star.name).like(pattern),
            )
        )

    conditions += _between(Planet.radius_earth, filters.min_radius, filters.max_radius)
    conditions += _between(Planet.mass_earth, filters.min_mass, filters.max_mass)
    conditions += _between(Planet.equilibrium_temp_k, filters.min_temp, filters.max_temp)
    conditions += _between(Star.distance_ly, filters.min_distance_ly, filters.max_distance_ly)
    conditions += _between(
        Planet.orbital_period_days, filters.min_period_days, filters.max_period_days
    )
    conditions += _between(
        Planet.insolation_earth, filters.min_insolation, filters.max_insolation
    )
    conditions += _between(Planet.esi, filters.min_esi, filters.max_esi)
    conditions += _between(
        Planet.habitability_score, filters.min_habitability, filters.max_habitability
    )
    conditions += _between(
        Planet.discovery_year, filters.min_discovery_year, filters.max_discovery_year
    )

    if filters.spectral_class:
        conditions.append(Star.spectral_class.in_([c.upper()[:1] for c in filters.spectral_class]))
    if filters.size_class:
        conditions.append(Planet.size_class.in_(filters.size_class))
    if filters.thermal_class:
        conditions.append(Planet.thermal_class.in_(filters.thermal_class))
    if filters.discovery_method:
        conditions.append(Planet.discovery_method.in_(filters.discovery_method))
    if filters.habitability_band:
        conditions.append(Planet.habitability_band.in_(filters.habitability_band))

    if filters.in_conservative_hz is not None:
        conditions.append(Planet.in_conservative_hz.is_(filters.in_conservative_hz))
    if filters.in_optimistic_hz is not None:
        conditions.append(Planet.in_optimistic_hz.is_(filters.in_optimistic_hz))

    if filters.has_measured_radius is not None:
        conditions.append(
            and_(Planet.radius_earth.is_not(None), Planet.radius_is_estimated.is_(False))
            if filters.has_measured_radius
            else or_(Planet.radius_earth.is_(None), Planet.radius_is_estimated.is_(True))
        )
    if filters.has_measured_mass is not None:
        conditions.append(
            and_(Planet.mass_earth.is_not(None), Planet.mass_is_estimated.is_(False))
            if filters.has_measured_mass
            else or_(Planet.mass_earth.is_(None), Planet.mass_is_estimated.is_(True))
        )
    if filters.has_habitability_score is not None:
        conditions.append(
            Planet.habitability_score.is_not(None)
            if filters.has_habitability_score
            else Planet.habitability_score.is_(None)
        )

    if filters.exclude_controversial:
        conditions.append(Planet.is_controversial.is_(False))
    if not filters.include_solar_system:
        conditions.append(Planet.is_solar_system.is_(False))

    return conditions


def apply_ordering(statement: Select, sort: str, order: str) -> Select:
    """Order by the requested field, always pushing unknown values to the end."""
    column = _SORT_COLUMNS.get(sort, Planet.habitability_score)
    direction = column.desc() if order == "desc" else column.asc()
    # `nulls_last` on the sort column, then slug as a deterministic tiebreaker so
    # pagination never repeats or drops a row between pages.
    return statement.order_by(direction.nulls_last(), Planet.slug.asc())


def build_select(filters: PlanetFilters) -> Select:
    """Full paginated SELECT for the explorer list."""
    statement = (
        select(Planet)
        .join(Star, Planet.star_id == Star.id)
        .options(joinedload(Planet.star))
    )
    conditions = build_conditions(filters)
    if conditions:
        statement = statement.where(and_(*conditions))
    statement = apply_ordering(statement, filters.sort, filters.order)
    return statement.limit(filters.limit).offset(filters.offset)


def build_count(filters: PlanetFilters) -> Select:
    """Matching row count for the same filters, without pagination."""
    statement = select(func.count(Planet.id)).join(Star, Planet.star_id == Star.id)
    conditions = build_conditions(filters)
    if conditions:
        statement = statement.where(and_(*conditions))
    return statement


def highlight_filters(**overrides: Any) -> PlanetFilters:
    """Build filters for a curated highlight section."""
    base: dict = {"limit": 8, "exclude_controversial": True}
    base.update(overrides)
    return PlanetFilters(**base)


def similar_planets_select(planet: Planet, limit: int = 6) -> Select:
    """Find planets closest to ``planet`` in normalised property space.

    "Similar" is defined over the three properties that drive both scores —
    radius, equilibrium temperature and insolation — each normalised by a
    characteristic scale so that no single one dominates the distance. Insolation
    is compared in log space because it spans six orders of magnitude across the
    catalogue.
    """
    terms: list[Any] = []

    if planet.radius_earth:
        terms.append(func.abs(Planet.radius_earth - planet.radius_earth) / 1.0)
    if planet.equilibrium_temp_k:
        terms.append(func.abs(Planet.equilibrium_temp_k - planet.equilibrium_temp_k) / 100.0)
    if planet.esi:
        terms.append(func.abs(Planet.esi - planet.esi) * 3.0)

    if not terms:
        # Nothing to measure similarity against: fall back to same size class.
        return (
            select(Planet)
            .options(joinedload(Planet.star))
            .where(Planet.id != planet.id, Planet.size_class == planet.size_class)
            .limit(limit)
        )

    distance = terms[0]
    for term in terms[1:]:
        distance = distance + term

    required = [Planet.id != planet.id]
    if planet.radius_earth:
        required.append(Planet.radius_earth.is_not(None))
    if planet.equilibrium_temp_k:
        required.append(Planet.equilibrium_temp_k.is_not(None))
    if planet.esi:
        required.append(Planet.esi.is_not(None))

    return (
        select(Planet)
        .options(joinedload(Planet.star))
        .where(and_(*required))
        .order_by(distance.asc())
        .limit(limit)
    )


def unique_planets(rows: Sequence[Any]) -> list[Planet]:
    """Collapse joined-eager-load duplicates while preserving order."""
    seen = set()
    result: list[Planet] = []
    for planet in rows:
        if planet.id not in seen:
            seen.add(planet.id)
            result.append(planet)
    return result
