"""Explainable habitability scoring.

There is no accepted single number that measures how habitable a planet is, and
any project that claims otherwise is overselling. What *can* be done rigorously
is to take the handful of properties we actually measure for exoplanets, score
each one against conditions we have physical reason to believe matter for
surface liquid water, and then report the weighted result **together with the
per-factor reasoning, the data we had to guess at, and the resulting
confidence**. That is what this module does.

The output is deliberately structured as evidence, not a verdict: every factor
carries its own score, weight, measured value, verdict band and a sentence
explaining what the value implies. The UI shows that breakdown instead of a
bare number.

Known limitations, stated up front because they bound the meaning of the score:

* Atmospheric composition is unknown for virtually every planet here, and it is
  the single biggest control on surface temperature. Equilibrium temperature is
  a proxy, nothing more.
* Equilibrium temperature cannot distinguish Earth from Venus (255 K vs 227 K).
  Only the habitable-zone factor separates them, via the runaway greenhouse
  limit.
* Masses are frequently minimum masses (radial velocity) or estimates from a
  mass-radius relation. Both are flagged.
* Factor weights encode a scientific judgement about relative importance. They
  are documented, tunable, and reported in the API response so a reader can
  disagree with them explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.science import astro
from app.science.constants import (
    LIQUID_WATER_MAX_K,
    LIQUID_WATER_MIN_K,
    RADIUS_VALLEY_LOWER_RE,
    RADIUS_VALLEY_UPPER_RE,
    ROCKY_RADIUS_CEILING_RE,
)
from app.science.habitable_zone import (
    HabitableZone,
    habitable_zone,
    hz_flux_position,
)

__all__ = [
    "FACTOR_WEIGHTS",
    "HabitabilityFactor",
    "HabitabilityResult",
    "PlanetInput",
    "classify_size",
    "classify_thermal",
    "compute_habitability",
    "score_band",
]


# --- Scoring curves -------------------------------------------------------


def _smoothstep(t: float) -> float:
    """Hermite easing on [0, 1]; avoids the kinks of linear interpolation."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _plateau(
    value: float, ideal_low: float, ideal_high: float, hard_low: float, hard_high: float
) -> float:
    """1.0 inside the ideal band, smoothly tapering to 0.0 at the hard bounds."""
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        if value <= hard_low:
            return 0.0
        return _smoothstep((value - hard_low) / (ideal_low - hard_low))
    if value >= hard_high:
        return 0.0
    return _smoothstep((hard_high - value) / (hard_high - ideal_high))


def _log_plateau(
    value: float, ideal_low: float, ideal_high: float, hard_low: float, hard_high: float
) -> float:
    """``_plateau`` in log space, for quantities spanning orders of magnitude."""
    if value <= 0:
        return 0.0
    return _plateau(
        math.log10(value),
        math.log10(ideal_low),
        math.log10(ideal_high),
        math.log10(hard_low),
        math.log10(hard_high),
    )


# --- Data structures ------------------------------------------------------

# Weights sum to 1.0. They are renormalised over whichever factors could
# actually be evaluated, so a planet missing eccentricity is not punished for
# the gap; instead its reported confidence drops.
FACTOR_WEIGHTS: dict[str, float] = {
    "habitable_zone": 0.24,
    "temperature": 0.18,
    "size": 0.15,
    "atmosphere_retention": 0.13,
    "host_star": 0.12,
    "composition": 0.09,
    "orbital_eccentricity": 0.05,
    "tidal_locking": 0.04,
}

# Factors are combined with a *weighted geometric* mean rather than an
# arithmetic one. Habitability is closer to a conjunction of requirements than a
# sum of merits: a world that is perfect in seven respects and cannot hold an
# atmosphere is not habitable, and an arithmetic mean would still call it
# promising. The geometric mean lets any single near-zero factor dominate, which
# is the behaviour we want. This floor keeps the logarithm finite, and has the
# side effect of capping how far one failed factor can sink the result — a
# planet outside the habitable zone bottoms out near 33/100 rather than 0,
# which honestly reflects that "wrong orbit" is strong evidence and not proof.
_FACTOR_FLOOR = 0.01

