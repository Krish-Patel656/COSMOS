"""Tests for the science engine.

These assert against *published* values wherever one exists — Kopparapu's
habitable zone edges for the Sun, Schulze-Makuch's ESI figures for the Solar
System planets — so that a refactor that quietly changes the physics fails here
rather than silently shipping wrong numbers to users.
"""

from __future__ import annotations

import math

import pytest

from app.science import astro
from app.science.appearance import derive_appearance, star_color_hex
from app.science.constants import (
    EARTH_DENSITY_G_CM3,
    EARTH_ESCAPE_VELOCITY_KM_S,
    EARTH_SURFACE_GRAVITY_MS2,
)
from app.science.esi import compute_esi
from app.science.habitability import (
    FACTOR_WEIGHTS,
    MINIMUM_SCORABLE_WEIGHT,
    PlanetInput,
    classify_size,
    compute_habitability,
)
from app.science.habitable_zone import effective_flux_limit, habitable_zone

# --- Derived quantities ---------------------------------------------------


class TestAstro:
    def test_earth_bulk_properties_reproduce_constants(self):
        assert astro.density_g_cm3(1.0, 1.0) == pytest.approx(EARTH_DENSITY_G_CM3)
        assert astro.escape_velocity_km_s(1.0, 1.0) == pytest.approx(
            EARTH_ESCAPE_VELOCITY_KM_S
        )
        assert astro.surface_gravity_ms2(1.0, 1.0) == pytest.approx(
            EARTH_SURFACE_GRAVITY_MS2
        )

    def test_keplers_third_law_places_earth_at_one_au(self):
        assert astro.semi_major_axis_au(365.25, 1.0) == pytest.approx(1.0, rel=1e-3)

    def test_keplers_third_law_scales_with_stellar_mass(self):
        """A 6-day orbit around a 0.09 Msun star sits at ~0.029 AU (TRAPPIST-1 e)."""
        assert astro.semi_major_axis_au(6.10, 0.0898) == pytest.approx(0.0292, abs=0.001)

    def test_solar_luminosity_is_unity(self):
        assert astro.stellar_luminosity_solar(1.0, 5772.0) == pytest.approx(1.0, rel=1e-3)

    def test_earth_equilibrium_temperature(self):
        """With a Bond albedo of 0.3, Earth's equilibrium temperature is ~255 K."""
        temp = astro.equilibrium_temperature_k(5772.0, 1.0, 1.0, bond_albedo=0.3)
        assert temp == pytest.approx(255.0, abs=2.0)

    def test_insolation_falls_as_inverse_square(self):
        assert astro.insolation_earth_units(1.0, 2.0) == pytest.approx(0.25)

    def test_mass_radius_relation_round_trips(self):
        for mass in (0.1, 0.5, 1.0, 2.0, 10.0, 100.0):
            radius = astro.radius_from_mass_earth_units(mass)
            assert astro.mass_from_radius_earth_units(radius) == pytest.approx(mass, rel=1e-6)

    def test_mass_radius_relation_is_continuous_at_regime_boundaries(self):
        """The piecewise Forecaster fit must not jump at its break points."""
        for boundary in (2.04, 131.6):
            below = astro.radius_from_mass_earth_units(boundary * 0.9999)
            above = astro.radius_from_mass_earth_units(boundary * 1.0001)
            assert below == pytest.approx(above, rel=1e-3)

    @pytest.mark.parametrize(
        ("temp", "expected"),
        [(5772, "G"), (3200, "M"), (4500, "K"), (6500, "F"), (9000, "A"), (20000, "B")],
    )
    def test_spectral_classification(self, temp, expected):
        assert astro.classify_spectral_type(temp) == expected

    def test_missing_inputs_return_none_rather_than_raising(self):
        """Real catalogue rows are full of gaps; the helpers must tolerate them."""
        assert astro.density_g_cm3(None, 1.0) is None
        assert astro.semi_major_axis_au(365.0, None) is None
        assert astro.stellar_luminosity_solar(1.0, 0) is None
        assert astro.escape_velocity_km_s(-1.0, 1.0) is None

    def test_short_period_planets_are_tidally_locked(self):
        assert astro.transit_tidal_locking_likelihood(2.0, 0.1) == 1.0
        assert astro.transit_tidal_locking_likelihood(365.0, 1.0) == 0.0


