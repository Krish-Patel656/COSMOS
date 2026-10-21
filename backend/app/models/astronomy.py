"""ORM models for stars, planetary systems and planets.

Column naming encodes units explicitly (``radius_earth``, ``distance_pc``,
``period_days``) because the single most common source of error in astronomical
data pipelines is silently mixing Jupiter radii with Earth radii, or parsecs
with light years. Scores are stored denormalised on the planet row: they are
expensive to compute, deterministic given the inputs, and every list and filter
endpoint sorts by them.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Star(Base, TimestampMixin):
    """A host star, which in this schema doubles as the planetary system."""

    __tablename__ = "stars"
    __table_args__ = (
        Index("ix_stars_distance", "distance_pc"),
        Index("ix_stars_temp", "effective_temp_k"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)

    # Alternate identifiers (HD, HIP, TIC, Gaia DR3 ...) used by search.
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # --- Position ---------------------------------------------------------
    right_ascension_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    declination_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_pc: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_ly: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Equatorial cartesian coordinates in parsecs, precomputed from
    # RA/Dec/distance so the 3D stellar map does not have to do spherical
    # trigonometry for thousands of stars on every render.
    x_pc: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_pc: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_pc: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Physical ---------------------------------------------------------
    spectral_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spectral_class: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    effective_temp_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_solar: Mapped[float | None] = mapped_column(Float, nullable=True)
    mass_solar: Mapped[float | None] = mapped_column(Float, nullable=True)
    luminosity_solar: Mapped[float | None] = mapped_column(Float, nullable=True)
    metallicity_dex: Mapped[float | None] = mapped_column(Float, nullable=True)
    surface_gravity_log: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_gyr: Mapped[float | None] = mapped_column(Float, nullable=True)
    rotation_period_days: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Observational ----------------------------------------------------
    v_magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gaia_magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    naked_eye_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- System -----------------------------------------------------------
    planet_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stellar_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_solar_system: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )

    # --- Derived / presentation ------------------------------------------
    color_hex: Mapped[str | None] = mapped_column(String(9), nullable=True)
    habitable_zone: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Best scores in the system, denormalised so the stellar map can colour
    # stars by "does anything interesting orbit here?" in a single query.
    best_habitability_score: Mapped[float | None] = mapped_column(
        Float, index=True, nullable=True
    )
    best_esi: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)

    planets: Mapped[list[Planet]] = relationship(
        back_populates="star",
        cascade="all, delete-orphan",
        order_by="Planet.semi_major_axis_au",
        lazy="selectin",
    )


class Planet(Base, TimestampMixin):
    """A confirmed exoplanet, or a Solar System planet used as reference."""

    __tablename__ = "planets"
    __table_args__ = (
        UniqueConstraint("star_id", "name", name="uq_planet_name_per_star"),
        Index("ix_planets_scores", "habitability_score", "esi"),
        Index("ix_planets_radius_temp", "radius_earth", "equilibrium_temp_k"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    letter: Mapped[str | None] = mapped_column(String(8), nullable=True)

    star_id: Mapped[int] = mapped_column(
        ForeignKey("stars.id", ondelete="CASCADE"), index=True, nullable=False
    )
    star: Mapped[Star] = relationship(back_populates="planets", lazy="joined")

    # --- Measured bulk properties ----------------------------------------
    radius_earth: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_jupiter: Mapped[float | None] = mapped_column(Float, nullable=True)
    mass_earth: Mapped[float | None] = mapped_column(Float, nullable=True)
    mass_jupiter: Mapped[float | None] = mapped_column(Float, nullable=True)
    mass_is_minimum: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mass_provenance: Mapped[str | None] = mapped_column(String(48), nullable=True)

    # --- Orbit ------------------------------------------------------------
    orbital_period_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    semi_major_axis_au: Mapped[float | None] = mapped_column(Float, nullable=True)
    eccentricity: Mapped[float | None] = mapped_column(Float, nullable=True)
    inclination_deg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Thermal ----------------------------------------------------------
    equilibrium_temp_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    insolation_earth: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Derived (computed at ingest, see app.science) ---------------------
    density_g_cm3: Mapped[float | None] = mapped_column(Float, nullable=True)
    surface_gravity_ms2: Mapped[float | None] = mapped_column(Float, nullable=True)
    escape_velocity_km_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    radius_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mass_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    temp_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    axis_is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Scores -----------------------------------------------------------
    esi: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    esi_interior: Mapped[float | None] = mapped_column(Float, nullable=True)
    esi_surface: Mapped[float | None] = mapped_column(Float, nullable=True)
    esi_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    habitability_score: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    habitability_band: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    habitability_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    habitability_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    in_conservative_hz: Mapped[bool | None] = mapped_column(Boolean, index=True, nullable=True)
    in_optimistic_hz: Mapped[bool | None] = mapped_column(Boolean, index=True, nullable=True)
    tidal_locking_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)

    size_class: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    thermal_class: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)

    # --- Presentation -----------------------------------------------------
    appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Discovery --------------------------------------------------------
    discovery_method: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    discovery_year: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    discovery_facility: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_controversial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_solar_system: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )

    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestRun(Base, TimestampMixin):
    """Audit trail for each data ingestion, so the UI can cite data provenance."""

    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    rows_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stars_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    planets_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
