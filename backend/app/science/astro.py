"""Derived astrophysical quantities.

Every function here is pure and operates on plain floats so it can be unit
tested in isolation and reused by both the ingestion pipeline and the live
habitability simulator. Functions return ``None`` when an input is missing or
physically meaningless rather than raising, because real catalogue rows are
full of gaps.
"""

from __future__ import annotations

import math

from app.science.constants import (
    ASTRONOMICAL_UNIT_M,
    DAYS_PER_YEAR,
    DEFAULT_BOND_ALBEDO,
    EARTH_DENSITY_G_CM3,
    EARTH_ESCAPE_VELOCITY_KM_S,
    EARTH_SURFACE_GRAVITY_MS2,
    PARSECS_TO_LIGHT_YEARS,
    SOLAR_EFFECTIVE_TEMP_K,
    SOLAR_RADIUS_M,
    SPECTRAL_CLASS_TEMP_BOUNDS_K,
)

__all__ = [
    "classify_spectral_type",
    "density_g_cm3",
    "equilibrium_temperature_k",
    "escape_velocity_km_s",
    "insolation_earth_units",
    "mass_from_radius_earth_units",
    "parsecs_to_light_years",
    "radius_from_mass_earth_units",
    "semi_major_axis_au",
    "stellar_luminosity_solar",
    "surface_gravity_ms2",
    "transit_tidal_locking_likelihood",
]


def _positive(value: float | None) -> float | None:
    """Return ``value`` only if it is a usable positive number."""
    if value is None:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


# --- Planet bulk properties ----------------------------------------------


def density_g_cm3(mass_earth: float | None, radius_earth: float | None) -> float | None:
    """Mean density in g/cm^3 from Earth-relative mass and radius."""
    mass = _positive(mass_earth)
    radius = _positive(radius_earth)
    if mass is None or radius is None:
        return None
    return EARTH_DENSITY_G_CM3 * mass / radius**3


def surface_gravity_ms2(
    mass_earth: float | None, radius_earth: float | None
) -> float | None:
    """Surface gravity in m/s^2 from Earth-relative mass and radius."""
    mass = _positive(mass_earth)
    radius = _positive(radius_earth)
    if mass is None or radius is None:
        return None
    return EARTH_SURFACE_GRAVITY_MS2 * mass / radius**2


def escape_velocity_km_s(
    mass_earth: float | None, radius_earth: float | None
) -> float | None:
    """Escape velocity in km/s from Earth-relative mass and radius."""
    mass = _positive(mass_earth)
    radius = _positive(radius_earth)
    if mass is None or radius is None:
        return None
    return EARTH_ESCAPE_VELOCITY_KM_S * math.sqrt(mass / radius)


# --- Mass/radius relations (Chen & Kipping 2017, "Forecaster") -------------
# A probabilistic broken power law fitted to planets and brown dwarfs. We use
# the median relation only: it is a point estimate, never a measurement, and
# anything derived from it is flagged as estimated in the API response.

_TERRAN_EXPONENT = 0.2790  # R ~ M^0.279 for M < 2.04 M_earth
_NEPTUNIAN_EXPONENT = 0.5890  # R ~ M^0.589 up to ~0.41 M_jup
_JOVIAN_EXPONENT = -0.0440  # degenerate/compressed regime

_TERRAN_MASS_CEILING_ME = 2.04
_NEPTUNIAN_MASS_CEILING_ME = 131.6

# Radii at the regime boundaries, enforcing continuity of the piecewise fit.
_TERRAN_RADIUS_CEILING_RE = _TERRAN_MASS_CEILING_ME**_TERRAN_EXPONENT
_NEPTUNIAN_RADIUS_CEILING_RE = _TERRAN_RADIUS_CEILING_RE * (
    _NEPTUNIAN_MASS_CEILING_ME / _TERRAN_MASS_CEILING_ME
) ** _NEPTUNIAN_EXPONENT


def radius_from_mass_earth_units(mass_earth: float | None) -> float | None:
    """Estimate radius (Earth radii) from mass (Earth masses)."""
    mass = _positive(mass_earth)
    if mass is None:
        return None
    if mass < _TERRAN_MASS_CEILING_ME:
        return mass**_TERRAN_EXPONENT
    if mass < _NEPTUNIAN_MASS_CEILING_ME:
        return _TERRAN_RADIUS_CEILING_RE * (
            mass / _TERRAN_MASS_CEILING_ME
        ) ** _NEPTUNIAN_EXPONENT
    return _NEPTUNIAN_RADIUS_CEILING_RE * (
        mass / _NEPTUNIAN_MASS_CEILING_ME
    ) ** _JOVIAN_EXPONENT


