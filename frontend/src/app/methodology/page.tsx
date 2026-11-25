import { PageShell } from "@/components/layout/page-shell";

export default function MethodologyPage() {
  return (
    <PageShell>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-aurora-400">
        Scientific basis
      </p>
      <h1 className="font-display text-4xl text-starlight-50">How COSMOS scores a world</h1>
      <p className="mt-4 max-w-3xl text-base leading-relaxed text-starlight-300">
        There is no accepted single number for habitability. COSMOS does not pretend otherwise. It
        takes the handful of properties we actually measure, scores each one against conditions that
        matter for surface liquid water, and reports the result together with the per-factor
        reasoning, the data we had to guess at, and a separate confidence figure.
      </p>

      <article className="prose-cosmos mt-12 max-w-3xl space-y-10 text-sm leading-relaxed text-starlight-300">
        <section>
          <h2 className="font-display text-2xl text-starlight-50">Data</h2>
          <p className="mt-3">
            Planetary parameters come from the NASA Exoplanet Archive{" "}
            <em>Planetary Systems Composite Parameters</em> table (<code>pscomppars</code>), one row
            per confirmed planet with the most complete published set. The Solar System is injected
            from IAU/NASA fact-sheet values and scored by the same engine so Earth, Venus and Mars
            are a sanity check, not a special case.
          </p>
          <p className="mt-3">
            Measured values are never overwritten by estimates. When radius or mass has to be filled
            from the Chen &amp; Kipping (2017) mass–radius relation, the corresponding{" "}
            <span className="text-solar-300">est</span> flag is stored and shown in the UI. Radial
            velocity masses with provenance <code>Msini</code> are flagged as minimum masses.
          </p>
        </section>

        <section>
          <h2 className="font-display text-2xl text-starlight-50">Habitable zone</h2>
          <p className="mt-3">
            Zone edges follow Kopparapu et al. (2013, 2014): conservative limits are the runaway
            greenhouse and maximum greenhouse fluxes; optimistic limits are the recent-Venus and
            early-Mars empirical edges. Both belts are drawn on the 3D system view because “in the
            habitable zone” is a choice of definition, not a binary fact.
          </p>
          <p className="mt-3">
            Stars cooler than 2600 K or hotter than 7200 K fall outside the model’s calibration. The
            API still computes edges and marks them <em>extrapolated</em>.
          </p>
        </section>

        <section>
          <h2 className="font-display text-2xl text-starlight-50">Habitability score</h2>
          <p className="mt-3">
            Factors (temperature, radius, mass/gravity, habitable-zone position, eccentricity,
            insolation, stellar type, stellar age) are combined as a weighted geometric mean. A
            single disqualifying property cannot be outvoted by several pleasant ones. Missing
            factors are dropped and their weight redistributed; confidence is the fraction of total
            weight that rested on measured inputs.
          </p>
          <p className="mt-3">
            Bands: exceptional ≥ 80, promising ≥ 65, plausible ≥ 50, marginal ≥ 30, unlikely ≥ 15,
            otherwise hostile. Earth scores 100 by construction. Venus scores poorly despite an
            Earth-like radius because the runaway-greenhouse limit places it inside the inner edge.
          </p>
        </section>

        <section>
          <h2 className="font-display text-2xl text-starlight-50">Earth Similarity Index</h2>
          <p className="mt-3">
            ESI follows Schulze-Makuch et al. (2011): a weighted geometric mean of radius, density,
            escape velocity and temperature, split into interior and surface groups. High ESI is not
            habitability. It means bulk physical properties resemble Earth. A lava world of Earth’s
            size can score well on interior ESI and terribly on surface ESI; the breakdown shows
            both.
          </p>
          <p className="mt-3">
            Exoplanet temperatures in the archive are almost always equilibrium temperatures.
            COSMOS therefore compares them to Earth’s 255 K equilibrium temperature, not the 288 K
            surface value, and says so in the note on that component.
          </p>
        </section>

        <section>
          <h2 className="font-display text-2xl text-starlight-50">What the 3D scenes are not</h2>
          <p className="mt-3">
            No exoplanet surface has been imaged. Colours, clouds, bands and atmospheres are
            illustrations derived from radius, mass, temperature and insolation. Every scene carries
            an artistic-rendering notice. Orbits are log-compressed so TRAPPIST-1 and the Solar
            System are both legible; planetary radii are cube-root compressed so a Jupiter does not
            erase an Earth. The stellar map preserves direction on the sky exactly and only
            compresses radial distance.
          </p>
        </section>

        <section>
          <h2 className="font-display text-2xl text-starlight-50">Limits, stated plainly</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              Atmospheric composition is unknown for virtually every planet here, and it is the
              largest control on surface temperature. Equilibrium temperature is a proxy.
            </li>
            <li>
              Equilibrium temperature cannot distinguish Earth from Venus (255 K vs 227 K). Only the
              habitable-zone factor separates them.
            </li>
            <li>
              The simulator uses the same model. Tuning a hypothetical world to 90 does not mean a
              real planet with those properties is inhabited.
            </li>
          </ul>
        </section>
      </article>
    </PageShell>
  );
}