# Weights are renormalised over whichever factors could be evaluated, which
# quietly assumes that a missing factor would have scored around the average of
# the others. For a planet with one or two gaps that is reasonable. For a
# microlensing detection — where the host star is never characterised, so there
# is no temperature, no insolation and no habitable zone — it is actively wrong:
# the handful of evaluable factors are all derived from the mass-radius relation
# and all come out Earth-like, producing a perfect score for a world we know
# essentially nothing about. These two gates prevent that.
MINIMUM_SCORABLE_WEIGHT = 0.45
REQUIRED_FACTOR_KEYS = ("habitable_zone", "temperature")
"""At least one of these must be evaluable. Without any constraint on how much
starlight a planet receives or how hot it is, "habitability" has no content."""

_VERDICT_BANDS = (
    (0.80, "ideal"),
    (0.60, "favourable"),
    (0.40, "marginal"),
    (0.20, "poor"),
    (0.00, "hostile"),
)


def _verdict(score: float | None) -> str:
    if score is None:
        return "unknown"
    for threshold, label in _VERDICT_BANDS:
        if score >= threshold:
            return label
    return "hostile"


def score_band(score_0_100: float | None) -> str:
    """Human-readable tier for an overall habitability score."""
    if score_0_100 is None:
        return "insufficient data"
    if score_0_100 >= 80:
        return "exceptional candidate"
    if score_0_100 >= 65:
        return "promising candidate"
    if score_0_100 >= 50:
        return "plausible candidate"
    if score_0_100 >= 30:
        return "marginal"
    if score_0_100 >= 15:
        return "unlikely"
    return "hostile"


@dataclass(frozen=True)
class HabitabilityFactor:
    key: str
    label: str
    score: float | None
    weight: float
    value: float | None
    unit: str
    verdict: str
    explanation: str
    estimated: bool = False

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "score": self.score,
            "weight": self.weight,
            "value": self.value,
            "unit": self.unit,
            "verdict": self.verdict,
            "explanation": self.explanation,
            "estimated": self.estimated,
        }


@dataclass(frozen=True)
class HabitabilityResult:
    score: float | None
    """Weighted habitability score on a 0-100 scale, or ``None`` when too
    little is known to say anything at all."""

    band: str
    confidence: float
    """0-1 measure combining how much of the factor weight could be evaluated
    with how much of the input was estimated rather than measured."""

    factors: list[HabitabilityFactor] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    size_class: str | None = None
    thermal_class: str | None = None
    habitable_zone: HabitableZone | None = None
    in_conservative_hz: bool | None = None
    in_optimistic_hz: bool | None = None
    summary: str = ""

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "band": self.band,
            "confidence": self.confidence,
            "summary": self.summary,
            "size_class": self.size_class,
            "thermal_class": self.thermal_class,
            "in_conservative_hz": self.in_conservative_hz,
            "in_optimistic_hz": self.in_optimistic_hz,
            "habitable_zone": self.habitable_zone.as_dict() if self.habitable_zone else None,
            "factors": [factor.as_dict() for factor in self.factors],
            "caveats": self.caveats,
        }


@dataclass
class PlanetInput:
    """Everything the scorer can use. Any field may be ``None``."""

    radius_earth: float | None = None
    mass_earth: float | None = None
    equilibrium_temp_k: float | None = None
    surface_temp_k: float | None = None
    orbital_period_days: float | None = None
    semi_major_axis_au: float | None = None
    eccentricity: float | None = None
    insolation_earth: float | None = None
    bond_albedo: float | None = None

    star_effective_temp_k: float | None = None
    star_radius_solar: float | None = None
    star_mass_solar: float | None = None
    star_luminosity_solar: float | None = None
    star_age_gyr: float | None = None
    star_metallicity_dex: float | None = None

    mass_is_minimum: bool = False
    """True when the mass comes from radial velocity without a known
    inclination, in which case it is M*sin(i): a lower bound."""

    mass_is_estimated: bool = False
    """True when the supplied mass is itself modelled rather than measured. The
    NASA archive fills roughly half of its masses from a mass-radius relation, and
    those must not be reported as observations."""

    radius_is_estimated: bool = False
    """As above, for radius."""


# --- Classification -------------------------------------------------------


def classify_size(
    radius_earth: float | None, mass_earth: float | None
) -> str | None:
    """Coarse size class, preferring radius when available."""
    radius = radius_earth
    if radius is None and mass_earth:
        radius = astro.radius_from_mass_earth_units(mass_earth)
    if not radius:
        return None
    if radius < 0.5:
        return "Sub-Earth"
    if radius < 1.25:
        return "Earth-sized"
    if radius < ROCKY_RADIUS_CEILING_RE:
        return "Super-Earth"
    if radius < 2.0:
        return "Radius-valley world"
    if radius < 4.0:
        return "Sub-Neptune"
    if radius < 8.0:
        return "Neptune-like"
    return "Gas giant"


