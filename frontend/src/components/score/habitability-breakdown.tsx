import { EstimatedMark, Meter } from "@/components/ui/primitives";
import { EM_DASH, clsx, formatPercent, formatScaled } from "@/lib/format";
import { bandStyle, confidenceLabel, verdictStyle } from "@/lib/scores";
import type { Habitability, HabitabilityFactor } from "@/lib/types";

/**
 * Full explanation of a habitability score.
 *
 * This component is the answer to the question the score itself raises. Each
 * contributing factor shows its measured value, the weight it carries, the
 * verdict the engine reached, and a sentence saying why — so a reader can
 * disagree with the conclusion on specific grounds rather than taking a number
 * on trust.
 */
export function HabitabilityBreakdown({
  habitability,
  className,
}: {
  habitability: Habitability;
  className?: string;
}) {
  const style = bandStyle(habitability.band);
  const evaluated = habitability.factors.filter((factor) => factor.score !== null);
  const unevaluated = habitability.factors.filter((factor) => factor.score === null);

  return (
    <div className={clsx("space-y-6", className)}>
      <div>
        <p className="text-sm leading-relaxed text-starlight-200">{habitability.summary}</p>

        <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wider text-starlight-400">Verdict</dt>
            <dd className={clsx("mt-1 text-sm font-semibold", style.text)}>{style.label}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-starlight-400">Confidence</dt>
            <dd className="mt-1 text-sm font-semibold text-starlight-100 tabular-nums">
              {formatPercent(habitability.confidence)}
              <span className="ml-1.5 font-normal text-starlight-400">
                {confidenceLabel(habitability.confidence)}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-starlight-400">Size class</dt>
            <dd className="mt-1 text-sm font-semibold text-starlight-100">
              {habitability.size_class ?? EM_DASH}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-starlight-400">Thermal class</dt>
            <dd className="mt-1 text-sm font-semibold text-starlight-100">
              {habitability.thermal_class ?? EM_DASH}
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h4 className="mb-1 font-display text-sm font-semibold uppercase tracking-wider text-starlight-200">
          Contributing factors
        </h4>
        <p className="mb-4 text-xs leading-relaxed text-starlight-400">
          Factors are combined as a weighted geometric mean, so a single
          disqualifying property — a surface hot enough to melt lead, say — cannot
          be outvoted by several favourable ones.
        </p>

        <ul className="space-y-3">
          {evaluated.map((factor) => (
            <FactorRow key={factor.key} factor={factor} />
          ))}
        </ul>
      </div>

      {unevaluated.length > 0 ? (
        <div>
          <h4 className="mb-2 font-display text-sm font-semibold uppercase tracking-wider text-starlight-200">
            Not evaluated
          </h4>
          <p className="mb-3 text-xs leading-relaxed text-starlight-400">
            These factors were excluded because the required measurements are
            missing. Their weight was redistributed across the remaining factors,
            which is why the confidence figure above is below 100%.
          </p>
          <ul className="space-y-2">
            {unevaluated.map((factor) => (
              <li
                key={factor.key}
                className="flex flex-wrap items-baseline gap-x-2 text-xs text-starlight-400"
              >
                <span className="font-medium text-starlight-300">{factor.label}</span>
                <span>{factor.explanation}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {habitability.caveats.length > 0 ? (
        <div className="rounded-lg border border-solar-500/30 bg-solar-500/5 p-4">
          <h4 className="mb-2 font-display text-sm font-semibold text-solar-300">
            Caveats on this score
          </h4>
          <ul className="space-y-1.5 text-xs leading-relaxed text-starlight-300">
            {habitability.caveats.map((caveat) => (
              <li key={caveat} className="flex gap-2">
                <span aria-hidden className="text-solar-400">
                  •
                </span>
                <span>{caveat}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function FactorRow({ factor }: { factor: HabitabilityFactor }) {
  const verdict = verdictStyle(factor.verdict);
  const score = factor.score ?? 0;

  return (
    <li className="rounded-lg border border-void-700/70 bg-void-900/40 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <div className="flex items-center gap-2">
          <span aria-hidden className={clsx("size-2 shrink-0 rounded-full", verdict.dot)} />
          <span className="text-sm font-medium text-starlight-100">{factor.label}</span>
          {factor.estimated ? <EstimatedMark /> : null}
        </div>
        <div className="flex items-baseline gap-3 text-xs tabular-nums">
          <span className="text-starlight-300">
            {factor.value === null ? EM_DASH : formatScaled(factor.value)}
            {factor.unit && factor.value !== null ? (
              <span className="ml-0.5 text-starlight-400">{factor.unit}</span>
            ) : null}
          </span>
          <span className={clsx("font-semibold", verdict.text)}>{verdict.label}</span>
          <span
            className="text-starlight-400"
            title={`This factor carries ${formatPercent(factor.weight)} of the total weight`}
          >
            {formatPercent(factor.weight)} weight
          </span>
        </div>
      </div>

      <Meter
        value={score}
        label={`${factor.label} sub-score`}
        valueText={`${(score * 100).toFixed(0)} out of 100`}
        fillClass={verdict.dot}
        className="my-2"
      />

      <p className="text-xs leading-relaxed text-starlight-300">{factor.explanation}</p>
    </li>
  );
}