def mass_from_radius_earth_units(radius_earth: float | None) -> float | None:
    """Estimate mass (Earth masses) from radius (Earth radii).

    Inverts the Forecaster median relation. The Jovian branch is non-invertible
    (radius is nearly flat in mass), so radii above the Neptunian ceiling are
    clamped to that boundary mass to avoid returning absurd values.
    """
    radius = _positive(radius_earth)
    if radius is None:
        return None
    if radius < _TERRAN_RADIUS_CEILING_RE:
        return radius ** (1.0 / _TERRAN_EXPONENT)
    if radius < _NEPTUNIAN_RADIUS_CEILING_RE:
        return _TERRAN_MASS_CEILING_ME * (
            radius / _TERRAN_RADIUS_CEILING_RE
        ) ** (1.0 / _NEPTUNIAN_EXPONENT)
    return _NEPTUNIAN_MASS_CEILING_ME


# --- Stellar properties ---------------------------------------------------


def stellar_luminosity_solar(
    radius_solar: float | None, effective_temp_k: float | None
) -> float | None:
    """Bolometric luminosity in solar units from the Stefan-Boltzmann law."""
    radius = _positive(radius_solar)
    temp = _positive(effective_temp_k)
    if radius is None or temp is None:
        return None
    return radius**2 * (temp / SOLAR_EFFECTIVE_TEMP_K) ** 4


def classify_spectral_type(effective_temp_k: float | None) -> str | None:
    """Return the Morgan-Keenan class letter for an effective temperature."""
    temp = _positive(effective_temp_k)
    if temp is None:
        return None
    for letter, low, high in SPECTRAL_CLASS_TEMP_BOUNDS_K:
        if low <= temp < high:
            return letter
    return "O" if temp >= 60000 else "T"


# --- Orbits ---------------------------------------------------------------


def semi_major_axis_au(
    period_days: float | None, stellar_mass_solar: float | None
) -> float | None:
    """Semi-major axis in AU from Kepler's third law.

    Assumes the planet mass is negligible against the star, which introduces
    sub-percent error for everything except brown-dwarf companions.
    """
    period = _positive(period_days)
    mass = _positive(stellar_mass_solar)
    if period is None or mass is None:
        return None
    period_years = period / DAYS_PER_YEAR
    return (mass * period_years**2) ** (1.0 / 3.0)


def insolation_earth_units(
    luminosity_solar: float | None, semi_major_axis_au_value: float | None
) -> float | None:
    """Stellar flux at the planet, relative to Earth's 1361 W/m^2."""
    luminosity = _positive(luminosity_solar)
    axis = _positive(semi_major_axis_au_value)
    if luminosity is None or axis is None:
        return None
    return luminosity / axis**2


def equilibrium_temperature_k(
    stellar_temp_k: float | None,
    stellar_radius_solar: float | None,
    semi_major_axis_au_value: float | None,
    bond_albedo: float = DEFAULT_BOND_ALBEDO,
) -> float | None:
    """Planetary equilibrium temperature assuming efficient heat redistribution.

    T_eq = T_star * sqrt(R_star / 2a) * (1 - A)^(1/4)

    This is the temperature of an airless fast-rotating blackbody. Real surface
    temperatures are warmer by whatever greenhouse effect the atmosphere
    provides (Earth: +33 K, Venus: +500 K).
    """
    temp = _positive(stellar_temp_k)
    radius = _positive(stellar_radius_solar)
    axis = _positive(semi_major_axis_au_value)
    if temp is None or radius is None or axis is None:
        return None
    if not 0.0 <= bond_albedo < 1.0:
        bond_albedo = DEFAULT_BOND_ALBEDO
    radius_m = radius * SOLAR_RADIUS_M
    axis_m = axis * ASTRONOMICAL_UNIT_M
    return temp * math.sqrt(radius_m / (2.0 * axis_m)) * (1.0 - bond_albedo) ** 0.25


def transit_tidal_locking_likelihood(
    period_days: float | None, stellar_mass_solar: float | None
) -> float | None:
    """Rough 0-1 likelihood that a planet is tidally locked to its star.

    Tidal spin-down timescale scales steeply with orbital distance, so for
    terrestrial planets the practical discriminator is orbital period: inside
    roughly 10 days locking is near-certain over gigayear timescales, beyond
    ~50 days it becomes unlikely. Low-mass stars lock planets at wider
    separations because their habitable zones sit much closer in.
    """
    period = _positive(period_days)
    if period is None:
        return None
    mass = _positive(stellar_mass_solar) or 1.0
    # Scale the transition period with stellar mass: a 0.1 Msun star locks
    # planets out to much longer periods than a 1.0 Msun star.
    lower = 10.0 * mass**0.5
    upper = 60.0 * mass**0.5
    if period <= lower:
        return 1.0
    if period >= upper:
        return 0.0
    return float((upper - period) / (upper - lower))


# --- Misc -----------------------------------------------------------------


def parsecs_to_light_years(parsecs: float | None) -> float | None:
    """Convert a distance in parsecs to light years."""
    value = _positive(parsecs)
    if value is None:
        return None
    return value * PARSECS_TO_LIGHT_YEARS