def classify_thermal(temperature_k: float | None) -> str | None:
    """Coarse thermal class from equilibrium temperature."""
    if not temperature_k or temperature_k <= 0:
        return None
    if temperature_k >= 1000:
        return "Ultra-hot"
    if temperature_k >= 500:
        return "Hot"
    if temperature_k >= 320:
        return "Warm"
    if temperature_k >= 200:
        return "Temperate"
    if temperature_k >= 120:
        return "Cold"
    return "Frozen"


# --- Individual factors ---------------------------------------------------


def _habitable_zone_factor(
    zone: HabitableZone | None,
    axis_au: float | None,
    insolation: float | None,
) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["habitable_zone"]

    if zone is None or not axis_au:
        # Fall back to raw insolation when the star is too poorly characterised
        # to place habitable-zone edges.
        if insolation:
            score = _log_plateau(insolation, 0.4, 1.1, 0.1, 4.0)
            return HabitabilityFactor(
                key="habitable_zone",
                label="Habitable zone position",
                score=score,
                weight=weight,
                value=insolation,
                unit="S⊕",
                verdict=_verdict(score),
                explanation=(
                    f"The host star is not characterised well enough to place habitable-zone "
                    f"edges, so this falls back to raw stellar flux: the planet receives "
                    f"{insolation:.2f}× the sunlight Earth does."
                ),
                estimated=True,
            )
        return HabitabilityFactor(
            key="habitable_zone",
            label="Habitable zone position",
            score=None,
            weight=weight,
            value=None,
            unit="",
            verdict="unknown",
            explanation=(
                "Neither the orbital distance nor the host star's luminosity is known well "
                "enough to say where this planet sits relative to the habitable zone."
            ),
        )

    # Work in flux rather than distance. The Kopparapu limits are published as
    # fluxes; expressing them in AU requires the stellar luminosity, and the NASA
    # composite table sources its stellar radius and its planetary insolation from
    # different publications often enough that the two are mutually inconsistent.
    # For Kepler-186 f the catalogued flux implies a luminosity 36% higher than
    # the catalogued stellar radius does — the difference between "inside the
    # habitable zone", as the literature reports, and "outside" it.
    flux = insolation
    flux_is_derived = False
    if flux is None and axis_au:
        flux = zone.stellar_luminosity_solar / axis_au**2
        flux_is_derived = True

    if not flux or flux <= 0:
        return HabitabilityFactor(
            key="habitable_zone",
            label="Habitable zone position",
            score=None,
            weight=weight,
            value=None,
            unit="S⊕",
            verdict="unknown",
            explanation=(
                "Neither a measured stellar flux nor an orbital distance is available, so the "
                "planet cannot be placed relative to the habitable zone."
            ),
        )

    outer_flux, inner_flux = zone.conservative_flux_range
    opt_outer_flux, opt_inner_flux = zone.optimistic_flux_range
    inner_au, outer_au = zone.conservative_range_au
    position = hz_flux_position(zone, flux)

    # The whole premise of the model is that the conservative zone is habitable
    # end to end, so we do not invent a preference for its centre. Anywhere inside
    # scores full marks; the empirical margins beyond it score half, reflecting
    # that they rest on Venus and Mars analogies rather than on the
    # radiative-convective model itself.
    if outer_flux <= flux <= inner_flux:
        score: float | None = 1.0
    elif flux > inner_flux:
        span = math.log(opt_inner_flux) - math.log(inner_flux)
        score = (
            0.5 * _smoothstep((math.log(opt_inner_flux) - math.log(flux)) / span)
            if span > 0
            else 0.0
        )
    else:
        span = math.log(outer_flux) - math.log(opt_outer_flux)
        score = (
            0.5 * _smoothstep((math.log(flux) - math.log(opt_outer_flux)) / span)
            if span > 0
            else 0.0
        )

    distance_phrase = f"At {axis_au:.3f} AU it" if axis_au else "It"
    if outer_flux <= flux <= inner_flux:
        where = (
            "near the inner edge of"
            if (position or 0) < 0.2
            else ("near the outer edge of" if (position or 0) > 0.8 else "comfortably within")
        )
        explanation = (
            f"{distance_phrase} receives {flux:.2f}× the starlight Earth does, placing it "
            f"{where} the conservative habitable zone ({outer_flux:.2f}–{inner_flux:.2f} S⊕, or "
            f"roughly {inner_au:.3f}–{outer_au:.3f} AU for this star) — the range where a "
            f"cloud-free water world could hold liquid water without losing its oceans or "
            f"freezing over."
        )
    elif flux > inner_flux:
        explanation = (
            f"{distance_phrase} receives {flux:.2f}× Earth's starlight, more than the "
            f"{inner_flux:.2f} S⊕ runaway greenhouse limit, so an Earth-like water inventory "
            f"would likely be boiled off and lost to space — the fate Venus suffered."
        )
    else:
        explanation = (
            f"{distance_phrase} receives only {flux:.2f}× Earth's starlight, below the "
            f"{outer_flux:.2f} S⊕ maximum greenhouse limit, where even a thick CO₂ atmosphere "
            f"cannot keep a surface above freezing because CO₂ begins scattering away more "
            f"light than it traps."
        )

    return HabitabilityFactor(
        key="habitable_zone",
        label="Habitable zone position",
        score=score,
        weight=weight,
        value=flux,
        unit="S⊕",
        verdict=_verdict(score),
        explanation=explanation,
        estimated=zone.extrapolated or flux_is_derived,
    )


