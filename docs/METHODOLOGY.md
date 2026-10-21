# COSMOS scoring methodology

This is the engineering-facing companion to the in-app `/methodology` page.

## Catalogue

- Source: NASA Exoplanet Archive TAP, table `pscomppars`.
- Units are stored with explicit suffixes (`radius_earth`, `distance_pc`).
- Jupiter-unit columns are used only when the Earth-unit column is blank.
- Archive `st_lum` is log10(L/L☉). Treating it as linear would collapse habitable zones.

## Habitable zone

Kopparapu et al. 2013/2014 moist-greenhouse / maximum-greenhouse (conservative) and recent-Venus / early-Mars (optimistic). A 1 Earth-mass reference planet is used for the system-level rings.

## Habitability

Weighted geometric mean over evaluable factors. Confidence = fraction of total weight backed by measured (not estimated) inputs. Bands are assigned in `app/science/habitability.py` (`score_band`).

## ESI

Schulze-Makuch et al. 2011. Interior group: radius, density. Surface group: escape velocity, temperature. Exoplanet equilibrium temperatures are compared to Earth's 255 K equilibrium temperature, not 288 K surface temperature.

## Appearance

`app/science/appearance.py` maps bulk properties to a render recipe. The UI must always disclose that the result is artistic.

## Simulator

`POST /api/v1/simulate` calls `compute_habitability` and `compute_esi` with the same functions used at ingest. Presets live in `app/api/v1/simulate.py`.
