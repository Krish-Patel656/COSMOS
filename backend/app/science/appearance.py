"""Artistic appearance derivation for 3D rendering.

Nothing in this module is an observation. We have resolved images of exactly
zero exoplanet surfaces. What we do have, for some planets, is radius, mass,
temperature and insolation — enough to say "this is probably a molten rock",
"this is probably an ice world", or "this is a hydrogen-dominated giant with
banded cloud decks". This module turns those inferences into a render recipe and
labels every output as artistic so the UI can say so plainly.

The mapping is documented in ``docs/METHODOLOGY.md`` and intentionally lives on
the server so the 3D scene, the comparison view and the social preview images
all render the same planet the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.science.constants import EARTH_DENSITY_G_CM3, ROCKY_RADIUS_CEILING_RE

__all__ = ["PlanetAppearance", "derive_appearance", "star_color_hex"]


@dataclass(frozen=True)
class PlanetAppearance:
    surface_type: str
    """One of: lava, scorched, desert, terrestrial, ocean, tundra, ice,
    sub_neptune, gas_giant, unknown."""

    base_color: str
    accent_color: str
    atmosphere_color: str
    atmosphere_opacity: float
    cloud_coverage: float
    roughness: float
    metalness: float
    emissive_intensity: float
    has_rings: bool
    banded: bool
    """True for gas giants, which get zonal cloud bands instead of continents."""

    basis: list[str] = field(default_factory=list)
    """Which measured properties drove this look, for the "why does it look like
    that?" disclosure in the UI."""

    is_artistic: bool = True

    def as_dict(self) -> dict:
        return {
            "surface_type": self.surface_type,
            "base_color": self.base_color,
            "accent_color": self.accent_color,
            "atmosphere_color": self.atmosphere_color,
            "atmosphere_opacity": self.atmosphere_opacity,
            "cloud_coverage": self.cloud_coverage,
            "roughness": self.roughness,
            "metalness": self.metalness,
            "emissive_intensity": self.emissive_intensity,
            "has_rings": self.has_rings,
            "banded": self.banded,
            "basis": self.basis,
            "is_artistic": self.is_artistic,
        }


_PALETTES = {
    "lava": ("#c2410c", "#fbbf24", "#7c2d12"),
    "scorched": ("#92400e", "#d97706", "#451a03"),
    "desert": ("#c08552", "#e8c39e", "#d9bb94"),
    "terrestrial": ("#2e7d5b", "#8fbf7f", "#7ec8f5"),
    "ocean": ("#1d6fa5", "#4aa8d8", "#8ecbf0"),
    "tundra": ("#7d8c7a", "#cfd8d1", "#bcd7e8"),
    "ice": ("#cfe4f0", "#ffffff", "#d8ecf8"),
    "sub_neptune": ("#6b8fd4", "#a8c4ec", "#b6cdf2"),
    "gas_giant": ("#d07a32", "#f0b45a", "#e8a868"),
    "gas_giant_saturn": ("#e6c99a", "#f7ead0", "#efe0c4"),
    "unknown": ("#6b7280", "#9ca3af", "#94a3b8"),
}

# Saturn is 0.69 g/cm³; Jupiter is 1.33. Rings are assigned only to the fluffy,
# cold giants — otherwise Jupiter renders as a second Saturn.
_SATURN_DENSITY_G_CM3 = 1.0
_RING_TEMP_MAX_K = 150.0


