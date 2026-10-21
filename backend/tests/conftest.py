"""Test fixtures.

Environment variables are set *before* importing anything from ``app`` because
``app.core.config.settings`` is a module-level singleton; configuring it any
later would silently test against the developer's real database.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="cosmos-tests-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP / 'test.db'}"
os.environ["SECRET_KEY"] = "test-only-secret-key-not-used-anywhere-real"
os.environ["REDIS_URL"] = ""
os.environ["ENVIRONMENT"] = "test"

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.ingest.normalize import build_solar_system, normalize_rows  # noqa: E402
from app.ingest.pipeline import _replace_catalogue  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

# Two synthetic systems that exercise the awkward paths: Jupiter-unit-only
# columns, a mass from the archive's own mass-radius relation, a minimum mass, and
# a row with almost nothing known (which must end up unscored).
FIXTURE_ROWS = [
    {
        "pl_name": "Testaris b",
        "hostname": "Testaris",
        "sy_snum": "1",
        "sy_pnum": "2",
        "discoverymethod": "Transit",
        "disc_year": "2019",
        "disc_facility": "Test Observatory",
        "pl_controv_flag": "0",
        "pl_orbper": "290.0",
        "pl_orbsmax": "0.82",
        "pl_orbeccen": "0.03",
        "pl_orbincl": "89.2",
        "pl_rade": "1.05",
        "pl_radj": None,
        "pl_bmasse": "1.2",
        "pl_bmassj": None,
        "pl_bmassprov": "Mass",
        "pl_eqt": "262",
        "pl_insol": "0.95",
        "st_spectype": "G8 V",
        "st_teff": "5400",
        "st_rad": "0.88",
        "st_mass": "0.92",
        "st_met": "0.02",
        "st_logg": "4.5",
        "st_age": "5.1",
        "st_lum": "-0.13",
        "st_rotp": "26.0",
        "ra": "180.0",
        "dec": "20.0",
        "sy_dist": "12.5",
        "sy_vmag": "7.1",
        "sy_gaiamag": "6.9",
        "pl_pubdate": "2019-06",
    },
    {
        # Jupiter-unit columns only, so the normaliser must convert both.
        "pl_name": "Testaris c",
        "hostname": "Testaris",
        "sy_snum": "1",
        "sy_pnum": "2",
        "discoverymethod": "Radial Velocity",
        "disc_year": "2021",
        "disc_facility": "Test Observatory",
        "pl_controv_flag": "0",
        "pl_orbper": "1400.0",
        "pl_orbsmax": None,
        "pl_orbeccen": "0.22",
        "pl_orbincl": None,
        "pl_rade": None,
        "pl_radj": "1.1",
        "pl_bmasse": None,
        "pl_bmassj": "2.4",
        "pl_bmassprov": "Msini",
        "pl_eqt": None,
        "pl_insol": None,
        "st_spectype": "G8 V",
        "st_teff": "5400",
        "st_rad": "0.88",
        "st_mass": "0.92",
        "st_met": "0.02",
        "st_logg": "4.5",
        "st_age": "5.1",
        "st_lum": "-0.13",
        "st_rotp": "26.0",
        "ra": "180.0",
        "dec": "20.0",
        "sy_dist": "12.5",
        "sy_vmag": "7.1",
        "sy_gaiamag": "6.9",
        "pl_pubdate": "2021-02",
    },
    {
        # A microlensing detection: no stellar characterisation at all, so this
        # must come out unscored rather than scored on its few known properties.
        "pl_name": "OGLE-TEST-9999L b",
        "hostname": "OGLE-TEST-9999L",
        "sy_snum": "1",
        "sy_pnum": "1",
        "discoverymethod": "Microlensing",
        "disc_year": "2020",
        "disc_facility": "OGLE",
        "pl_controv_flag": "0",
        "pl_orbper": None,
        "pl_orbsmax": "1.9",
        "pl_orbeccen": None,
        "pl_orbincl": None,
        "pl_rade": "1.2",
        "pl_radj": None,
        "pl_bmasse": "1.9",
        "pl_bmassj": None,
        "pl_bmassprov": "M-R relationship",
        "pl_eqt": None,
        "pl_insol": None,
        "st_spectype": None,
        "st_teff": None,
        "st_rad": None,
        "st_mass": None,
        "st_met": None,
        "st_logg": None,
        "st_age": None,
        "st_lum": None,
        "st_rotp": None,
        "ra": "269.0",
        "dec": "-28.0",
        "sy_dist": "3400.0",
        "sy_vmag": None,
        "sy_gaiamag": "19.2",
        "pl_pubdate": "2020-01",
    },
]


@pytest.fixture(scope="session")
def fixture_rows() -> list[dict]:
    return FIXTURE_ROWS


@pytest.fixture(autouse=True)
async def seeded_database() -> AsyncIterator[None]:
    """Fresh schema plus the Solar System and the synthetic systems, per test."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    stars = normalize_rows(FIXTURE_ROWS)
    stars.insert(0, build_solar_system())
    async with SessionLocal() as session:
        await _replace_catalogue(session, stars)
        await session.commit()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """A client with a registered user's access token already attached."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "explorer@example.com",
            "display_name": "Explorer",
            "password": "Andromeda-42-Nebula",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
