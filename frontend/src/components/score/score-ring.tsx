import { clsx, formatScore } from "@/lib/format";
import { bandStyle, confidenceLabel } from "@/lib/scores";
import type { HabitabilityBand } from "@/lib/types";

const SIZES = {
  sm: { box: 72, stroke: 6, value: "text-xl", label: "text-[0.5rem]" },
  md: { box: 112, stroke: 8, value: "text-3xl", label: "text-[0.625rem]" },
  lg: { box: 160, stroke: 10, value: "text-5xl", label: "text-xs" },
} as const;

/**
 * Circular gauge for a 0–100 habitability score.
 *
 * The confidence figure is drawn as a second, inner arc rather than being mixed
 * into the main one. A score of 85 backed by two measured properties and a score
 * of 85 backed by eight are very different claims, and the ring shows both at
 * once instead of averaging them into a single misleading number.
 */
export function ScoreRing({
  score,
  band,
  confidence,
  size = "md",
  className,
}: {
  score: number | null;
  band: HabitabilityBand | null;
  confidence?: number | null;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const style = bandStyle(band);
  const dims = SIZES[size];
  const radius = (dims.box - dims.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const fraction = score === null ? 0 : Math.max(0, Math.min(1, score / 100));

  const innerRadius = radius - dims.stroke * 1.6;
  const innerCircumference = 2 * Math.PI * innerRadius;
  const confidenceFraction =
    confidence === null || confidence === undefined ? null : Math.max(0, Math.min(1, confidence));

  const describedScore = score === null ? "not scored" : `${formatScore(score)} out of 100`;

  return (
    <div
      className={clsx("relative inline-flex shrink-0", className)}
      style={{ width: dims.box, height: dims.box }}
      role="img"
      aria-label={`Habitability score: ${describedScore}. ${style.label}.${
        confidenceFraction !== null
          ? ` Data confidence: ${Math.round(confidenceFraction * 100)}%, ${confidenceLabel(confidenceFraction)}.`
          : ""
      }`}
    >
      <svg
        width={dims.box}
        height={dims.box}
        viewBox={`0 0 ${dims.box} ${dims.box}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={dims.box / 2}
          cy={dims.box / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={dims.stroke}
          className="text-void-700"
        />
        {score !== null ? (
          <circle
            cx={dims.box / 2}
            cy={dims.box / 2}
            r={radius}
            fill="none"
            stroke={style.hex}
            strokeWidth={dims.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - fraction)}
            className="transition-[stroke-dashoffset] duration-700 ease-out"
          />
        ) : null}

        {confidenceFraction !== null && innerRadius > 0 ? (
          <circle
            cx={dims.box / 2}
            cy={dims.box / 2}
            r={innerRadius}
            fill="none"
            stroke="currentColor"
            strokeWidth={Math.max(2, dims.stroke / 3)}
            strokeLinecap="round"
            strokeDasharray={innerCircumference}
            strokeDashoffset={innerCircumference * (1 - confidenceFraction)}
            className="text-starlight-400/60 transition-[stroke-dashoffset] duration-700 ease-out"
          />
        ) : null}
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={clsx("font-display font-semibold tabular-nums", dims.value, style.text)}>
          {formatScore(score)}
        </span>
        <span
          className={clsx(
            "font-semibold uppercase tracking-[0.12em] text-starlight-400",
            dims.label,
          )}
        >
          {score === null ? "no data" : "/ 100"}
        </span>
      </div>
    </div>
  );
}
