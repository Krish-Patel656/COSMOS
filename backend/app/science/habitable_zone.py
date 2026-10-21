"""Circumstellar habitable zone boundaries.

Implements the parametrisation of Kopparapu et al. (2013, ApJ 765:131; erratum
2013, ApJ 770:82) with the planet-mass dependence of Kopparapu et al. (2014,
ApJL 787:L29). The model gives the stellar flux at which a cloud-free,
1-dimensional radiative-convective atmosphere loses its oceans (inner edge) or
can no longer be kept above freezing by a maximal CO2 greenhouse (outer edge).

Four boundaries are produced:

* ``recent_venus``    - empirical inner edge: Venus may have been habitable
                        until ~1 Gyr ago, so this flux is an observational
                        upper limit rather than a model result.
* ``runaway_greenhouse`` - conservative inner edge: water vapour feedback runs
                        away and the ocean is lost to space.
* ``maximum_greenhouse`` - conservative outer edge: the CO2 greenhouse peaks;
                        beyond this, adding CO2 cools the surface by Rayleigh
                        scattering.
* ``early_mars``      - empirical outer edge: Mars shows evidence of liquid
                        water ~3.8 Gyr ago under a fainter young Sun.

The region between the two conservative edges is the "conservative habitable
zone"; between the two empirical edges, the "optimistic habitable zone".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "HabitableZone",
    "HZ_BOUNDARY_LABELS",
    "effective_flux_limit",
    "habitable_zone",
    "hz_flux_position",
    "hz_position",
]

# Polynomial coefficients: S_eff = S_eff_sun + a*dT + b*dT^2 + c*dT^3 + d*dT^4
# with dT = T_eff - 5780 K. Valid for 2600 K <= T_eff <= 7200 K.
# Rows are (S_eff_sun, a, b, c, d) from Kopparapu et al. (2014) Table 1.
_COEFFICIENTS = {
    "recent_venus": (1.7763, 1.4335e-4, 3.3954e-9, -7.6364e-12, -1.1950e-15),
    "runaway_greenhouse": (1.0385, 1.2456e-4, 1.4612e-8, -7.6345e-12, -1.7511e-15),
    "maximum_greenhouse": (0.3507, 5.9578e-5, 1.6707e-9, -3.0058e-12, -5.1925e-16),
    "early_mars": (0.3207, 5.4471e-5, 1.5275e-9, -2.1709e-12, -3.8282e-16),
}

# Mass scaling of the runaway greenhouse limit (Kopparapu et al. 2014, Eq. 5).
# More massive planets have higher surface gravity, a shorter scale height and
# therefore a drier stratosphere, pushing the inner edge slightly starward.
_RUNAWAY_MASS_COEFFS = (0.99, 0.00067, 1.5e-6)

_REFERENCE_TEMP_K = 5780.0
_VALID_TEMP_RANGE_K = (2600.0, 7200.0)

HZ_BOUNDARY_LABELS = {
    "recent_venus": "Recent Venus (optimistic inner edge)",
    "runaway_greenhouse": "Runaway greenhouse (conservative inner edge)",
    "maximum_greenhouse": "Maximum greenhouse (conservative outer edge)",
    "early_mars": "Early Mars (optimistic outer edge)",
}


@dataclass(frozen=True)
class HabitableZone:
    """Habitable zone edges for one star, in AU and in Earth-relative flux."""

    recent_venus_au: float
    runaway_greenhouse_au: float
    maximum_greenhouse_au: float
    early_mars_au: float

    recent_venus_flux: float
    runaway_greenhouse_flux: float
    maximum_greenhouse_flux: float
    early_mars_flux: float

    stellar_temp_k: float
    stellar_luminosity_solar: float
    extrapolated: bool
    """True when the host star's temperature falls outside the model's
    2600-7200 K calibration range and coefficients were evaluated at the
    nearest valid temperature."""

    @property
    def conservative_range_au(self) -> tuple[float, float]:
        return (self.runaway_greenhouse_au, self.maximum_greenhouse_au)

    @property
    def optimistic_range_au(self) -> tuple[float, float]:
        return (self.recent_venus_au, self.early_mars_au)

    @property
    def conservative_flux_range(self) -> tuple[float, float]:
        """(outer, inner) in flux units — note flux *decreases* outward."""
        return (self.maximum_greenhouse_flux, self.runaway_greenhouse_flux)

    @property
    def optimistic_flux_range(self) -> tuple[float, float]:
        return (self.early_mars_flux, self.recent_venus_flux)

    def contains(self, semi_major_axis_au: float, optimistic: bool = False) -> bool:
        low, high = self.optimistic_range_au if optimistic else self.conservative_range_au
        return low <= semi_major_axis_au <= high

    def contains_flux(self, insolation_earth: float, optimistic: bool = False) -> bool:
        """Whether a planet receiving this flux falls inside the zone.

        Prefer this over :meth:`contains` whenever a measured insolation is
        available. The Kopparapu limits are defined as fluxes; converting them to
        distances requires the stellar luminosity, and the NASA composite table
        draws its stellar radius and its planetary insolation from different
        publications often enough that the two disagree by tens of percent. For
        Kepler-186 f that discrepancy is the difference between "inside the
        habitable zone" and "outside it".
        """
        low, high = (
            self.optimistic_flux_range if optimistic else self.conservative_flux_range
        )
        return low <= insolation_earth <= high

    def as_dict(self) -> dict:
        return {
            "recent_venus_au": self.recent_venus_au,
            "runaway_greenhouse_au": self.runaway_greenhouse_au,
            "maximum_greenhouse_au": self.maximum_greenhouse_au,
            "early_mars_au": self.early_mars_au,
            "recent_venus_flux": self.recent_venus_flux,
            "runaway_greenhouse_flux": self.runaway_greenhouse_flux,
            "maximum_greenhouse_flux": self.maximum_greenhouse_flux,
            "early_mars_flux": self.early_mars_flux,
            "stellar_temp_k": self.stellar_temp_k,
            "stellar_luminosity_solar": self.stellar_luminosity_solar,
            "extrapolated": self.extrapolated,
        }


def effective_flux_limit(
    boundary: str, stellar_temp_k: float, planet_mass_earth: float | None = None
) -> float:
    """Effective stellar flux (Earth units) at one habitable zone boundary."""
    if boundary not in _COEFFICIENTS:
        raise ValueError(f"unknown habitable zone boundary: {boundary!r}")

    clamped = min(max(stellar_temp_k, _VALID_TEMP_RANGE_K[0]), _VALID_TEMP_RANGE_K[1])
    s_sun, a, b, c, d = _COEFFICIENTS[boundary]

    if boundary == "runaway_greenhouse" and planet_mass_earth:
        # Kopparapu et al. (2014) calibrate the mass term over 0.1-5 M_earth.
        mass = min(max(planet_mass_earth, 0.1), 5.0)
        log_mass = math.log10(mass)
        k0, k1, k2 = _RUNAWAY_MASS_COEFFS
        s_sun = s_sun * (k0 + k1 * log_mass + k2 * log_mass**2)

    delta_t = clamped - _REFERENCE_TEMP_K
    return s_sun + a * delta_t + b * delta_t**2 + c * delta_t**3 + d * delta_t**4


def habitable_zone(
    stellar_temp_k: float | None,
    stellar_luminosity_solar: float | None,
    planet_mass_earth: float | None = None,
) -> HabitableZone | None:
    """Compute habitable zone edges, or ``None`` if the star is unconstrained."""
    if not stellar_temp_k or not stellar_luminosity_solar:
        return None
    if stellar_temp_k <= 0 or stellar_luminosity_solar <= 0:
        return None

    extrapolated = not (
        _VALID_TEMP_RANGE_K[0] <= stellar_temp_k <= _VALID_TEMP_RANGE_K[1]
    )

    fluxes = {
        name: effective_flux_limit(name, stellar_temp_k, planet_mass_earth)
        for name in _COEFFICIENTS
    }
    # d = sqrt(L / S_eff) with L in solar units gives the distance in AU.
    distances = {
        name: math.sqrt(stellar_luminosity_solar / flux) for name, flux in fluxes.items()
    }

    return HabitableZone(
        recent_venus_au=distances["recent_venus"],
        runaway_greenhouse_au=distances["runaway_greenhouse"],
        maximum_greenhouse_au=distances["maximum_greenhouse"],
        early_mars_au=distances["early_mars"],
        recent_venus_flux=fluxes["recent_venus"],
        runaway_greenhouse_flux=fluxes["runaway_greenhouse"],
        maximum_greenhouse_flux=fluxes["maximum_greenhouse"],
        early_mars_flux=fluxes["early_mars"],
        stellar_temp_k=stellar_temp_k,
        stellar_luminosity_solar=stellar_luminosity_solar,
        extrapolated=extrapolated,
    )


def hz_position(zone: HabitableZone, semi_major_axis_au: float) -> float | None:
    """Normalised position across the conservative habitable zone.

    Returns 0.0 at the runaway-greenhouse (inner) edge and 1.0 at the
    maximum-greenhouse (outer) edge. Values outside [0, 1] mean the planet sits
    outside the conservative zone; the magnitude indicates how far, measured in
    units of the zone's own width.
    """
    if semi_major_axis_au is None or semi_major_axis_au <= 0:
        return None
    inner, outer = zone.conservative_range_au
    width = outer - inner
    if width <= 0:
        return None
    return (semi_major_axis_au - inner) / width


def hz_flux_position(zone: HabitableZone, insolation_earth: float) -> float | None:
    """Normalised position across the conservative zone, measured in flux.

    0.0 at the runaway-greenhouse (inner, bright) edge and 1.0 at the
    maximum-greenhouse (outer, dim) edge, interpolated logarithmically because
    flux falls as the inverse square of distance.
    """
    if insolation_earth is None or insolation_earth <= 0:
        return None
    outer_flux, inner_flux = zone.conservative_flux_range
    if outer_flux <= 0 or inner_flux <= outer_flux:
        return None
    span = math.log(inner_flux) - math.log(outer_flux)
    return (math.log(inner_flux) - math.log(insolation_earth)) / span