# --- Habitable zone -------------------------------------------------------


class TestHabitableZone:
    def test_sun_edges_match_kopparapu_2014(self):
        """Published values: conservative 0.99-1.70 AU, optimistic 0.75-1.77 AU."""
        zone = habitable_zone(5772.0, 1.0, 1.0)
        assert zone is not None
        assert zone.runaway_greenhouse_au == pytest.approx(0.99, abs=0.02)
        assert zone.maximum_greenhouse_au == pytest.approx(1.70, abs=0.02)
        assert zone.recent_venus_au == pytest.approx(0.75, abs=0.02)
        assert zone.early_mars_au == pytest.approx(1.77, abs=0.02)

    def test_earth_is_inside_and_venus_outside(self):
        zone = habitable_zone(5772.0, 1.0, 1.0)
        assert zone.contains(1.0)
        assert not zone.contains(0.723)
        assert not zone.contains(0.723, optimistic=True)

    def test_cooler_stars_have_closer_zones(self):
        sun = habitable_zone(5772.0, 1.0, 1.0)
        dwarf = habitable_zone(3200.0, 0.01, 1.0)
        assert dwarf.runaway_greenhouse_au < 0.2 < sun.runaway_greenhouse_au

    def test_flux_and_distance_membership_agree_when_self_consistent(self):
        """With a luminosity-consistent flux, both comparisons must agree."""
        zone = habitable_zone(5772.0, 1.0, 1.0)
        for axis in (0.6, 0.9, 1.0, 1.5, 2.0):
            flux = 1.0 / axis**2
            assert zone.contains(axis) == zone.contains_flux(flux)

    def test_more_massive_planets_push_the_inner_edge_inward(self):
        """Higher gravity means a drier stratosphere and less water loss."""
        light = effective_flux_limit("runaway_greenhouse", 5772.0, 0.5)
        heavy = effective_flux_limit("runaway_greenhouse", 5772.0, 5.0)
        assert heavy > light

    def test_out_of_range_temperature_is_flagged_not_silently_extrapolated(self):
        zone = habitable_zone(2000.0, 0.001, 1.0)
        assert zone.extrapolated is True
        assert habitable_zone(5772.0, 1.0, 1.0).extrapolated is False

    def test_unconstrained_star_yields_no_zone(self):
        assert habitable_zone(None, 1.0) is None
        assert habitable_zone(5772.0, None) is None

    def test_unknown_boundary_name_is_rejected(self):
        with pytest.raises(ValueError, match="unknown habitable zone boundary"):
            effective_flux_limit("goldilocks", 5772.0)


# --- Earth Similarity Index ----------------------------------------------


