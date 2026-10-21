"""Normalisation and enrichment.

Turns raw archive rows (all strings, many blank, mixed unit conventions) into
star records with nested, fully scored planet records. This is where every unit
conversion, derived quantity and score is computed exactly once, so that the API
layer only ever reads and filters.

Design rules enforced here:

* Measured values are never overwritten by estimates. When a value has to be
  derived, the corresponding ``*_is_estimated`` flag is set and surfaced through
  the API so the UI can mark it.
* Jupiter-unit columns are only consulted when the Earth-unit column is blank,
  since the archive populates both inconsistently.
* ``st_lum`` is log10(L/L_sun) in the archive, a detail that silently corrupts
  habitable-zone calculations if missed.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from typing import Any

from app.core.text import planet_letter, slugify
from app.ingest import solar_system
from app.science import appearance as appearance_mod
from app.science import astro
from app.science.constants import (
    JUPITER_MASSES_IN_EARTH_MASSES,
    JUPITER_RADII_IN_EARTH_RADII,
)
from app.science.esi import compute_esi
from app.science.habitability import PlanetInput, compute_habitability
from app.science.habitable_zone import habitable_zone

logger = logging.getLogger(__name__)

# Stars brighter than magnitude 6.5 are visible to the unaided eye from a dark
# site, which is a genuinely useful thing to tell someone looking at a map.
NAKED_EYE_MAGNITUDE_LIMIT = 6.5


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "nan", "none"):
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _as_int(value: str | None) -> int | None:
    number = _as_float(value)
    return int(number) if number is not None else None


def _as_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def equatorial_to_cartesian(
    ra_deg: float | None, dec_deg: float | None, distance_pc: float | None
) -> tuple[float | None, float | None, float | None]:
    """Convert right ascension, declination and distance to cartesian parsecs.

    The resulting frame is equatorial: +x towards the vernal equinox, +z towards
    the north celestial pole, with the Sun at the origin. Precomputing this keeps
    trigonometry out of the render loop for thousands of stars.
    """
    if ra_deg is None or dec_deg is None or distance_pc is None:
        return (None, None, None)
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    return (
        distance_pc * math.cos(dec) * math.cos(ra),
        distance_pc * math.cos(dec) * math.sin(ra),
        distance_pc * math.sin(dec),
    )


# --- Star ------------------------------------------------------------------


def _build_star(row: dict[str, str | None]) -> dict[str, Any]:
    name = _as_text(row.get("hostname")) or "Unknown"
    temp = _as_float(row.get("st_teff"))
    radius = _as_float(row.get("st_rad"))
    distance = _as_float(row.get("sy_dist"))

    # The archive stores luminosity as log10(L/Lsun). Treating it as a linear
    # value would put the habitable zone of a Sun-like star at 0 AU.
    log_luminosity = _as_float(row.get("st_lum"))
    luminosity = 10.0**log_luminosity if log_luminosity is not None else None
    if luminosity is None:
        luminosity = astro.stellar_luminosity_solar(radius, temp)

    ra = _as_float(row.get("ra"))
    dec = _as_float(row.get("dec"))
    x, y, z = equatorial_to_cartesian(ra, dec, distance)
    v_mag = _as_float(row.get("sy_vmag"))

    return {
        "slug": slugify(name),
        "name": name,
        "aliases": None,
        "right_ascension_deg": ra,
        "declination_deg": dec,
        "distance_pc": distance,
        "distance_ly": astro.parsecs_to_light_years(distance),
        "x_pc": x,
        "y_pc": y,
        "z_pc": z,
        "spectral_type": _as_text(row.get("st_spectype")),
        "spectral_class": astro.classify_spectral_type(temp),
        "effective_temp_k": temp,
        "radius_solar": radius,
        "mass_solar": _as_float(row.get("st_mass")),
        "luminosity_solar": luminosity,
        "metallicity_dex": _as_float(row.get("st_met")),
        "surface_gravity_log": _as_float(row.get("st_logg")),
        "age_gyr": _as_float(row.get("st_age")),
        "rotation_period_days": _as_float(row.get("st_rotp")),
        "v_magnitude": v_mag,
        "gaia_magnitude": _as_float(row.get("sy_gaiamag")),
        "naked_eye_visible": bool(v_mag is not None and v_mag <= NAKED_EYE_MAGNITUDE_LIMIT),
        "planet_count": _as_int(row.get("sy_pnum")) or 0,
        "stellar_count": _as_int(row.get("sy_snum")) or 1,
        "is_solar_system": False,
        "color_hex": appearance_mod.star_color_hex(temp),
        "description": None,
        "planets": [],
    }


# --- Planet ----------------------------------------------------------------


def _resolve_radius(row: dict[str, str | None]) -> tuple[float | None, float | None]:
    radius_earth = _as_float(row.get("pl_rade"))
    radius_jupiter = _as_float(row.get("pl_radj"))
    if radius_earth is None and radius_jupiter is not None:
        radius_earth = radius_jupiter * JUPITER_RADII_IN_EARTH_RADII
    if radius_jupiter is None and radius_earth is not None:
        radius_jupiter = radius_earth / JUPITER_RADII_IN_EARTH_RADII
    return radius_earth, radius_jupiter


def _resolve_mass(row: dict[str, str | None]) -> tuple[float | None, float | None]:
    mass_earth = _as_float(row.get("pl_bmasse"))
    mass_jupiter = _as_float(row.get("pl_bmassj"))
    if mass_earth is None and mass_jupiter is not None:
        mass_earth = mass_jupiter * JUPITER_MASSES_IN_EARTH_MASSES
    if mass_jupiter is None and mass_earth is not None:
        mass_jupiter = mass_earth / JUPITER_MASSES_IN_EARTH_MASSES
    return mass_earth, mass_jupiter


def enrich_planet(planet: dict[str, Any], star: dict[str, Any]) -> dict[str, Any]:
    """Fill in derived quantities, scores and appearance for one planet.

    Shared by exoplanet ingestion and the Solar System loader so that both are
    scored by identical rules — which is the whole point of carrying the Solar
    System in the same catalogue.
    """
    radius = planet.get("radius_earth")
    mass = planet.get("mass_earth")

    axis = planet.get("semi_major_axis_au")
    if axis is None:
        axis = astro.semi_major_axis_au(
            planet.get("orbital_period_days"), star.get("mass_solar")
        )
        planet["axis_is_estimated"] = axis is not None
    planet["semi_major_axis_au"] = axis

    temp = planet.get("equilibrium_temp_k")
    if temp is None:
        temp = astro.equilibrium_temperature_k(
            star.get("effective_temp_k"), star.get("radius_solar"), axis
        )
        planet["temp_is_estimated"] = temp is not None
    planet["equilibrium_temp_k"] = temp

    if planet.get("insolation_earth") is None:
        planet["insolation_earth"] = astro.insolation_earth_units(
            star.get("luminosity_solar"), axis
        )

    # Bulk quantities use measured values when both mass and radius exist, and
    # the mass-radius relation otherwise. The flags record which happened.
    effective_radius = radius or astro.radius_from_mass_earth_units(mass)
    effective_mass = mass or astro.mass_from_radius_earth_units(radius)
    # Preserve any flag the caller already set from catalogue provenance — the
    # archive derives roughly half of its masses from a mass-radius relation, and
    # those are no more measured than the ones we derive ourselves.
    planet["radius_is_estimated"] = bool(planet.get("radius_is_estimated")) or (
        radius is None and effective_radius is not None
    )
    planet["mass_is_estimated"] = bool(planet.get("mass_is_estimated")) or (
        mass is None and effective_mass is not None
    )

    planet["density_g_cm3"] = astro.density_g_cm3(effective_mass, effective_radius)
    planet["surface_gravity_ms2"] = astro.surface_gravity_ms2(effective_mass, effective_radius)
    planet["escape_velocity_km_s"] = astro.escape_velocity_km_s(effective_mass, effective_radius)
    planet["tidal_locking_likelihood"] = astro.transit_tidal_locking_likelihood(
        planet.get("orbital_period_days"), star.get("mass_solar")
    )

    scoring_input = PlanetInput(
        radius_earth=radius,
        mass_earth=mass,
        equilibrium_temp_k=planet.get("equilibrium_temp_k"),
        surface_temp_k=planet.get("surface_temp_k"),
        orbital_period_days=planet.get("orbital_period_days"),
        semi_major_axis_au=axis,
        eccentricity=planet.get("eccentricity"),
        insolation_earth=planet.get("insolation_earth"),
        star_effective_temp_k=star.get("effective_temp_k"),
        star_radius_solar=star.get("radius_solar"),
        star_mass_solar=star.get("mass_solar"),
        star_luminosity_solar=star.get("luminosity_solar"),
        star_age_gyr=star.get("age_gyr"),
        star_metallicity_dex=star.get("metallicity_dex"),
        mass_is_minimum=bool(planet.get("mass_is_minimum")),
        mass_is_estimated=bool(planet["mass_is_estimated"]),
        radius_is_estimated=bool(planet["radius_is_estimated"]),
    )
    habitability = compute_habitability(scoring_input)

    # Solar System planets have measured surface temperatures; exoplanets do
    # not, so the ESI reference temperature differs between the two.
    surface_temp = planet.get("surface_temp_k")
    esi = compute_esi(
        radius,
        mass,
        surface_temp if surface_temp is not None else planet.get("equilibrium_temp_k"),
        temperature_is_equilibrium=surface_temp is None,
        mass_is_estimated=bool(planet["mass_is_estimated"]),
        radius_is_estimated=bool(planet["radius_is_estimated"]),
    )

    planet["habitability_score"] = habitability.score
    planet["habitability_band"] = habitability.band
    planet["habitability_confidence"] = habitability.confidence
    planet["habitability_breakdown"] = habitability.as_dict()
    planet["in_conservative_hz"] = habitability.in_conservative_hz
    planet["in_optimistic_hz"] = habitability.in_optimistic_hz
    planet["size_class"] = habitability.size_class
    planet["thermal_class"] = habitability.thermal_class

    planet["esi"] = esi.overall
    planet["esi_interior"] = esi.interior
    planet["esi_surface"] = esi.surface
    planet["esi_breakdown"] = esi.as_dict()

    planet["appearance"] = appearance_mod.derive_appearance(
        effective_radius,
        effective_mass,
        planet.get("equilibrium_temp_k"),
        planet.get("insolation_earth"),
        planet.get("density_g_cm3"),
    ).as_dict()

    return planet


def _build_planet(row: dict[str, str | None], star: dict[str, Any]) -> dict[str, Any]:
    name = _as_text(row.get("pl_name")) or "Unknown"
    radius_earth, radius_jupiter = _resolve_radius(row)
    mass_earth, mass_jupiter = _resolve_mass(row)
    provenance = _as_text(row.get("pl_bmassprov"))
    provenance_lower = (provenance or "").lower()

    planet: dict[str, Any] = {
        "slug": slugify(name),
        "name": name,
        "letter": planet_letter(name, star["name"]),
        "radius_earth": radius_earth,
        "radius_jupiter": radius_jupiter,
        "mass_earth": mass_earth,
        "mass_jupiter": mass_jupiter,
        # "Msini" provenance means radial velocity without a known inclination,
        # so the catalogued mass is a lower bound on the true mass.
        "mass_is_minimum": "msini" in provenance_lower or "msin(i)" in provenance_lower,
        "mass_provenance": provenance,
        "orbital_period_days": _as_float(row.get("pl_orbper")),
        "semi_major_axis_au": _as_float(row.get("pl_orbsmax")),
        "eccentricity": _as_float(row.get("pl_orbeccen")),
        "inclination_deg": _as_float(row.get("pl_orbincl")),
        "equilibrium_temp_k": _as_float(row.get("pl_eqt")),
        "surface_temp_k": None,
        "insolation_earth": _as_float(row.get("pl_insol")),
        "discovery_method": _as_text(row.get("discoverymethod")),
        "discovery_year": _as_int(row.get("disc_year")),
        "discovery_facility": _as_text(row.get("disc_facility")),
        "is_controversial": _as_int(row.get("pl_controv_flag")) == 1,
        "is_solar_system": False,
        "last_updated_source": _as_text(row.get("pl_pubdate")),
        "radius_is_estimated": False,
        # The archive's own "M-R relationship" provenance means the mass was
        # computed from the radius, not observed. About 46% of the catalogue is
        # like this, so treating it as measured would misrepresent half the data.
        "mass_is_estimated": "m-r" in provenance_lower,
        "temp_is_estimated": False,
        "axis_is_estimated": False,
        "reference": "NASA Exoplanet Archive, Planetary Systems Composite Parameters table",
        "notes": None,
    }
    return enrich_planet(planet, star)


# --- Assembly --------------------------------------------------------------


def _finalise_star(star: dict[str, Any]) -> dict[str, Any]:
    """Compute system-level aggregates once all planets are attached."""
    planets = star["planets"]
    star["planet_count"] = max(star.get("planet_count") or 0, len(planets))

    habitability_scores = [p["habitability_score"] for p in planets if p["habitability_score"]]
    esi_scores = [p["esi"] for p in planets if p["esi"]]
    star["best_habitability_score"] = max(habitability_scores) if habitability_scores else None
    star["best_esi"] = max(esi_scores) if esi_scores else None

    # Habitable zone shown on the system map uses a 1 Earth-mass reference
    # planet, since the zone edges are a property of the star plus an assumed
    # planet mass and we want one set of rings per system, not one per planet.
    zone = habitable_zone(star.get("effective_temp_k"), star.get("luminosity_solar"), 1.0)
    star["habitable_zone"] = zone.as_dict() if zone else None
    return star


def normalize_rows(rows: Iterable[dict[str, str | None]]) -> list[dict[str, Any]]:
    """Group raw archive rows into enriched star records with nested planets."""
    stars: dict[str, dict[str, Any]] = {}
    skipped = 0

    for row in rows:
        host = _as_text(row.get("hostname"))
        planet_name = _as_text(row.get("pl_name"))
        if not host or not planet_name:
            skipped += 1
            continue

        star = stars.get(host)
        if star is None:
            star = _build_star(row)
            stars[host] = star

        star["planets"].append(_build_planet(row, star))

    result = [_finalise_star(star) for star in stars.values()]

    # Slug collisions would break URLs silently, so disambiguate explicitly.
    _deduplicate_slugs(result)

    if skipped:
        logger.warning("Skipped %d rows with no host or planet name", skipped)
    logger.info("Normalised %d systems containing %d planets", len(result), sum(len(s["planets"]) for s in result))
    return result


def _deduplicate_slugs(stars: list[dict[str, Any]]) -> None:
    seen_stars: dict[str, int] = {}
    seen_planets: dict[str, int] = {}
    for star in stars:
        base = star["slug"]
        count = seen_stars.get(base, 0)
        if count:
            star["slug"] = f"{base}-{count + 1}"
        seen_stars[base] = count + 1

        for planet in star["planets"]:
            pbase = planet["slug"]
            pcount = seen_planets.get(pbase, 0)
            if pcount:
                planet["slug"] = f"{pbase}-{pcount + 1}"
            seen_planets[pbase] = pcount + 1


def build_solar_system() -> dict[str, Any]:
    """Build the Sun's record with all eight planets, scored like any other."""
    star: dict[str, Any] = dict(solar_system.SUN)
    temp = star["effective_temp_k"]
    x, y, z = 0.0, 0.0, 0.0

    star.update(
        {
            "slug": "sun",
            "aliases": solar_system.SUN["aliases"],
            "spectral_class": astro.classify_spectral_type(temp),
            "distance_ly": 0.0,
            "x_pc": x,
            "y_pc": y,
            "z_pc": z,
            "gaia_magnitude": None,
            "naked_eye_visible": True,
            "is_solar_system": True,
            "color_hex": appearance_mod.star_color_hex(temp),
            "planet_count": len(solar_system.PLANETS),
            "planets": [],
        }
    )

    for entry in solar_system.PLANETS:
        year, facility = solar_system.DISCOVERY[entry["name"]]
        planet: dict[str, Any] = {
            "slug": slugify(entry["name"]),
            "name": entry["name"],
            "letter": None,
            "radius_earth": entry["radius_earth"],
            "radius_jupiter": entry["radius_earth"] / JUPITER_RADII_IN_EARTH_RADII,
            "mass_earth": entry["mass_earth"],
            "mass_jupiter": entry["mass_earth"] / JUPITER_MASSES_IN_EARTH_MASSES,
            "mass_is_minimum": False,
            "mass_provenance": "Mass",
            "orbital_period_days": entry["orbital_period_days"],
            "semi_major_axis_au": entry["semi_major_axis_au"],
            "eccentricity": entry["eccentricity"],
            "inclination_deg": entry["inclination_deg"],
            "equilibrium_temp_k": entry["equilibrium_temp_k"],
            "surface_temp_k": entry["surface_temp_k"],
            "insolation_earth": entry["insolation_earth"],
            "discovery_method": "Direct observation",
            "discovery_year": year,
            "discovery_facility": facility,
            "is_controversial": False,
            "is_solar_system": True,
            "last_updated_source": "NASA Planetary Fact Sheet",
            "radius_is_estimated": False,
            "mass_is_estimated": False,
            "temp_is_estimated": False,
            "axis_is_estimated": False,
            "reference": "NASA/JPL Planetary Fact Sheet and IAU nominal values",
            "notes": entry["notes"],
        }
        star["planets"].append(enrich_planet(planet, star))

    return _finalise_star(star)
