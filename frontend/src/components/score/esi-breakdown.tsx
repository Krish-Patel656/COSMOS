import { EstimatedMark, Meter } from "@/components/ui/primitives";
import { EM_DASH, clsx, formatEsi, formatPercent, formatScaled } from "@/lib/format";
import { esiLabel } from "@/lib/scores";
import type { Esi } from "@/lib/types";

/**
 * Breakdown of the Earth Similarity Index.
 *
 * ESI is a geometric mean over four properties in two groups (interior and
 * surface), following Schulze-Makuch et al. (2011). Showing the two group scores
 * separately matters because they can diverge sharply: a world can be a near
 * twin of Earth in bulk composition while being hundreds of degrees too hot.
 */
export function EsiBreakdown({ esi, className }: { esi: Esi; className?: string }) {
  return (
    <div className={clsx("space-y-5", className)}>
      <div className="flex flex-wrap items-center gap-6">
        <div>
          <p className="text-xs uppercase tracking-wider text-starlight-400">Overall</p>
          <p className="font-display text-3xl font-semibold text-starlight-50 tabular-nums">
            {formatEsi(esi.overall)}
          </p>
          <p className="text-xs text-starlight-400">{esiLabel(esi.overall)}</p>
        </div>
        <div className="flex gap-6">
          <GroupScore label="Interior" value={esi.interior} hint="Radius and bulk density" />
          <GroupScore
            label="Surface"
            value={esi.surface}
            hint="Escape velocity and temperature"
          />
        </div>
      </div>

      <ul className="space-y-3">
        {esi.components.map((component) => {
          const similarity = component.similarity;
          return (
            <li
              key={component.key}
              className="rounded-lg border border-void-700/70 bg-void-900/40 p-3"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-starlight-100">
                    {component.label}
                  </span>
                  {component.estimated ? <EstimatedMark /> : null}
                </div>
                <div className="flex items-baseline gap-3 text-xs tabular-nums">
                  <span className="text-starlight-300">
                    {component.value === null ? EM_DASH : formatScaled(component.value)}
                    {component.unit ? (
                      <span className="ml-0.5 text-starlight-400">{component.unit}</span>
                    ) : null}
                  </span>
                  <span className="text-starlight-400">
                    Earth: {formatScaled(component.earth_value)}
                  </span>
                  <span className="font-semibold text-starlight-100">
                    {similarity === null ? EM_DASH : formatEsi(similarity)}
                  </span>
                </div>
              </div>

              <Meter
                value={similarity ?? 0}
                label={`${component.label} similarity to Earth`}
                valueText={
                  similarity === null
                    ? "not computable"
                    : `${formatEsi(similarity)} similarity to Earth`
                }
                fillClass="bg-aurora-400"
                className="my-2"
              />

              <p className="text-xs leading-relaxed text-starlight-400">
                {component.note} Weighted {formatScaled(component.weight)} within its group
                — a higher exponent means this property penalises differences more sharply.
              </p>
            </li>
          );
        })}
      </ul>

      <p className="text-xs leading-relaxed text-starlight-400">
        Data completeness: {formatPercent(esi.data_completeness)} of the four inputs are direct
        measurements. A high similarity built on modelled inputs says more about the model than
        about the planet.
      </p>
    </div>
  );
}

function GroupScore({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | null;
  hint: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-starlight-400">{label}</p>
      <p className="font-display text-xl font-semibold text-starlight-100 tabular-nums">
        {formatEsi(value)}
      </p>
      <p className="text-xs text-starlight-400">{hint}</p>
    </div>
  );
}
