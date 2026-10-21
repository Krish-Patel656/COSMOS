"""Tests for normalisation and ingestion.

The unit-conversion and provenance assertions here guard the two failure modes
that would corrupt everything downstream without raising: mixing Jupiter and
Earth units, and treating the archive's log-scale luminosity as linear.
"""

from __future__ import annotations

import gzip
import json

import pytest

from app.ingest import nasa
from app.ingest.normalize import (
    build_solar_system,
    equatorial_to_cartesian,
    normalize_rows,
)
from app.ingest.pipeline import read_snapshot, write_snapshot
from app.science.constants import (
    JUPITER_MASSES_IN_EARTH_MASSES,
    JUPITER_RADII_IN_EARTH_RADII,
)


class TestNormalisation:
    def test_rows_group_into_systems(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        by_name = {star["name"]: star for star in stars}
        assert set(by_name) == {"Testaris", "OGLE-TEST-9999L"}
        assert len(by_name["Testaris"]["planets"]) == 2

    def test_jupiter_units_are_converted_when_earth_columns_are_blank(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        planet = next(
            p for s in stars for p in s["planets"] if p["name"] == "Testaris c"
        )
        assert planet["radius_earth"] == pytest.approx(1.1 * JUPITER_RADII_IN_EARTH_RADII)
        assert planet["mass_earth"] == pytest.approx(2.4 * JUPITER_MASSES_IN_EARTH_MASSES)

    def test_both_unit_systems_are_always_populated(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        for star in stars:
            for planet in star["planets"]:
                if planet["radius_earth"] is not None:
                    assert planet["radius_jupiter"] is not None
                if planet["mass_earth"] is not None:
                    assert planet["mass_jupiter"] is not None

    def test_stellar_luminosity_is_read_as_log10(self, fixture_rows):
        """st_lum is log10(L/Lsun); reading it linearly would break every zone."""
        stars = normalize_rows(fixture_rows)
        testaris = next(s for s in stars if s["name"] == "Testaris")
        assert testaris["luminosity_solar"] == pytest.approx(10**-0.13, rel=1e-6)

    def test_missing_luminosity_falls_back_to_stefan_boltzmann(self):
        rows = [
            {
                "pl_name": "X b",
                "hostname": "X",
                "st_teff": "5772",
                "st_rad": "1.0",
                "st_lum": None,
                "sy_pnum": "1",
                "sy_snum": "1",
            }
        ]
        star = normalize_rows(rows)[0]
        assert star["luminosity_solar"] == pytest.approx(1.0, rel=1e-3)

    def test_minimum_mass_provenance_is_flagged(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        planet = next(p for s in stars for p in s["planets"] if p["name"] == "Testaris c")
        assert planet["mass_is_minimum"] is True

    def test_archive_derived_mass_is_flagged_as_estimated(self, fixture_rows):
        """'M-R relationship' provenance means modelled, not measured."""
        stars = normalize_rows(fixture_rows)
        planet = next(
            p for s in stars for p in s["planets"] if p["name"] == "OGLE-TEST-9999L b"
        )
        assert planet["mass_is_estimated"] is True

    def test_measured_mass_is_not_flagged(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        planet = next(p for s in stars for p in s["planets"] if p["name"] == "Testaris b")
        assert planet["mass_is_estimated"] is False
        assert planet["mass_is_minimum"] is False

    def test_semi_major_axis_is_derived_when_absent(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        planet = next(p for s in stars for p in s["planets"] if p["name"] == "Testaris c")
        assert planet["semi_major_axis_au"] is not None
        assert planet["axis_is_estimated"] is True

    def test_unconstrained_planet_is_left_unscored(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        planet = next(
            p for s in stars for p in s["planets"] if p["name"] == "OGLE-TEST-9999L b"
        )
        assert planet["habitability_score"] is None
        assert planet["habitability_band"] == "insufficient data"

    def test_slugs_are_url_safe_and_unique(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        slugs = [p["slug"] for s in stars for p in s["planets"]]
        assert len(slugs) == len(set(slugs))
        for slug in slugs:
            assert slug == slug.lower()
            assert " " not in slug

    def test_duplicate_names_are_disambiguated(self):
        rows = [
            {"pl_name": "Dup b", "hostname": "Dup", "sy_pnum": "1", "sy_snum": "1"},
            {"pl_name": "Dup b", "hostname": "Dup 2", "sy_pnum": "1", "sy_snum": "1"},
        ]
        stars = normalize_rows(rows)
        slugs = sorted(p["slug"] for s in stars for p in s["planets"])
        assert slugs == ["dup-b", "dup-b-2"]

    def test_rows_without_names_are_skipped(self):
        rows = [
            {"pl_name": None, "hostname": "Nameless", "sy_pnum": "1"},
            {"pl_name": "Fine b", "hostname": "Fine", "sy_pnum": "1", "sy_snum": "1"},
        ]
        assert len(normalize_rows(rows)) == 1

    def test_system_aggregates_take_the_best_planet(self, fixture_rows):
        stars = normalize_rows(fixture_rows)
        testaris = next(s for s in stars if s["name"] == "Testaris")
        scores = [
            p["habitability_score"]
            for p in testaris["planets"]
            if p["habitability_score"] is not None
        ]
        assert testaris["best_habitability_score"] == max(scores)


class TestCoordinates:
    def test_cartesian_conversion_preserves_distance(self):
        x, y, z = equatorial_to_cartesian(123.4, -45.6, 10.0)
        assert (x**2 + y**2 + z**2) ** 0.5 == pytest.approx(10.0)

    def test_north_pole_lies_on_the_z_axis(self):
        x, y, z = equatorial_to_cartesian(0.0, 90.0, 5.0)
        assert z == pytest.approx(5.0)
        assert x == pytest.approx(0.0, abs=1e-12)
        assert y == pytest.approx(0.0, abs=1e-12)

    def test_missing_inputs_yield_no_position(self):
        assert equatorial_to_cartesian(None, 0.0, 1.0) == (None, None, None)
        assert equatorial_to_cartesian(0.0, 0.0, None) == (None, None, None)


class TestSolarSystem:
    def test_all_eight_planets_are_present_and_scored(self):
        sun = build_solar_system()
        assert len(sun["planets"]) == 8
        assert sun["is_solar_system"] is True
        assert sun["slug"] == "sun"
        for planet in sun["planets"]:
            assert planet["habitability_score"] is not None

    def test_earth_tops_the_solar_system(self):
        sun = build_solar_system()
        by_name = {p["name"]: p for p in sun["planets"]}
        assert by_name["Earth"]["habitability_score"] == pytest.approx(100.0, abs=0.5)
        assert by_name["Earth"]["esi"] == pytest.approx(1.0, abs=1e-6)
        best = max(p["habitability_score"] for p in sun["planets"])
        assert by_name["Earth"]["habitability_score"] == best

    def test_sun_sits_at_the_origin_of_the_map(self):
        sun = build_solar_system()
        assert (sun["x_pc"], sun["y_pc"], sun["z_pc"]) == (0.0, 0.0, 0.0)

    def test_surface_temperatures_are_retained_for_esi(self):
        """Venus's 737 K surface, not its 227 K equilibrium value, drives its ESI."""
        sun = build_solar_system()
        venus = next(p for p in sun["planets"] if p["name"] == "Venus")
        assert venus["esi"] < 0.6


class TestSnapshot:
    def test_round_trip(self, tmp_path, fixture_rows):
        target = tmp_path / "snap.json.gz"
        write_snapshot(fixture_rows, target)
        assert read_snapshot(target) == fixture_rows

    def test_snapshot_records_provenance(self, tmp_path, fixture_rows):
        target = tmp_path / "snap.json.gz"
        write_snapshot(fixture_rows, target)
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["row_count"] == len(fixture_rows)
        assert payload["source"].startswith("NASA Exoplanet Archive")
        assert payload["retrieved_at"]

    def test_snapshot_is_byte_stable_for_identical_content(self, tmp_path, fixture_rows):
        """Re-ingesting must not produce a spurious git diff."""
        a, b = tmp_path / "a.gz", tmp_path / "b.gz"
        write_snapshot(fixture_rows, a)
        write_snapshot(fixture_rows, b)
        assert a.read_bytes() == b.read_bytes()


class TestNotableCatalogue:
    def test_includes_flagship_habitable_zone_worlds(self):
        from app.ingest.notable import catalogue_rows

        rows = catalogue_rows()
        names = {row["pl_name"] for row in rows}
        assert "TRAPPIST-1 e" in names
        assert "Kepler-186 f" in names
        assert "Proxima Cen b" in names
        hosts = {row["hostname"] for row in rows}
        assert "TRAPPIST-1" in hosts
        for row in rows:
            assert row["pl_name"]
            assert row["hostname"]


class TestArchiveQuery:
    def test_query_requests_only_known_columns(self):
        query = nasa.build_query()
        assert "from pscomppars" in query
        for column in nasa.COLUMNS:
            assert column in query

    def test_rowupdate_is_not_requested(self):
        """`rowupdate` exists on `ps` but not `pscomppars`; asking for it 400s."""
        assert "rowupdate" not in nasa.build_query()

    def test_row_limit_becomes_a_top_clause(self):
        assert "top 25" in nasa.build_query(row_limit=25)
