"""Aggregated v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, compare, highlights, me, planets, search, simulate, stats, systems

api_router = APIRouter()

# Order matters for the few routers that share a path prefix: `systems` registers
# the literal `/stars/map` before `/stars/{slug}`, so it must stay ahead of any
# future router that could claim the same space.
api_router.include_router(stats.router)
api_router.include_router(search.router)
api_router.include_router(highlights.router)
api_router.include_router(systems.router)
api_router.include_router(planets.router)
api_router.include_router(compare.router)
api_router.include_router(simulate.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