def _temperature_factor(
    temperature_k: float | None, is_equilibrium: bool
) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["temperature"]
    if not temperature_k or temperature_k <= 0:
        return HabitabilityFactor(
            key="temperature",
            label="Temperature",
            score=None,
            weight=weight,
            value=None,
            unit="K",
            verdict="unknown",
            explanation="No temperature estimate is available for this planet.",
        )

    if is_equilibrium:
        # Earth's equilibrium temperature is 255 K; its 288 K surface is the work
        # of 33 K of greenhouse warming. The ideal band straddles that value,
        # and the taper is generous because an unknown atmosphere can shift the
        # true surface temperature by tens to hundreds of kelvin in either
        # direction.
        score = _plateau(temperature_k, 240.0, 275.0, 150.0, 440.0)
        basis = "equilibrium"
        reference = "Earth's is 255 K before greenhouse warming"
    else:
        score = _plateau(
            temperature_k, LIQUID_WATER_MIN_K + 5.0, 305.0, 245.0, LIQUID_WATER_MAX_K
        )
        basis = "surface"
        reference = "Earth's is 288 K"

    if score >= 0.8:
        implication = "comfortably compatible with liquid water given a plausible atmosphere"
    elif score >= 0.4:
        implication = "only compatible with liquid water under a favourable atmosphere"
    elif temperature_k > 320:
        implication = "hot enough that surface water would be vapour under most atmospheres"
    else:
        implication = "cold enough that surface water would be ice without strong greenhouse warming"

    return HabitabilityFactor(
        key="temperature",
        label="Temperature",
        score=score,
        weight=weight,
        value=temperature_k,
        unit="K",
        verdict=_verdict(score),
        explanation=(
            f"The {basis} temperature of {temperature_k:.0f} K ({reference}) is {implication}."
        ),
        estimated=False,
    )


def _size_factor(radius_earth: float | None, estimated: bool) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["size"]
    if not radius_earth or radius_earth <= 0:
        return HabitabilityFactor(
            key="size",
            label="Planet size",
            score=None,
            weight=weight,
            value=None,
            unit="R⊕",
            verdict="unknown",
            explanation="Neither a measured radius nor a mass to estimate one from is available.",
        )

    # The upper taper ends at the top of the radius valley rather than beyond it:
    # above ~1.6 R⊕ the fraction of planets with rocky densities collapses
    # (Rogers 2015), so a 1.8 R⊕ world is far more likely to be a sub-Neptune
    # with no surface than a large rocky planet.
    score = _plateau(radius_earth, 0.8, 1.5, 0.30, RADIUS_VALLEY_UPPER_RE)

    if radius_earth < 0.5:
        detail = (
            "too small to hold onto a substantial atmosphere against thermal escape over "
            "geological time, much as Mars failed to"
        )
    elif radius_earth <= ROCKY_RADIUS_CEILING_RE:
        detail = (
            "within the range where essentially every planet with a measured mass turns out "
            "to be rocky, so a solid surface is likely"
        )
    elif radius_earth < 2.0:
        detail = (
            f"inside the radius valley ({RADIUS_VALLEY_LOWER_RE}–2.0 R⊕), an observed gap that "
            "marks the transition from rocky worlds to those wrapped in thick hydrogen envelopes"
        )
    elif radius_earth < 4.0:
        detail = (
            "large enough that the planet is probably a sub-Neptune with a deep volatile "
            "envelope and no surface to stand on"
        )
    else:
        detail = "a gas-dominated world with no solid surface at any survivable pressure"

    return HabitabilityFactor(
        key="size",
        label="Planet size",
        score=score,
        weight=weight,
        value=radius_earth,
        unit="R⊕",
        verdict=_verdict(score),
        explanation=f"A radius of {radius_earth:.2f} Earth radii puts it {detail}.",
        estimated=estimated,
    )


