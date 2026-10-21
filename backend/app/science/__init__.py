"""COSMOS science engine.

Pure, dependency-free astrophysics: derived quantities, habitable zone edges,
the Earth Similarity Index, explainable habitability scoring, and artistic
appearance derivation. Nothing here touches the database or the network, so
every function is directly unit testable and reusable by both the ingestion
pipeline and the live simulator endpoint.
"""

from app.science import appearance, astro, esi, habitability, habitable_zone

__all__ = ["appearance", "astro", "esi", "habitability", "habitable_zone"]