class TestEsi:
    def test_earth_scores_exactly_one(self):
        result = compute_esi(1.0, 1.0, 255.0)
        assert result.overall == pytest.approx(1.0, abs=1e-9)
        assert result.interior == pytest.approx(1.0, abs=1e-9)
        assert result.surface == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize(
        ("name", "radius", "mass", "surface_temp", "published"),
        [
            # Schulze-Makuch et al. (2011) / PHL published ESI values.
            ("Venus", 0.949, 0.815, 737.0, 0.44),
            ("Mars", 0.532, 0.107, 210.0, 0.70),
            ("Mercury", 0.383, 0.055, 440.0, 0.60),
            ("Jupiter", 11.209, 317.83, 165.0, 0.29),
        ],
    )
    def test_solar_system_matches_published_values(
        self, name, radius, mass, surface_temp, published
    ):
        result = compute_esi(
            radius, mass, surface_temp, temperature_is_equilibrium=False
        )
        assert result.overall == pytest.approx(published, abs=0.06), name

    def test_score_is_bounded(self):
        extreme = compute_esi(30.0, 5000.0, 4000.0)
        assert 0.0 <= extreme.overall <= 1.0

    def test_missing_temperature_leaves_overall_undefined(self):
        """A missing property makes the product meaningless, not merely smaller."""
        result = compute_esi(1.0, 1.0, None)
        assert result.overall is None
        assert result.interior is not None
        assert result.surface is None

    def test_relation_derived_mass_is_flagged_and_lowers_completeness(self):
        measured = compute_esi(1.0, 1.0, 255.0)
        modelled = compute_esi(1.0, 1.0, 255.0, mass_is_estimated=True)
        assert measured.data_completeness > modelled.data_completeness
        assert any(c.estimated for c in modelled.components if c.key == "density")
        # The similarity value itself is unchanged; only its provenance differs.
        assert measured.overall == pytest.approx(modelled.overall)

    def test_equilibrium_and_surface_references_differ(self):
        """288 K is Earth-like as a surface temperature but hot as an equilibrium one."""
        as_surface = compute_esi(1.0, 1.0, 288.0, temperature_is_equilibrium=False)
        as_equilibrium = compute_esi(1.0, 1.0, 288.0, temperature_is_equilibrium=True)
        assert as_surface.overall > as_equilibrium.overall


# --- Habitability ---------------------------------------------------------


def _planet(**overrides) -> PlanetInput:
    base = {
        "radius_earth": 1.0,
        "mass_earth": 1.0,
        "equilibrium_temp_k": 255.0,
        "orbital_period_days": 365.25,
        "semi_major_axis_au": 1.0,
        "eccentricity": 0.0167,
        "insolation_earth": 1.0,
        "star_effective_temp_k": 5772.0,
        "star_radius_solar": 1.0,
        "star_mass_solar": 1.0,
        "star_age_gyr": 4.6,
    }
    base.update(overrides)
    return PlanetInput(**base)