def _atmosphere_factor(
    escape_velocity: float | None, gravity: float | None, estimated: bool
) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["atmosphere_retention"]
    if not escape_velocity:
        return HabitabilityFactor(
            key="atmosphere_retention",
            label="Atmosphere retention",
            score=None,
            weight=weight,
            value=None,
            unit="km/s",
            verdict="unknown",
            explanation="Mass and radius are both unknown, so atmospheric retention cannot be assessed.",
        )

    # Earth holds a nitrogen atmosphere at 11.2 km/s. Mars, at 5.0 km/s, has
    # lost all but 0.6% of Earth's surface pressure, and Mercury at 4.3 km/s
    # holds nothing at all — so the cliff sits between roughly 5 and 10 km/s.
    # Above ~20 km/s a planet retains primordial hydrogen and becomes a
    # sub-Neptune rather than a terrestrial world.
    score = _plateau(escape_velocity, 9.5, 16.0, 4.2, 26.0)

    gravity_text = f" Surface gravity would be {gravity / 9.80665:.2f} g." if gravity else ""
    if escape_velocity < 6:
        detail = (
            "weak enough that nitrogen and water vapour escape to space over billions of years, "
            "leaving a thin and dry atmosphere"
        )
    elif escape_velocity <= 16:
        detail = "strong enough to hold a nitrogen-oxygen-water atmosphere over geological time"
    else:
        detail = (
            "strong enough to retain primordial hydrogen and helium, which tends to produce a "
            "crushing envelope rather than a habitable surface"
        )

    return HabitabilityFactor(
        key="atmosphere_retention",
        label="Atmosphere retention",
        score=score,
        weight=weight,
        value=escape_velocity,
        unit="km/s",
        verdict=_verdict(score),
        explanation=(
            f"An escape velocity of {escape_velocity:.1f} km/s (Earth: 11.2 km/s) is {detail}."
            f"{gravity_text}"
        ),
        estimated=estimated,
    )


def _composition_factor(density: float | None, estimated: bool) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["composition"]
    if not density:
        return HabitabilityFactor(
            key="composition",
            label="Bulk composition",
            score=None,
            weight=weight,
            value=None,
            unit="g/cm³",
            verdict="unknown",
            explanation="A mass and radius pair is needed to infer bulk composition.",
        )

    score = _plateau(density, 4.0, 7.0, 1.5, 13.0)

    if density < 2.5:
        detail = "far too low for rock — this is a volatile- or gas-dominated world"
    elif density < 4.0:
        detail = (
            "consistent with a substantial water or ice fraction, possibly an ocean world "
            "without exposed land"
        )
    elif density <= 7.0:
        detail = "a good match for an iron-and-silicate world like Earth (5.5 g/cm³)"
    else:
        detail = "unusually high, suggesting an iron-rich, stripped core like Mercury's"

    return HabitabilityFactor(
        key="composition",
        label="Bulk composition",
        score=score,
        weight=weight,
        value=density,
        unit="g/cm³",
        verdict=_verdict(score),
        explanation=f"A bulk density of {density:.2f} g/cm³ is {detail}.",
        estimated=estimated,
    )


