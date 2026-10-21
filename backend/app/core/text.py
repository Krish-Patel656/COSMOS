"""Text helpers shared by ingestion and the API."""

from __future__ import annotations

import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """URL-safe identifier.

    Astronomical names are full of spaces, hyphens, plus signs and Greek
    letters ("HD 209458 b", "mu Arae c", "GJ 1214 b"). We normalise to NFKD,
    strip accents, lowercase, and collapse everything else to single hyphens so
    that ``/systems/trappist-1`` and ``/planets/trappist-1-e`` are stable,
    readable URLs.
    """
    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG.sub("-", ascii_only.lower()).strip("-")
    return slug or "unknown"


def planet_letter(planet_name: str, host_name: str) -> str | None:
    """Extract the trailing designation ("b", "c", "AB b") from a planet name."""
    remainder = planet_name[len(host_name) :].strip() if planet_name.startswith(host_name) else ""
    if not remainder:
        parts = planet_name.rsplit(" ", 1)
        remainder = parts[1] if len(parts) == 2 else ""
    return remainder or None