class TestHabitability:
    def test_weights_sum_to_one(self):
        assert sum(FACTOR_WEIGHTS.values()) == pytest.approx(1.0)

    def test_earth_scores_one_hundred(self):
        result = compute_habitability(_planet())
        assert result.score == pytest.approx(100.0, abs=0.5)
        assert result.band == "exceptional candidate"
        assert result.in_conservative_hz is True

    def test_solar_system_ordering_is_physically_sensible(self):
        earth = compute_habitability(_planet()).score
        mars = compute_habitability(
            _planet(
                radius_earth=0.532,
                mass_earth=0.107,
                equilibrium_temp_k=210.0,
                semi_major_axis_au=1.524,
                insolation_earth=0.431,
                orbital_period_days=687.0,
                eccentricity=0.0934,
            )
        ).score
        venus = compute_habitability(
            _planet(
                radius_earth=0.949,
                mass_earth=0.815,
                equilibrium_temp_k=227.0,
                semi_major_axis_au=0.723,
                insolation_earth=1.911,
                orbital_period_days=224.7,
                eccentricity=0.0068,
            )
        ).score
        jupiter = compute_habitability(
            _planet(
                radius_earth=11.21,
                mass_earth=317.8,
                equilibrium_temp_k=110.0,
                semi_major_axis_au=5.204,
                insolation_earth=0.0369,
                orbital_period_days=4333.0,
            )
        ).score
        assert earth > mars > venus > jupiter

    def test_a_single_fatal_flaw_dominates(self):
        """Mars-like gravity must sink an otherwise perfect world.

        This is why the factors combine geometrically: an arithmetic mean would
        rate a planet that cannot hold an atmosphere as a promising candidate.
        """
        result = compute_habitability(_planet(radius_earth=0.4, mass_earth=0.05))
        atmosphere = next(f for f in result.factors if f.key == "atmosphere_retention")
        assert atmosphere.score < 0.2
        assert result.score < 55

    def test_venus_fails_only_on_habitable_zone_position(self):
        """The signature case: physically Earth-like, fatally misplaced."""
        result = compute_habitability(
            _planet(
                radius_earth=0.949,
                mass_earth=0.815,
                equilibrium_temp_k=227.0,
                semi_major_axis_au=0.723,
                insolation_earth=1.911,
            )
        )
        by_key = {f.key: f for f in result.factors}
        assert by_key["habitable_zone"].score == pytest.approx(0.0, abs=0.01)
        assert by_key["size"].score == pytest.approx(1.0)
        assert by_key["composition"].score == pytest.approx(1.0)
        assert "runaway greenhouse" in by_key["habitable_zone"].explanation

    def test_unconstrained_planet_gets_no_score(self):
        """A microlensing-style detection must be refused, not scored at 100.

        Without a temperature or a habitable-zone position, the only evaluable
        factors all derive from the mass-radius relation and all come out
        Earth-like, which would otherwise produce a perfect score for a planet we
        know essentially nothing about.
        """
        result = compute_habitability(
            PlanetInput(radius_earth=1.2, mass_earth=1.9, semi_major_axis_au=1.9)
        )
        assert result.score is None
        assert result.band == "insufficient data"
        assert any("microlensing" in caveat for caveat in result.caveats)

    def test_gate_threshold_is_respected(self):
        """Having a temperature alone is below the weight floor."""
        result = compute_habitability(PlanetInput(equilibrium_temp_k=255.0))
        assert FACTOR_WEIGHTS["temperature"] < MINIMUM_SCORABLE_WEIGHT
        assert result.score is None

    def test_every_factor_carries_an_explanation(self):
        result = compute_habitability(_planet())
        assert len(result.factors) == len(FACTOR_WEIGHTS)
        for factor in result.factors:
            assert factor.explanation.strip()
            assert factor.explanation.rstrip().endswith((".", "!"))
            assert factor.verdict in {
                "ideal",
                "favourable",
                "marginal",
                "poor",
                "hostile",
                "unknown",
            }

    def test_confidence_drops_when_inputs_are_modelled(self):
        measured = compute_habitability(_planet())
        modelled = compute_habitability(_planet(mass_earth=None))
        assert modelled.confidence < measured.confidence
        assert any("mass-radius" in caveat for caveat in modelled.caveats)

    def test_flux_is_preferred_over_distance_for_zone_membership(self):
        """When catalogued flux and distance disagree, flux wins.

        This is the Kepler-186 f case: the archive's stellar radius and its
        planetary insolation come from different publications, and only the flux
        comparison reproduces the published conclusion that the planet is inside
        the habitable zone.
        """
        result = compute_habitability(
            _planet(
                semi_major_axis_au=0.432,
                insolation_earth=0.30,
                equilibrium_temp_k=250.0,
                star_effective_temp_k=3788.0,
                star_radius_solar=0.472,
                star_mass_solar=0.478,
                star_luminosity_solar=0.0412,
                orbital_period_days=129.9,
            )
        )
        assert result.in_conservative_hz is True

    def test_m_dwarf_hosts_are_penalised_but_not_disqualified(self):
        sun_like = compute_habitability(_planet())
        m_dwarf = compute_habitability(
            _planet(star_effective_temp_k=3000.0, star_radius_solar=0.15)
        )
        by_key = {f.key: f for f in m_dwarf.factors}
        assert 0.2 < by_key["host_star"].score < 0.6
        assert m_dwarf.score < sun_like.score
        assert m_dwarf.score > 40

    def test_tidally_locked_worlds_are_not_written_off(self):
        # A 2-day orbit around a 0.12 Msun star is well inside the radius where
        # locking is certain, so the factor bottoms out at its floor of 0.45.
        locked = compute_habitability(
            _planet(orbital_period_days=2.0, star_mass_solar=0.12)
        )
        by_key = {f.key: f for f in locked.factors}
        assert by_key["tidal_locking"].score == pytest.approx(0.45, abs=0.01)
        assert "climate models" in by_key["tidal_locking"].explanation.lower()

    def test_score_never_leaves_its_range(self):
        for radius, mass, temp, axis in [
            (0.1, 0.001, 5.0, 0.001),
            (30.0, 9000.0, 5000.0, 400.0),
            (1.0, 1.0, 255.0, 1.0),
        ]:
            result = compute_habitability(
                _planet(radius_earth=radius, mass_earth=mass, equilibrium_temp_k=temp,
                        semi_major_axis_au=axis, insolation_earth=1.0 / axis**2)
            )
            if result.score is not None:
                assert 0.0 <= result.score <= 100.0
            assert 0.0 <= result.confidence <= 1.0

    def test_summary_names_the_limiting_factors(self):
        result = compute_habitability(_planet(radius_earth=0.4, mass_earth=0.05))
        assert "held back by" in result.summary

    @pytest.mark.parametrize(
        ("radius", "expected"),
        [
            (0.4, "Sub-Earth"),
            (1.0, "Earth-sized"),
            (1.4, "Super-Earth"),
            (1.8, "Radius-valley world"),
            (3.0, "Sub-Neptune"),
            (5.0, "Neptune-like"),
            (11.0, "Gas giant"),
        ],
    )
    def test_size_classification(self, radius, expected):
        assert classify_size(radius, None) == expected


