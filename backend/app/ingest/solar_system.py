"""The Solar System as a reference system.

Including our own planets is not decoration. It gives the habitability engine a
ground truth to be sanity-checked against (Earth must score at the top, Venus
and Mars must not), it gives users something familiar to compare alien worlds
against in the comparison view, and it gives the 3D explorer a system whose
appearance people can actually verify.

Values are IAU/NASA Planetary Fact Sheet figures. Unlike the exoplanet rows,
these carry both an equilibrium temperature and a measured mean surface
temperature, which is how the UI can show the 33 K greenhouse gap on Earth and
the 510 K gap on Venus.

Pluto and the dwarf planets are deliberately excluded: the IAU definition of a
planet is the line the rest of the catalogue uses.
"""

from __future__ import annotations

from typing import Any

SUN: dict[str, Any] = {
    "name": "Sun",
    "aliases": ["Sol", "Solar System"],
    "spectral_type": "G2 V",
    "effective_temp_k": 5772.0,
    "radius_solar": 1.0,
    "mass_solar": 1.0,
    "luminosity_solar": 1.0,
    "metallicity_dex": 0.0,
    "surface_gravity_log": 4.438,
    "age_gyr": 4.603,
    "rotation_period_days": 25.05,
    "right_ascension_deg": 0.0,
    "declination_deg": 0.0,
    "distance_pc": 0.0,
    "v_magnitude": -26.74,
    "stellar_count": 1,
    "description": (
        "Our own star: a middle-aged G-type main-sequence dwarf, 4.6 billion years into a "
        "roughly 10-billion-year hydrogen-burning lifetime. It is the only star whose planetary "
        "system we have visited, and the only one where we know for certain that life exists."
    ),
}

# Each entry carries measured values only; derived quantities and scores are
# computed by the same pipeline that processes exoplanets, so the Solar System
# is scored by exactly the same rules.
PLANETS: list[dict[str, Any]] = [
    {
        "name": "Mercury",
        "radius_earth": 0.3829,
        "mass_earth": 0.05527,
        "orbital_period_days": 87.9691,
        "semi_major_axis_au": 0.387098,
        "eccentricity": 0.205630,
        "inclination_deg": 7.005,
        "equilibrium_temp_k": 440.0,
        "surface_temp_k": 440.0,
        "insolation_earth": 6.6741,
        "notes": (
            "Airless and tidally tortured: its 3:2 spin-orbit resonance and lack of atmosphere "
            "produce a 600 K swing between day and night."
        ),
    },
    {
        "name": "Venus",
        "radius_earth": 0.9499,
        "mass_earth": 0.81500,
        "orbital_period_days": 224.701,
        "semi_major_axis_au": 0.723332,
        "eccentricity": 0.006772,
        "inclination_deg": 3.39458,
        "equilibrium_temp_k": 227.0,
        "surface_temp_k": 737.0,
        "insolation_earth": 1.9112,
        "notes": (
            "The cautionary tale of habitability: nearly Earth's twin in size and density, but a "
            "runaway greenhouse has left it with a 92-bar CO₂ atmosphere and a 737 K surface — "
            "510 K hotter than its equilibrium temperature."
        ),
    },
    {
        "name": "Earth",
        "radius_earth": 1.0,
        "mass_earth": 1.0,
        "orbital_period_days": 365.256,
        "semi_major_axis_au": 1.000003,
        "eccentricity": 0.016710,
        "inclination_deg": 0.0,
        "equilibrium_temp_k": 255.0,
        "surface_temp_k": 288.0,
        "insolation_earth": 1.0,
        "notes": (
            "The reference world, and the only one known to be inhabited. Its 33 K greenhouse "
            "effect is what lifts a 255 K equilibrium temperature to a 288 K surface where water "
            "is liquid."
        ),
    },
    {
        "name": "Mars",
        "radius_earth": 0.5320,
        "mass_earth": 0.10745,
        "orbital_period_days": 686.980,
        "semi_major_axis_au": 1.523680,
        "eccentricity": 0.093410,
        "inclination_deg": 1.850,
        "equilibrium_temp_k": 210.0,
        "surface_temp_k": 210.0,
        "insolation_earth": 0.4310,
        "notes": (
            "Inside the Sun's habitable zone, yet frozen and nearly airless: at 0.11 Earth masses "
            "it could not hold onto its early atmosphere. Proof that orbital position alone does "
            "not make a planet habitable."
        ),
    },
    {
        "name": "Jupiter",
        "radius_earth": 11.209,
        "mass_earth": 317.83,
        "orbital_period_days": 4332.589,
        "semi_major_axis_au": 5.2044,
        "eccentricity": 0.048930,
        "inclination_deg": 1.303,
        "equilibrium_temp_k": 110.0,
        "surface_temp_k": 165.0,
        "insolation_earth": 0.03692,
        "notes": (
            "A hydrogen-helium giant with 318 Earth masses and no surface. Its gravity shapes the "
            "whole Solar System, including which asteroids reach the inner planets."
        ),
    },
    {
        "name": "Saturn",
        "radius_earth": 9.449,
        "mass_earth": 95.159,
        "orbital_period_days": 10759.22,
        "semi_major_axis_au": 9.5826,
        "eccentricity": 0.056500,
        "inclination_deg": 2.485,
        "equilibrium_temp_k": 81.0,
        "surface_temp_k": 134.0,
        "insolation_earth": 0.01089,
        "notes": (
            "The least dense planet in the Solar System at 0.69 g/cm³ — it would float on water — "
            "wrapped in a ring system only about 20 metres thick in places."
        ),
    },
    {
        "name": "Uranus",
        "radius_earth": 4.007,
        "mass_earth": 14.536,
        "orbital_period_days": 30688.5,
        "semi_major_axis_au": 19.2184,
        "eccentricity": 0.047170,
        "inclination_deg": 0.773,
        "equilibrium_temp_k": 58.0,
        "surface_temp_k": 76.0,
        "insolation_earth": 0.002707,
        "notes": (
            "An ice giant tipped 98° on its side, probably by a giant impact, so its poles take "
            "turns facing the Sun through a 42-year summer and winter."
        ),
    },
    {
        "name": "Neptune",
        "radius_earth": 3.883,
        "mass_earth": 17.147,
        "orbital_period_days": 60182.0,
        "semi_major_axis_au": 30.1104,
        "eccentricity": 0.008590,
        "inclination_deg": 1.770,
        "equilibrium_temp_k": 47.0,
        "surface_temp_k": 72.0,
        "insolation_earth": 0.001103,
        "notes": (
            "The windiest planet known, with jets exceeding 2000 km/h despite receiving a "
            "thousandth of Earth's sunlight. It was found by mathematics before it was ever seen."
        ),
    },
]

DISCOVERY = {
    "Mercury": (None, "Known since antiquity"),
    "Venus": (None, "Known since antiquity"),
    "Earth": (None, "Known since antiquity"),
    "Mars": (None, "Known since antiquity"),
    "Jupiter": (None, "Known since antiquity"),
    "Saturn": (None, "Known since antiquity"),
    "Uranus": (1781, "William Herschel, Bath"),
    "Neptune": (1846, "Berlin Observatory"),
}
