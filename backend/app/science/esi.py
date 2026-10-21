"""Earth Similarity Index.

Implements the ESI of Schulze-Makuch et al. (2011, Astrobiology 11:1041). The
index asks a deliberately narrow question: *how close are this planet's bulk
physical properties to Earth's?* It is not a habitability measure. A hot Jupiter
and a frozen rock can both score poorly for completely different reasons, and a
planet can score highly while being utterly uninhabitable, because the index
knows nothing about atmospheres, chemistry or stellar environment.

Each property contributes a similarity term

    s_i = (1 - |x_i - x_earth| / (x_i + x_earth)) ** (w_i / n)

and terms are multiplied within two groups:

* *interior* ESI from radius and bulk density
* *surface*  ESI from escape velocity and temperature

The global index is the geometric mean of the two groups.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.science import astro
from app.science.constants import (
    EARTH_DENSITY_G_CM3,
    EARTH_EQUILIBRIUM_TEMP_K,
    EARTH_ESCAPE_VELOCITY_KM_S,
    EARTH_SURFACE_TEMP_K,
)

__all__ = ["EsiComponent", "EsiResult", "compute_esi", "similarity_term"]


@dataclass(frozen=True)
class EsiComponent:
    """One weighted property comparison inside the index."""

    key: str
    label: str
    value: float | None
    earth_value: float
    unit: str
    weight: float
    similarity: float | None
    estimated: bool
    note: str

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "earth_value": self.earth_value,
            "unit": self.unit,
            "weight": self.weight,
            "similarity": self.similarity,
            "estimated": self.estimated,
            "note": self.note,
        }


@dataclass(frozen=True)
class EsiResult:
    overall: float | None
    interior: float | None
    surface: float | None
    components: list[EsiComponent] = field(default_factory=list)
    data_completeness: float = 0.0
    """Fraction of the four input properties backed by catalogue measurements
    rather than by a mass-radius estimate."""

    def as_dict(self) -> dict:
        return {
            "overall": self.overall,
            "interior": self.interior,
            "surface": self.surface,
            "data_completeness": self.data_completeness,
            "components": [component.as_dict() for component in self.components],
        }


# Weight exponents from Schulze-Makuch et al. (2011), Table 2.
_WEIGHTS = {
    "radius": 0.57,
    "density": 1.07,
    "escape_velocity": 0.70,
    "temperature": 5.58,
}


def similarity_term(value: float, reference: float, weight: float, n_terms: int) -> float:
    """Single ESI similarity factor, already raised to its weight exponent."""
    denominator = value + reference
    if denominator == 0:
        return 0.0
    base = 1.0 - abs(value - reference) / denominator
    base = max(base, 0.0)
    return base ** (weight / n_terms)


def _group(components: list[EsiComponent]) -> float | None:
    """Multiply the similarity terms of one ESI group."""
    usable = [c for c in components if c.similarity is not None]
    if len(usable) != len(components):
        # A missing property makes the group's product meaningless rather than
        # merely smaller, so we decline to report it.
        return None
    product = 1.0
    for component in usable:
        product *= component.similarity  # type: ignore[operator]
    return product


def compute_esi(
    radius_earth: float | None,
    mass_earth: float | None,
    temperature_k: float | None,
    temperature_is_equilibrium: bool = True,
    mass_is_estimated: bool = False,
    radius_is_estimated: bool = False,
) -> EsiResult:
    """Compute the Earth Similarity Index.

    ``temperature_is_equilibrium`` selects the Earth reference: 255 K when the
    supplied temperature is an equilibrium temperature (the usual case for
    exoplanets) and 288 K when it is a true surface temperature. Mixing the two
    would systematically flatter cold planets by about 30 K.

    ``mass_is_estimated`` and ``radius_is_estimated`` let the caller declare that
    a supplied value is itself modelled rather than observed. This matters: the
    NASA archive populates roughly half of its masses from its own mass-radius
    relationship, and without this flag those would be reported as measurements.
    """
    measured_radius = radius_earth if radius_earth and radius_earth > 0 else None
    measured_mass = mass_earth if mass_earth and mass_earth > 0 else None

    radius_estimated = (measured_radius is None and measured_mass is not None) or (
        measured_radius is not None and radius_is_estimated
    )
    mass_estimated = (measured_mass is None and measured_radius is not None) or (
        measured_mass is not None and mass_is_estimated
    )

    effective_radius = measured_radius or astro.radius_from_mass_earth_units(measured_mass)
    effective_mass = measured_mass or astro.mass_from_radius_earth_units(measured_radius)

    density = astro.density_g_cm3(effective_mass, effective_radius)
    escape_velocity = astro.escape_velocity_km_s(effective_mass, effective_radius)

    earth_temp = EARTH_EQUILIBRIUM_TEMP_K if temperature_is_equilibrium else EARTH_SURFACE_TEMP_K
    temp_note = (
        "Compared against Earth's 255 K equilibrium temperature, not its 288 K "
        "surface temperature, because the catalogue value excludes greenhouse warming."
        if temperature_is_equilibrium
        else "Compared against Earth's 288 K mean surface temperature."
    )
    derived_note = "Derived from the mass-radius relation, not measured." 

    interior = [
        EsiComponent(
            key="radius",
            label="Radius",
            value=effective_radius,
            earth_value=1.0,
            unit="R⊕",
            weight=_WEIGHTS["radius"],
            similarity=(
                similarity_term(effective_radius, 1.0, _WEIGHTS["radius"], 2)
                if effective_radius
                else None
            ),
            estimated=radius_estimated,
            note=derived_note if radius_estimated else "Measured planetary radius.",
        ),
        EsiComponent(
            key="density",
            label="Bulk density",
            value=density,
            earth_value=EARTH_DENSITY_G_CM3,
            unit="g/cm³",
            weight=_WEIGHTS["density"],
            similarity=(
                similarity_term(density, EARTH_DENSITY_G_CM3, _WEIGHTS["density"], 2)
                if density
                else None
            ),
            estimated=radius_estimated or mass_estimated,
            note=(
                derived_note
                if (radius_estimated or mass_estimated)
                else "Computed from measured mass and radius."
            ),
        ),
    ]

    surface = [
        EsiComponent(
            key="escape_velocity",
            label="Escape velocity",
            value=escape_velocity,
            earth_value=EARTH_ESCAPE_VELOCITY_KM_S,
            unit="km/s",
            weight=_WEIGHTS["escape_velocity"],
            similarity=(
                similarity_term(
                    escape_velocity, EARTH_ESCAPE_VELOCITY_KM_S, _WEIGHTS["escape_velocity"], 2
                )
                if escape_velocity
                else None
            ),
            estimated=radius_estimated or mass_estimated,
            note=(
                derived_note
                if (radius_estimated or mass_estimated)
                else "Computed from measured mass and radius."
            ),
        ),
        EsiComponent(
            key="temperature",
            label="Temperature",
            value=temperature_k,
            earth_value=earth_temp,
            unit="K",
            weight=_WEIGHTS["temperature"],
            similarity=(
                similarity_term(temperature_k, earth_temp, _WEIGHTS["temperature"], 2)
                if temperature_k and temperature_k > 0
                else None
            ),
            estimated=False,
            note=temp_note,
        ),
    ]

    interior_esi = _group(interior)
    surface_esi = _group(surface)
    overall = (
        (interior_esi * surface_esi) ** 0.5
        if interior_esi is not None and surface_esi is not None
        else None
    )

    measured_inputs = sum(
        1
        for present in (
            measured_radius is not None and not radius_estimated,
            measured_mass is not None and not mass_estimated,
            temperature_k is not None and temperature_k > 0,
        )
        if present
    )

    return EsiResult(
        overall=overall,
        interior=interior_esi,
        surface=surface_esi,
        components=interior + surface,
        data_completeness=measured_inputs / 3.0,
    )