def _host_star_factor(
    temp_k: float | None, age_gyr: float | None, spectral_class: str | None
) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["host_star"]
    if not temp_k:
        return HabitabilityFactor(
            key="host_star",
            label="Host star suitability",
            score=None,
            weight=weight,
            value=None,
            unit="K",
            verdict="unknown",
            explanation="The host star's effective temperature is unknown.",
        )

    # G and K stars are the sweet spot: long-lived, quiet, and with habitable
    # zones far enough out that planets are not tidally locked or flare-blasted.
    base = _plateau(temp_k, 4800.0, 6300.0, 2500.0, 7800.0)
    # M dwarfs are not ruled out — they are the majority of stars and of known
    # temperate planets — but flares, XUV erosion and tidal locking are real
    # risks, so they are floored rather than zeroed.
    if temp_k < 3900:
        base = max(base, 0.35)

    notes: list[str] = []
    if temp_k < 3900:
        notes.append(
            "M dwarfs flare violently and emit enough XUV radiation to erode planetary "
            "atmospheres, though they remain stable for tens of billions of years"
        )
    elif temp_k > 7200:
        notes.append(
            "stars this hot burn out in under a billion years, probably too fast for "
            "complex life to arise"
        )
    else:
        notes.append(
            "a quiet, long-lived star of the kind that gives a planet billions of stable years"
        )

    score = base
    if age_gyr is not None and age_gyr > 0:
        if age_gyr < 0.5:
            score *= 0.75
            notes.append(
                f"at only {age_gyr:.1f} Gyr the system is still young and likely volatile"
            )
        elif age_gyr < 1.0:
            score *= 0.9
            notes.append(f"the system is a relatively young {age_gyr:.1f} Gyr old")
        else:
            notes.append(f"the system has had {age_gyr:.1f} Gyr for chemistry to develop")

    label = spectral_class or astro.classify_spectral_type(temp_k) or "?"
    return HabitabilityFactor(
        key="host_star",
        label="Host star suitability",
        score=min(score, 1.0),
        weight=weight,
        value=temp_k,
        unit="K",
        verdict=_verdict(score),
        explanation=(
            f"The host is a {label}-type star at {temp_k:.0f} K: " + "; ".join(notes) + "."
        ),
    )


def _eccentricity_factor(eccentricity: float | None) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["orbital_eccentricity"]
    if eccentricity is None or eccentricity < 0:
        return HabitabilityFactor(
            key="orbital_eccentricity",
            label="Orbital stability",
            score=None,
            weight=weight,
            value=None,
            unit="",
            verdict="unknown",
            explanation="Orbital eccentricity has not been measured.",
        )

    score = _plateau(eccentricity, 0.0, 0.1, -1.0, 0.65)
    if eccentricity < 0.1:
        detail = "nearly circular, so the planet receives a steady amount of starlight all year"
    elif eccentricity < 0.3:
        detail = (
            "moderately eccentric, producing seasonal swings in starlight that a deep ocean "
            "could still buffer"
        )
    else:
        # Flux varies as 1/r^2, so the peak-to-trough ratio is ((1+e)/(1-e))^2.
        ratio = ((1 + eccentricity) / (1 - eccentricity)) ** 2 if eccentricity < 1 else float("inf")
        detail = (
            f"highly eccentric: the starlight reaching the planet varies by a factor of "
            f"{ratio:.1f} between closest and furthest approach"
        )

    return HabitabilityFactor(
        key="orbital_eccentricity",
        label="Orbital stability",
        score=score,
        weight=weight,
        value=eccentricity,
        unit="e",
        verdict=_verdict(score),
        explanation=f"An eccentricity of {eccentricity:.3f} is {detail}.",
    )


def _tidal_locking_factor(
    likelihood: float | None, period_days: float | None
) -> HabitabilityFactor:
    weight = FACTOR_WEIGHTS["tidal_locking"]
    if likelihood is None:
        return HabitabilityFactor(
            key="tidal_locking",
            label="Rotation",
            score=None,
            weight=weight,
            value=None,
            unit="",
            verdict="unknown",
            explanation="The orbital period is unknown, so rotation state cannot be estimated.",
        )

    # Tidal locking is a complication, not a disqualification: 3-D climate
    # models show locked planets can hold liquid water on the day side or along
    # the terminator provided they keep an atmosphere to move heat around.
    score = 1.0 - 0.55 * likelihood
    period_text = f"{period_days:.2f}-day" if period_days else "short"
    if likelihood > 0.7:
        detail = (
            f"Its {period_text} orbit makes tidal locking near-certain, so one hemisphere likely "
            "faces the star permanently. Climate models suggest such worlds can still host "
            "liquid water if their atmosphere redistributes heat."
        )
    elif likelihood > 0.3:
        detail = (
            f"Its {period_text} orbit puts it near the boundary where tidal locking becomes "
            "likely, so its rotation state is genuinely uncertain."
        )
    else:
        detail = (
            f"Its {period_text} orbit is wide enough that the planet probably retains an "
            "independent rotation period, giving it a normal day-night cycle."
        )

    return HabitabilityFactor(
        key="tidal_locking",
        label="Rotation",
        score=score,
        weight=weight,
        value=likelihood,
        unit="P(locked)",
        verdict=_verdict(score),
        explanation=detail,
        estimated=True,
    )