# --- Appearance -----------------------------------------------------------


class TestAppearance:
    @pytest.mark.parametrize(
        ("radius", "temp", "expected"),
        [
            (1.0, 1500.0, "lava"),
            (1.0, 800.0, "scorched"),
            (1.0, 400.0, "desert"),
            (1.0, 270.0, "terrestrial"),
            (1.0, 200.0, "tundra"),
            (1.0, 100.0, "ice"),
            (5.0, 200.0, "sub_neptune"),
            (11.0, 150.0, "gas_giant"),
        ],
    )
    def test_surface_type_follows_size_then_temperature(self, radius, temp, expected):
        assert derive_appearance(radius, None, temp).surface_type == expected

    def test_appearance_is_always_labelled_artistic(self):
        """No exoplanet surface has ever been imaged; the UI must be able to say so."""
        appearance = derive_appearance(1.0, 1.0, 288.0)
        assert appearance.is_artistic is True
        assert appearance.basis, "appearance must cite the properties that drove it"

    def test_unknown_temperature_yields_unknown_surface(self):
        assert derive_appearance(1.0, 1.0, None).surface_type == "unknown"

    def test_star_colour_runs_blue_to_red(self):
        assert star_color_hex(30000) != star_color_hex(3000)
        assert star_color_hex(None) == star_color_hex(5772)
        for temp in (2000, 3500, 5772, 9000, 40000):
            assert re_hex(star_color_hex(temp))

    def test_jupiter_does_not_get_saturn_rings(self):
        look = derive_appearance(11.209, 317.83, 110.0, 0.037, 1.33)
        assert look.surface_type == "gas_giant"
        assert look.has_rings is False

    def test_saturn_keeps_rings(self):
        look = derive_appearance(9.449, 95.159, 81.0, 0.011, 0.69)
        assert look.surface_type == "gas_giant"
        assert look.has_rings is True

    def test_hot_jupiter_does_not_get_rings(self):
        look = derive_appearance(12.0, 220.0, 1400.0, 800.0, 0.7)
        assert look.has_rings is False


def re_hex(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("#")
        and len(value) == 7
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )


def test_smoothstep_curves_are_monotonic():
    """Guards the shared easing used by every scoring curve."""
    from app.science.habitability import _plateau

    rising = [_plateau(x / 100.0, 0.8, 1.0, 0.0, 2.0) for x in range(0, 81)]
    assert all(b >= a - 1e-9 for a, b in zip(rising, rising[1:], strict=False))
    assert _plateau(0.9, 0.8, 1.0, 0.0, 2.0) == 1.0
    assert _plateau(-1.0, 0.8, 1.0, 0.0, 2.0) == 0.0
    assert math.isclose(_plateau(2.0, 0.8, 1.0, 0.0, 2.0), 0.0)
