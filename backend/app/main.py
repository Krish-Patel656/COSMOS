"""COSMOS FastAPI application."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.core.cache import close_cache
from app.core.config import settings
from app.db.session import dispose_engine, init_models

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DESCRIPTION = """
An API over the NASA Exoplanet Archive with a transparent habitability analysis layer.

**What makes this different from a catalogue mirror:** every planet carries an Earth
Similarity Index and a habitability score, and both ship with the full per-factor
breakdown that produced them — the value used, the weight applied, the verdict, and a
sentence explaining what that value implies. Estimated inputs are flagged, and a
separate confidence figure reports how much of the score rests on measurement versus
inference.

**Scientific basis:** habitable zone edges follow Kopparapu et al. (2013, 2014); the
Earth Similarity Index follows Schulze-Makuch et al. (2011); mass-radius estimates use
the Chen & Kipping (2017) relation. Full methodology, including the limits of each
model, is in `docs/METHODOLOGY.md`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Creating tables at startup keeps a fresh checkout runnable in one command.
    # Deployed environments run Alembic and this becomes a no-op.
    await init_models()
    logger.info("COSMOS API ready (environment=%s)", settings.environment)
    yield
    await close_cache()
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=DESCRIPTION,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# The stellar-map and explorer payloads are JSON in the hundreds of kilobytes and
# compress by roughly 80%, so this is the single highest-leverage perf setting.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["meta"], summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "version": __version__, "environment": settings.environment}


@app.get("/", tags=["meta"], include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