def derive_appearance(
    radius_earth: float | None,
    mass_earth: float | None,
    temperature_k: float | None,
    insolation_earth: float | None = None,
    density_g_cm3: float | None = None,
) -> PlanetAppearance:
    """Infer a plausible visual appearance from bulk properties."""
    basis: list[str] = []
    radius = radius_earth if (radius_earth or 0) > 0 else None
    temp = temperature_k if (temperature_k or 0) > 0 else None

    if radius:
        basis.append(f"radius {radius:.2f} R⊕")
    if temp:
        basis.append(f"temperature {temp:.0f} K")
    if density_g_cm3:
        basis.append(f"density {density_g_cm3:.1f} g/cm³")
    if insolation_earth:
        basis.append(f"insolation {insolation_earth:.2f} S⊕")

    # Giants are decided by size alone: above ~4 Earth radii no known planet has
    # a surface, so temperature only tunes the palette.
    if radius and radius >= 8.0:
        surface = "gas_giant"
    elif radius and radius >= 4.0 or radius and radius > 2.0 and (density_g_cm3 or 99) < 3.0:
        surface = "sub_neptune"
    elif temp is None:
        surface = "unknown"
    elif temp >= 1200:
        surface = "lava"
    elif temp >= 600:
        surface = "scorched"
    elif temp >= 330:
        surface = "desert"
    elif temp >= 250:
        surface = "terrestrial" if (radius or 1.0) <= ROCKY_RADIUS_CEILING_RE else "ocean"
    elif temp >= 190:
        surface = "tundra"
    else:
        surface = "ice"

    density = density_g_cm3 if density_g_cm3 and density_g_cm3 > 0 else None
    if density is None and mass_earth and radius and mass_earth > 0:
        density = EARTH_DENSITY_G_CM3 * mass_earth / radius**3

    saturn_like = (
        surface == "gas_giant"
        and density is not None
        and density < _SATURN_DENSITY_G_CM3
        and (temp or 0) < _RING_TEMP_MAX_K
    )
    if saturn_like:
        base, accent, atmosphere = _PALETTES["gas_giant_saturn"]
    else:
        base, accent, atmosphere = _PALETTES[surface]

    banded = surface in ("gas_giant", "sub_neptune")
    has_rings = saturn_like

    if surface in ("lava",):
        opacity, clouds, roughness, metalness, emissive = 0.35, 0.15, 0.85, 0.15, 0.45
    elif surface == "scorched":
        opacity, clouds, roughness, metalness, emissive = 0.25, 0.1, 0.95, 0.1, 0.08
    elif surface == "desert":
        opacity, clouds, roughness, metalness, emissive = 0.3, 0.2, 0.9, 0.05, 0.0
    elif surface == "terrestrial":
        opacity, clouds, roughness, metalness, emissive = 0.55, 0.55, 0.7, 0.05, 0.0
    elif surface == "ocean":
        opacity, clouds, roughness, metalness, emissive = 0.6, 0.65, 0.35, 0.1, 0.0
    elif surface == "tundra":
        opacity, clouds, roughness, metalness, emissive = 0.4, 0.45, 0.8, 0.05, 0.0
    elif surface == "ice":
        opacity, clouds, roughness, metalness, emissive = 0.3, 0.3, 0.45, 0.05, 0.0
    elif surface == "sub_neptune":
        opacity, clouds, roughness, metalness, emissive = 0.8, 0.9, 0.5, 0.0, 0.0
    elif surface == "gas_giant":
        opacity, clouds, roughness, metalness, emissive = 0.75, 0.95, 0.55, 0.0, 0.0
    else:
        opacity, clouds, roughness, metalness, emissive = 0.25, 0.3, 0.85, 0.1, 0.0

    return PlanetAppearance(
        surface_type=surface,
        base_color=base,
        accent_color=accent,
        atmosphere_color=atmosphere,
        atmosphere_opacity=opacity,
        cloud_coverage=clouds,
        roughness=roughness,
        metalness=metalness,
        emissive_intensity=emissive,
        has_rings=has_rings,
        banded=banded,
        basis=basis,
    )


# Approximate blackbody colours for main-sequence stars, keyed by the lower
# bound of each temperature bucket. Derived from the Planckian locus converted
# to sRGB, then lightened so stars read as luminous rather than muddy on screen.
_STAR_COLORS = (
    (33000, "#9bb0ff"),
    (10000, "#aabfff"),
    (7500, "#cad7ff"),
    (6000, "#fbf8ff"),
    (5200, "#fff4e8"),
    (3700, "#ffd2a1"),
    (2400, "#ffa060"),
    (0, "#ff7b4a"),
)


def star_color_hex(effective_temp_k: float | None) -> str:
    """Approximate sRGB colour of a star with the given effective temperature."""
    if not effective_temp_k or effective_temp_k <= 0:
        return "#fff4e8"
    for threshold, color in _STAR_COLORS:
        if effective_temp_k >= threshold:
            return color
    return "#ff7b4a"
