"""Physical and astronomical constants used across the COSMOS science engine.

Values follow IAU 2015 nominal conversion constants where applicable
(Prsa et al. 2016, "Nominal Values for Selected Solar and Planetary Quantities").
All constants are SI unless the name states otherwise.
"""

from __future__ import annotations

# --- Fundamental ----------------------------------------------------------
GRAVITATIONAL_CONSTANT = 6.67430e-11  # m^3 kg^-1 s^-2
STEFAN_BOLTZMANN = 5.670374419e-8  # W m^-2 K^-4
SPEED_OF_LIGHT = 2.99792458e8  # m / s

# --- Solar ----------------------------------------------------------------
SOLAR_RADIUS_M = 6.957e8
SOLAR_MASS_KG = 1.98892e30
SOLAR_LUMINOSITY_W = 3.828e26
SOLAR_EFFECTIVE_TEMP_K = 5772.0

# --- Earth ----------------------------------------------------------------
EARTH_RADIUS_M = 6.3781e6
EARTH_MASS_KG = 5.97217e24
EARTH_DENSITY_G_CM3 = 5.513
EARTH_ESCAPE_VELOCITY_KM_S = 11.186
EARTH_SURFACE_GRAVITY_MS2 = 9.80665

# Earth's reference temperatures. The ESI of Schulze-Makuch et al. (2011) is
# defined against the *surface* temperature (288 K), but almost every measured
# exoplanet temperature in the NASA archive is an *equilibrium* temperature.
# We therefore score equilibrium temperatures against Earth's equilibrium
# temperature (255 K) and say so in the explanation, rather than silently
# comparing two different physical quantities.
EARTH_SURFACE_TEMP_K = 288.0
EARTH_EQUILIBRIUM_TEMP_K = 255.0

# --- Jupiter --------------------------------------------------------------
JUPITER_RADIUS_M = 7.1492e7
JUPITER_MASS_KG = 1.898e27

# Convenient Earth-relative conversions
JUPITER_RADII_IN_EARTH_RADII = JUPITER_RADIUS_M / EARTH_RADIUS_M  # ~11.209
JUPITER_MASSES_IN_EARTH_MASSES = JUPITER_MASS_KG / EARTH_MASS_KG  # ~317.8

# --- Distance -------------------------------------------------------------
ASTRONOMICAL_UNIT_M = 1.495978707e11
PARSEC_M = 3.0856775814913673e16
LIGHT_YEAR_M = 9.4607304725808e15
PARSECS_TO_LIGHT_YEARS = PARSEC_M / LIGHT_YEAR_M  # ~3.26156

# --- Time -----------------------------------------------------------------
SECONDS_PER_DAY = 86400.0
DAYS_PER_YEAR = 365.25

# --- Planetary science ----------------------------------------------------
# Default Bond albedo used when computing equilibrium temperature for planets
# with no measured albedo. 0.3 is Earth-like and the conventional choice in the
# exoplanet literature.
DEFAULT_BOND_ALBEDO = 0.3

# The "radius valley" (Fulton et al. 2017): a measured scarcity of planets
# between ~1.5 and ~2.0 Earth radii, interpreted as the boundary between
# rocky super-Earths and volatile-rich sub-Neptunes.
RADIUS_VALLEY_LOWER_RE = 1.5
RADIUS_VALLEY_UPPER_RE = 2.0

# Above ~1.6 Earth radii, nearly all planets with measured masses have
# densities too low to be rocky (Rogers 2015).
ROCKY_RADIUS_CEILING_RE = 1.6

# Liquid-water-compatible surface temperature band at ~1 bar, widened modestly
# to allow for greenhouse warming and salinity/pressure effects.
LIQUID_WATER_MIN_K = 273.15
LIQUID_WATER_MAX_K = 373.15

# Stellar effective-temperature boundaries for Morgan-Keenan spectral classes.
SPECTRAL_CLASS_TEMP_BOUNDS_K: tuple[tuple[str, float, float], ...] = (
    ("O", 30000.0, 60000.0),
    ("B", 10000.0, 30000.0),
    ("A", 7500.0, 10000.0),
    ("F", 6000.0, 7500.0),
    ("G", 5200.0, 6000.0),
    ("K", 3700.0, 5200.0),
    ("M", 2400.0, 3700.0),
    ("L", 1300.0, 2400.0),
)