# --- Aggregation ----------------------------------------------------------


def _zone_membership(
    zone: HabitableZone | None,
    axis_au: float | None,
    insolation: float | None,
) -> tuple[bool | None, bool | None]:
    """Habitable-zone membership, preferring flux over distance.

    Falls back to the distance comparison only when no flux is available, since
    flux is the quantity the model is actually defined in.
    """
    if zone is None:
        return (None, None)
    if insolation and insolation > 0:
        return (zone.contains_flux(insolation), zone.contains_flux(insolation, optimistic=True))
    if axis_au:
        return (zone.contains(axis_au), zone.contains(axis_au, optimistic=True))
    return (None, None)


def compute_habitability(planet: PlanetInput) -> HabitabilityResult:
    """Score a planet and explain every component of the result."""
    caveats: list[str] = []

    measured_radius = planet.radius_earth if (planet.radius_earth or 0) > 0 else None
    measured_mass = planet.mass_earth if (planet.mass_earth or 0) > 0 else None
    radius_absent = measured_radius is None and measured_mass is not None
    mass_absent = measured_mass is None and measured_radius is not None
    radius_estimated = radius_absent or (measured_radius is not None and planet.radius_is_estimated)
    mass_estimated = mass_absent or (measured_mass is not None and planet.mass_is_estimated)

    radius = measured_radius or astro.radius_from_mass_earth_units(measured_mass)
    mass = measured_mass or astro.mass_from_radius_earth_units(measured_radius)
    bulk_estimated = radius_estimated or mass_estimated

    if radius_absent:
        caveats.append(
            "Radius was estimated from mass using the Chen & Kipping (2017) mass-radius "
            "relation; it is a statistical expectation, not a measurement."
        )
    if mass_absent:
        caveats.append(
            "Mass was estimated from radius using the Chen & Kipping (2017) mass-radius "
            "relation, which has roughly a factor-of-two scatter for terrestrial planets."
        )
    if planet.mass_is_estimated and measured_mass is not None:
        caveats.append(
            "The catalogued mass is not a measurement: it was derived from the planet's radius "
            "via a mass-radius relationship, so density, surface gravity and escape velocity "
            "below are all modelled rather than observed."
        )
    if planet.mass_is_minimum:
        caveats.append(
            "The catalogued mass is a minimum mass (M·sin i) from radial velocity; the true "
            "mass is larger by an unknown factor set by the orbital inclination."
        )

    luminosity = planet.star_luminosity_solar or astro.stellar_luminosity_solar(
        planet.star_radius_solar, planet.star_effective_temp_k
    )
    axis = planet.semi_major_axis_au or astro.semi_major_axis_au(
        planet.orbital_period_days, planet.star_mass_solar
    )
    if planet.semi_major_axis_au is None and axis is not None:
        caveats.append(
            "Orbital distance was derived from the orbital period and stellar mass via "
            "Kepler's third law."
        )

    insolation = planet.insolation_earth or astro.insolation_earth_units(luminosity, axis)

    temperature = planet.equilibrium_temp_k
    temperature_is_equilibrium = True
    if temperature is None and planet.surface_temp_k:
        temperature = planet.surface_temp_k
        temperature_is_equilibrium = False
    if temperature is None:
        temperature = astro.equilibrium_temperature_k(
            planet.star_effective_temp_k,
            planet.star_radius_solar,
            axis,
            planet.bond_albedo if planet.bond_albedo is not None else 0.3,
        )
        if temperature is not None:
            caveats.append(
                "Equilibrium temperature was computed assuming a Bond albedo of 0.3 and "
                "efficient day-night heat redistribution."
            )

    zone = habitable_zone(planet.star_effective_temp_k, luminosity, mass)
    if zone and zone.extrapolated:
        caveats.append(
            "The host star's temperature lies outside the 2600–7200 K range over which the "
            "Kopparapu habitable-zone model is calibrated, so its edges are extrapolated."
        )

    density = astro.density_g_cm3(mass, radius)
    escape_velocity = astro.escape_velocity_km_s(mass, radius)
    gravity = astro.surface_gravity_ms2(mass, radius)
    locking = astro.transit_tidal_locking_likelihood(
        planet.orbital_period_days, planet.star_mass_solar
    )

    factors = [
        _habitable_zone_factor(zone, axis, insolation),
        _temperature_factor(temperature, temperature_is_equilibrium),
        _size_factor(radius, radius_estimated),
        _atmosphere_factor(escape_velocity, gravity, bulk_estimated),
        _composition_factor(density, bulk_estimated),
        _host_star_factor(
            planet.star_effective_temp_k,
            planet.star_age_gyr,
            astro.classify_spectral_type(planet.star_effective_temp_k),
        ),
        _eccentricity_factor(planet.eccentricity),
        _tidal_locking_factor(locking, planet.orbital_period_days),
    ]

    scored = [f for f in factors if f.score is not None]
    available_weight = sum(f.weight for f in scored)
    scored_keys = {f.key for f in scored}
    missing_required = [k for k in REQUIRED_FACTOR_KEYS if k not in scored_keys]

    if not scored or available_weight < MINIMUM_SCORABLE_WEIGHT or len(
        missing_required
    ) == len(REQUIRED_FACTOR_KEYS):
        reason = (
            "Neither this planet's temperature nor its position relative to the habitable zone "
            "is constrained — typical of microlensing and pulsar-timing detections, where the "
            "host star is never characterised. Without either, a habitability score would be "
            "arithmetic on the few properties that happen to be known rather than a statement "
            "about the planet."
            if len(missing_required) == len(REQUIRED_FACTOR_KEYS)
            else (
                f"Only {available_weight:.0%} of the scoring weight could be evaluated, below the "
                f"{MINIMUM_SCORABLE_WEIGHT:.0%} needed for a meaningful result."
            )
        )
        return HabitabilityResult(
            score=None,
            band="insufficient data",
            confidence=round(max(available_weight, 0.0), 3),
            factors=factors,
            caveats=caveats
            + [reason, "Absence of data is not evidence of hostility."],
            size_class=classify_size(radius, mass),
            thermal_class=classify_thermal(temperature),
            habitable_zone=zone,
            in_conservative_hz=_zone_membership(zone, axis, insolation)[0],
            in_optimistic_hz=_zone_membership(zone, axis, insolation)[1],
            summary="Too little is known about this planet to assess its habitability.",
        )

    log_sum = sum(
        f.weight * math.log(max(f.score or 0.0, _FACTOR_FLOOR)) for f in scored
    )
    weighted = math.exp(log_sum / available_weight)
    score_100 = round(weighted * 100.0, 1)

    # Confidence is reported alongside the score rather than folded into it: a
    # planet can be genuinely Earth-like on every property we can measure while
    # half of those properties are estimates. Conflating the two would hide which
    # is the case.
    estimated_weight = sum(f.weight for f in scored if f.estimated)
    confidence = available_weight * (1.0 - 0.35 * (estimated_weight / available_weight))
    if missing_required:
        confidence *= 0.8
    confidence = round(min(max(confidence, 0.0), 1.0), 3)

    band = score_band(score_100)
    in_conservative, in_optimistic = _zone_membership(zone, axis, insolation)

    strengths = sorted(
        (f for f in scored if f.score is not None and f.score >= 0.65),
        key=lambda f: -(f.score or 0) * f.weight,
    )
    weaknesses = sorted(
        (f for f in scored if f.score is not None and f.score < 0.4),
        key=lambda f: (f.score or 0) * f.weight,
    )

    parts = [f"Scores {score_100:.0f}/100 ({band})"]
    if strengths:
        parts.append("helped most by " + ", ".join(f.label.lower() for f in strengths[:2]))
    if weaknesses:
        parts.append("held back by " + ", ".join(f.label.lower() for f in weaknesses[:2]))
    summary = "; ".join(parts) + "."

    return HabitabilityResult(
        score=score_100,
        band=band,
        confidence=confidence,
        factors=factors,
        caveats=caveats,
        size_class=classify_size(radius, mass),
        thermal_class=classify_thermal(temperature),
        habitable_zone=zone,
        in_conservative_hz=in_conservative,
        in_optimistic_hz=in_optimistic,
        summary=summary,
    )
