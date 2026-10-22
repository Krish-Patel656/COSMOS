"""End-to-end API tests against the seeded fixture catalogue."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

V1 = "/api/v1"


class TestMeta:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_openapi_schema_is_valid(self, client: AsyncClient):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"]


class TestStats:
    async def test_counts_and_ranges(self, client: AsyncClient):
        response = await client.get(f"{V1}/stats")
        assert response.status_code == 200
        body = response.json()
        assert body["planet_count"] == 11  # 8 Solar System + 3 fixtures
        assert body["star_count"] == 3
        assert body["scored_planet_count"] == 10  # the microlensing row is unscored
        assert body["ranges"]["radius_earth"]["max"] > 1.0
        assert body["data_source"].startswith("NASA Exoplanet Archive")

    async def test_ranges_cover_every_slider(self, client: AsyncClient):
        body = (await client.get(f"{V1}/stats")).json()
        for key in ("radius_earth", "mass_earth", "equilibrium_temp_k", "esi"):
            assert key in body["ranges"]


class TestPlanets:
    async def test_list_defaults_to_habitability_order(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets")).json()
        scores = [p["habitability_score"] for p in body["items"] if p["habitability_score"]]
        assert scores == sorted(scores, reverse=True)
        assert body["items"][0]["name"] == "Earth"

    async def test_unknown_values_always_sort_last(self, client: AsyncClient):
        """Ascending order must not lead with nulls."""
        body = (await client.get(f"{V1}/planets?sort=temperature&order=asc&limit=50")).json()
        temps = [p["equilibrium_temp_k"] for p in body["items"]]
        known = [t for t in temps if t is not None]
        assert temps[: len(known)] == known
        assert known == sorted(known)

    async def test_pagination_is_stable_and_consistent(self, client: AsyncClient):
        first = (await client.get(f"{V1}/planets?limit=4&offset=0")).json()
        second = (await client.get(f"{V1}/planets?limit=4&offset=4")).json()
        assert first["total"] == second["total"] == 11
        assert first["has_more"] is True
        slugs = {p["slug"] for p in first["items"]} & {p["slug"] for p in second["items"]}
        assert not slugs, "pages must not overlap"

    @pytest.mark.parametrize(
        ("query", "predicate"),
        [
            ("max_radius=1.1", lambda p: p["radius_earth"] <= 1.1),
            ("min_temp=250", lambda p: p["equilibrium_temp_k"] >= 250),
            ("min_esi=0.5", lambda p: p["esi"] >= 0.5),
            ("in_conservative_hz=true", lambda p: p["in_conservative_hz"] is True),
            ("has_habitability_score=true", lambda p: p["habitability_score"] is not None),
            ("discovery_method=Transit", lambda p: p["discovery_method"] == "Transit"),
        ],
    )
    async def test_filters_are_honoured(self, client: AsyncClient, query, predicate):
        body = (await client.get(f"{V1}/planets?{query}&limit=50")).json()
        assert body["items"], f"filter {query} returned nothing"
        assert all(predicate(p) for p in body["items"])

    async def test_solar_system_can_be_excluded(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets?include_solar_system=false&limit=50")).json()
        assert body["total"] == 3
        assert all(p["is_solar_system"] is False for p in body["items"])

    async def test_measured_mass_filter_excludes_modelled_values(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets?has_measured_mass=true&limit=50")).json()
        assert all(p["mass_is_estimated"] is False for p in body["items"])
        assert all(p["mass_earth"] is not None for p in body["items"])

    async def test_name_search_matches_host_as_well_as_planet(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets?q=testaris&limit=50")).json()
        assert body["total"] == 2

    async def test_detail_includes_full_breakdowns(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets/earth")).json()
        assert body["name"] == "Earth"
        assert body["habitability"]["score"] == pytest.approx(100.0, abs=0.5)
        assert len(body["habitability"]["factors"]) == 8
        assert body["esi_detail"]["overall"] == pytest.approx(1.0, abs=1e-6)
        assert body["star"]["name"] == "Sun"
        for factor in body["habitability"]["factors"]:
            assert factor["explanation"]
            assert factor["weight"] > 0

    async def test_detail_includes_artistic_appearance_flag(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets/earth")).json()
        assert body["appearance"]["is_artistic"] is True
        assert body["appearance"]["base_color"].startswith("#")

    async def test_unknown_slug_is_404(self, client: AsyncClient):
        assert (await client.get(f"{V1}/planets/planet-nine")).status_code == 404

    async def test_similar_excludes_itself(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets/earth/similar?limit=3")).json()
        assert all(p["slug"] != "earth" for p in body)

    async def test_siblings_are_ordered_outward(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets/earth/system")).json()
        axes = [p["semi_major_axis_au"] for p in body]
        assert axes == sorted(axes)
        assert [p["name"] for p in body][:3] == ["Mercury", "Venus", "Earth"]

    async def test_random_returns_a_characterised_planet(self, client: AsyncClient):
        body = (await client.get(f"{V1}/planets/random")).json()
        assert body["habitability_score"] is not None
        assert body["radius_earth"] is not None

    async def test_invalid_filter_value_is_rejected(self, client: AsyncClient):
        assert (await client.get(f"{V1}/planets?min_esi=5")).status_code == 422
        assert (await client.get(f"{V1}/planets?limit=9999")).status_code == 422


class TestSystems:
    async def test_system_detail_bundles_planets(self, client: AsyncClient):
        body = (await client.get(f"{V1}/systems/sun")).json()
        assert body["name"] == "Sun"
        assert len(body["planets"]) == 8
        assert body["habitable_zone"]["runaway_greenhouse_au"] == pytest.approx(0.99, abs=0.02)

    async def test_system_planets_are_ordered_outward(self, client: AsyncClient):
        body = (await client.get(f"{V1}/systems/sun")).json()
        axes = [p["semi_major_axis_au"] for p in body["planets"]]
        assert axes == sorted(axes)

    async def test_stellar_map_is_trimmed_and_anchored_at_the_sun(self, client: AsyncClient):
        body = (await client.get(f"{V1}/stars/map?max_distance_ly=100&limit=50")).json()
        assert any(star["is_solar_system"] for star in body)
        sun = next(s for s in body if s["is_solar_system"])
        assert (sun["x_pc"], sun["y_pc"], sun["z_pc"]) == (0.0, 0.0, 0.0)
        # The map payload must stay minimal — no score breakdowns.
        assert "habitability_breakdown" not in body[0]

    async def test_stellar_map_includes_the_sun_even_when_filtered_out(
        self, client: AsyncClient
    ):
        body = (await client.get(f"{V1}/stars/map?max_distance_ly=1&limit=10")).json()
        assert any(star["is_solar_system"] for star in body)

    async def test_system_listing_filters_and_sorts(self, client: AsyncClient):
        body = (await client.get(f"{V1}/systems?min_planets=2&sort=planet_count&order=desc")).json()
        assert body["items"][0]["name"] == "Sun"
        assert all(s["planet_count"] >= 2 for s in body["items"])

    async def test_unknown_system_is_404(self, client: AsyncClient):
        assert (await client.get(f"{V1}/systems/nowhere")).status_code == 404


class TestSearch:
    async def test_system_outranks_its_own_planets(self, client: AsyncClient):
        body = (await client.get(f"{V1}/search?q=Testaris")).json()
        assert body["hits"][0]["kind"] == "star"
        assert body["hits"][0]["slug"] == "testaris"

    async def test_exact_match_wins(self, client: AsyncClient):
        body = (await client.get(f"{V1}/search?q=Earth")).json()
        assert body["hits"][0]["slug"] == "earth"

    async def test_kind_filter(self, client: AsyncClient):
        body = (await client.get(f"{V1}/search?q=Testaris&kind=planet")).json()
        assert body["hits"]
        assert all(hit["kind"] == "planet" for hit in body["hits"])

    async def test_no_match_returns_empty_not_error(self, client: AsyncClient):
        body = (await client.get(f"{V1}/search?q=zzzznotathing")).json()
        assert body["hits"] == []

    async def test_hits_carry_a_subtitle_for_display(self, client: AsyncClient):
        body = (await client.get(f"{V1}/search?q=Earth")).json()
        assert body["hits"][0]["subtitle"]


class TestHighlights:
    async def test_sections_are_populated(self, client: AsyncClient):
        body = (await client.get(f"{V1}/highlights?per_section=4")).json()
        keys = {section["key"] for section in body["sections"]}
        assert {"most-earth-like", "potentially-habitable", "nearby", "solar-system"} <= keys
        for section in body["sections"]:
            assert section["title"] and section["description"]

    async def test_solar_system_section_contains_only_our_planets(self, client: AsyncClient):
        body = (await client.get(f"{V1}/highlights")).json()
        section = next(s for s in body["sections"] if s["key"] == "solar-system")
        assert section["planets"]
        assert all(p["is_solar_system"] for p in section["planets"])

    async def test_other_sections_exclude_the_solar_system(self, client: AsyncClient):
        body = (await client.get(f"{V1}/highlights")).json()
        section = next(s for s in body["sections"] if s["key"] == "nearby")
        assert all(not p["is_solar_system"] for p in section["planets"])


class TestCompare:
    async def test_table_is_built_in_requested_order(self, client: AsyncClient):
        response = await client.get(f"{V1}/compare?slugs=earth&slugs=mars&slugs=venus")
        assert response.status_code == 200
        body = response.json()
        assert [p["name"] for p in body["planets"]] == ["Earth", "Mars", "Venus"]
        assert body["rows"]
        for row in body["rows"]:
            assert len(row["values"]) == 3
            assert row["better"] in {"higher", "lower", "closer_to_earth", "none"}

    async def test_rows_with_no_data_at_all_are_omitted(self, client: AsyncClient):
        body = (await client.get(f"{V1}/compare?slugs=earth&slugs=mars")).json()
        for row in body["rows"]:
            assert any(value is not None for value in row["values"])

    async def test_notes_surface_data_quality_caveats(self, client: AsyncClient):
        body = (
            await client.get(f"{V1}/compare?slugs=earth&slugs=ogle-test-9999l-b")
        ).json()
        joined = " ".join(body["notes"])
        assert "mass-radius" in joined or "habitability score" in joined

    async def test_too_few_planets_is_rejected(self, client: AsyncClient):
        assert (await client.get(f"{V1}/compare?slugs=earth")).status_code == 422
        assert (
            await client.get(f"{V1}/compare?slugs=earth&slugs=earth")
        ).status_code == 400

    async def test_unknown_slug_is_reported(self, client: AsyncClient):
        response = await client.get(f"{V1}/compare?slugs=earth&slugs=vulcan")
        assert response.status_code == 404
        assert "vulcan" in response.json()["detail"]


class TestSimulate:
    EARTH = {
        "radius_earth": 1.0,
        "mass_earth": 1.0,
        "semi_major_axis_au": 1.0,
        "eccentricity": 0.0167,
        "star_effective_temp_k": 5772.0,
        "star_radius_solar": 1.0,
        "star_mass_solar": 1.0,
        "star_age_gyr": 4.6,
    }

    async def test_earth_parameters_score_one_hundred(self, client: AsyncClient):
        body = (await client.post(f"{V1}/simulate", json=self.EARTH)).json()
        assert body["habitability"]["score"] == pytest.approx(100.0, abs=0.5)
        assert body["derived"]["orbital_period_days"] == pytest.approx(365.25, rel=1e-2)
        assert body["derived"]["equilibrium_temp_k"] == pytest.approx(255, abs=3)

    async def test_moving_inward_triggers_the_runaway_greenhouse(self, client: AsyncClient):
        payload = {**self.EARTH, "semi_major_axis_au": 0.72}
        body = (await client.post(f"{V1}/simulate", json=payload)).json()
        assert body["habitability"]["score"] < 50
        hz = next(f for f in body["habitability"]["factors"] if f["key"] == "habitable_zone")
        assert "runaway greenhouse" in hz["explanation"]

    async def test_period_is_accepted_instead_of_distance(self, client: AsyncClient):
        payload = {k: v for k, v in self.EARTH.items() if k != "semi_major_axis_au"}
        payload["orbital_period_days"] = 365.25
        body = (await client.post(f"{V1}/simulate", json=payload)).json()
        assert body["derived"]["semi_major_axis_au"] == pytest.approx(1.0, rel=1e-2)

    async def test_baseline_comparison_reports_a_delta(self, client: AsyncClient):
        payload = {**self.EARTH, "semi_major_axis_au": 1.4, "baseline_slug": "earth"}
        body = (await client.post(f"{V1}/simulate", json=payload)).json()
        assert body["baseline"]["slug"] == "earth"
        assert body["baseline"]["delta_habitability"] <= 0

    async def test_derived_quantities_are_exposed(self, client: AsyncClient):
        body = (await client.post(f"{V1}/simulate", json=self.EARTH)).json()
        derived = body["derived"]
        assert derived["surface_gravity_g"] == pytest.approx(1.0, abs=0.01)
        assert derived["escape_velocity_km_s"] == pytest.approx(11.19, abs=0.1)
        assert derived["star_spectral_class"] == "G"

    async def test_out_of_range_input_is_rejected(self, client: AsyncClient):
        response = await client.post(f"{V1}/simulate", json={**self.EARTH, "radius_earth": 500})
        assert response.status_code == 422

    async def test_presets_are_available(self, client: AsyncClient):
        body = (await client.get(f"{V1}/simulate/presets")).json()
        keys = {preset["key"] for preset in body["presets"]}
        assert {"earth", "venus", "mars", "trappist-1e"} <= keys

    async def test_presets_all_run(self, client: AsyncClient):
        presets = (await client.get(f"{V1}/simulate/presets")).json()["presets"]
        for preset in presets:
            response = await client.post(f"{V1}/simulate", json=preset["request"])
            assert response.status_code == 200, preset["key"]


class TestAuth:
    CREDENTIALS = {
        "email": "new@example.com",
        "display_name": "New Explorer",
        "password": "Cassiopeia-77-Drift",
    }

    async def test_register_then_login(self, client: AsyncClient):
        created = await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        assert created.status_code == 201
        assert created.json()["user"]["email"] == "new@example.com"

        logged_in = await client.post(
            f"{V1}/auth/login",
            json={"email": "new@example.com", "password": self.CREDENTIALS["password"]},
        )
        assert logged_in.status_code == 200
        assert logged_in.json()["access_token"]

    async def test_duplicate_email_is_rejected(self, client: AsyncClient):
        await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        again = await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        assert again.status_code == 409

    async def test_email_is_normalised_to_lowercase(self, client: AsyncClient):
        await client.post(
            f"{V1}/auth/register", json={**self.CREDENTIALS, "email": "MiXeD@Example.com"}
        )
        response = await client.post(
            f"{V1}/auth/login",
            json={"email": "mixed@example.com", "password": self.CREDENTIALS["password"]},
        )
        assert response.status_code == 200

    async def test_wrong_password_is_unauthorised(self, client: AsyncClient):
        await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        response = await client.post(
            f"{V1}/auth/login", json={"email": "new@example.com", "password": "Wrong-Password-1"}
        )
        assert response.status_code == 401

    async def test_unknown_email_gives_the_same_error(self, client: AsyncClient):
        """Must not reveal whether an address is registered."""
        response = await client.post(
            f"{V1}/auth/login", json={"email": "ghost@example.com", "password": "Whatever-99x"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    @pytest.mark.parametrize("password", ["short", "allloweronly", "1234567890"])
    async def test_weak_passwords_are_rejected(self, client: AsyncClient, password):
        response = await client.post(
            f"{V1}/auth/register", json={**self.CREDENTIALS, "password": password}
        )
        assert response.status_code == 422

    async def test_refresh_token_mints_a_new_access_token(self, client: AsyncClient):
        created = await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        refresh = created.json()["refresh_token"]
        response = await client.post(f"{V1}/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 200
        assert response.json()["access_token"]

    async def test_access_token_is_not_accepted_as_a_refresh_token(self, client: AsyncClient):
        created = await client.post(f"{V1}/auth/register", json=self.CREDENTIALS)
        access = created.json()["access_token"]
        response = await client.post(f"{V1}/auth/refresh", json={"refresh_token": access})
        assert response.status_code == 401

    async def test_protected_route_requires_a_token(self, client: AsyncClient):
        assert (await client.get(f"{V1}/auth/me")).status_code == 401
        assert (await client.get(f"{V1}/me/favorites")).status_code == 401

    async def test_garbage_token_is_rejected(self, client: AsyncClient):
        client.headers["Authorization"] = "Bearer not-a-real-jwt"
        assert (await client.get(f"{V1}/auth/me")).status_code == 401

    async def test_me_returns_the_signed_in_user(self, auth_client: AsyncClient):
        body = (await auth_client.get(f"{V1}/auth/me")).json()
        assert body["email"] == "explorer@example.com"


class TestFavorites:
    async def test_add_list_and_remove(self, auth_client: AsyncClient):
        created = await auth_client.post(
            f"{V1}/me/favorites", json={"target_type": "planet", "target_slug": "earth"}
        )
        assert created.status_code == 201

        listed = (await auth_client.get(f"{V1}/me/favorites")).json()
        assert [f["target_slug"] for f in listed] == ["earth"]

        removed = await auth_client.delete(f"{V1}/me/favorites/planet/earth")
        assert removed.status_code == 204
        assert (await auth_client.get(f"{V1}/me/favorites")).json() == []

    async def test_adding_twice_is_idempotent(self, auth_client: AsyncClient):
        for _ in range(2):
            response = await auth_client.post(
                f"{V1}/me/favorites", json={"target_type": "planet", "target_slug": "mars"}
            )
            assert response.status_code == 201
        assert len((await auth_client.get(f"{V1}/me/favorites")).json()) == 1

    async def test_cannot_favourite_something_that_does_not_exist(
        self, auth_client: AsyncClient
    ):
        response = await auth_client.post(
            f"{V1}/me/favorites", json={"target_type": "planet", "target_slug": "tatooine"}
        )
        assert response.status_code == 404

    async def test_favourites_resolve_to_full_records(self, auth_client: AsyncClient):
        await auth_client.post(
            f"{V1}/me/favorites", json={"target_type": "planet", "target_slug": "earth"}
        )
        await auth_client.post(
            f"{V1}/me/favorites", json={"target_type": "star", "target_slug": "sun"}
        )
        planets = (await auth_client.get(f"{V1}/me/favorites/planets")).json()
        stars = (await auth_client.get(f"{V1}/me/favorites/stars")).json()
        assert [p["name"] for p in planets] == ["Earth"]
        assert [s["name"] for s in stars] == ["Sun"]

    async def test_favourites_are_scoped_to_the_owner(self, auth_client: AsyncClient):
        await auth_client.post(
            f"{V1}/me/favorites", json={"target_type": "planet", "target_slug": "earth"}
        )
        other = await auth_client.post(
            f"{V1}/auth/register",
            json={
                "email": "other@example.com",
                "display_name": "Other",
                "password": "Betelgeuse-31-Pulse",
            },
        )
        auth_client.headers["Authorization"] = f"Bearer {other.json()['access_token']}"
        assert (await auth_client.get(f"{V1}/me/favorites")).json() == []


class TestCollections:
    async def test_full_lifecycle(self, auth_client: AsyncClient):
        created = await auth_client.post(
            f"{V1}/me/collections",
            json={"name": "Worlds to watch", "description": "Shortlist", "is_public": False},
        )
        assert created.status_code == 201
        collection_id = created.json()["id"]
        assert created.json()["share_token"] is None

        added = await auth_client.post(
            f"{V1}/me/collections/{collection_id}/items",
            json={"target_type": "planet", "target_slug": "earth"},
        )
        assert [i["target_slug"] for i in added.json()["items"]] == ["earth"]

        published = await auth_client.patch(
            f"{V1}/me/collections/{collection_id}", json={"is_public": True}
        )
        assert published.json()["share_token"]

        item_id = added.json()["items"][0]["id"]
        emptied = await auth_client.delete(
            f"{V1}/me/collections/{collection_id}/items/{item_id}"
        )
        assert emptied.json()["items"] == []

        assert (
            await auth_client.delete(f"{V1}/me/collections/{collection_id}")
        ).status_code == 204

    async def test_duplicate_name_is_rejected(self, auth_client: AsyncClient):
        await auth_client.post(f"{V1}/me/collections", json={"name": "Shortlist"})
        again = await auth_client.post(f"{V1}/me/collections", json={"name": "Shortlist"})
        assert again.status_code == 409

    async def test_unpublishing_revokes_the_share_token(self, auth_client: AsyncClient):
        created = await auth_client.post(
            f"{V1}/me/collections", json={"name": "Temp", "is_public": True}
        )
        collection_id = created.json()["id"]
        assert created.json()["share_token"]
        updated = await auth_client.patch(
            f"{V1}/me/collections/{collection_id}", json={"is_public": False}
        )
        assert updated.json()["share_token"] is None

    async def test_cannot_touch_another_users_collection(self, auth_client: AsyncClient):
        created = await auth_client.post(f"{V1}/me/collections", json={"name": "Private"})
        collection_id = created.json()["id"]

        other = await auth_client.post(
            f"{V1}/auth/register",
            json={
                "email": "intruder@example.com",
                "display_name": "Intruder",
                "password": "Rigel-55-Vector",
            },
        )
        auth_client.headers["Authorization"] = f"Bearer {other.json()['access_token']}"
        assert (
            await auth_client.get(f"{V1}/me/collections")
        ).json() == []
        assert (
            await auth_client.patch(
                f"{V1}/me/collections/{collection_id}", json={"name": "Hijacked"}
            )
        ).status_code == 404
        assert (
            await auth_client.delete(f"{V1}/me/collections/{collection_id}")
        ).status_code == 404


class TestSavedComparisons:
    async def test_save_list_and_delete(self, auth_client: AsyncClient):
        created = await auth_client.post(
            f"{V1}/me/comparisons",
            json={"name": "Rocky trio", "planet_slugs": ["earth", "mars", "venus"]},
        )
        assert created.status_code == 201
        assert created.json()["planet_slugs"] == ["earth", "mars", "venus"]

        listed = (await auth_client.get(f"{V1}/me/comparisons")).json()
        assert len(listed) == 1

        assert (
            await auth_client.delete(f"{V1}/me/comparisons/{created.json()['id']}")
        ).status_code == 204

    async def test_unknown_planet_is_rejected(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{V1}/me/comparisons",
            json={"name": "Bad", "planet_slugs": ["earth", "arrakis"]},
        )
        assert response.status_code == 404

    async def test_at_least_two_planets_are_required(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{V1}/me/comparisons", json={"name": "Lonely", "planet_slugs": ["earth"]}
        )
        assert response.status_code == 422
