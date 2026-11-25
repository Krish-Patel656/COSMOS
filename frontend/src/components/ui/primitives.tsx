import type { ReactNode } from "react";

import { clsx } from "@/lib/format";

export function Panel({
  children,
  className,
  as: Component = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "aside";
}) {
  return (
    <Component
      className={clsx(
        "rounded-panel border border-void-700 bg-void-850/80 backdrop-blur-md",
        className,
      )}
    >
      {children}
    </Component>
  );
}

export function Badge({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        className ?? "bg-void-700/60 text-starlight-200 ring-1 ring-void-600",
      )}
    >
      {children}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow ? (
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-aurora-400">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-semibold text-starlight-50 sm:text-3xl">{title}</h2>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-starlight-300">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

/**
 * Label/value pair.
 *
 * `estimated` renders a visible marker rather than only a tooltip, because
 * whether a number was measured or modelled changes how much weight a reader
 * should give it, and that is not an optional detail.
 */
export function Stat({
  label,
  value,
  hint,
  estimated = false,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  estimated?: boolean;
  className?: string;
}) {
  return (
    <div className={clsx("min-w-0", className)}>
      <dt className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-starlight-400">
        <span className="truncate">{label}</span>
        {estimated ? <EstimatedMark /> : null}
      </dt>
      <dd className="mt-1 font-display text-lg text-starlight-50 tabular-nums">{value}</dd>
      {hint ? <p className="mt-0.5 text-xs text-starlight-400">{hint}</p> : null}
    </div>
  );
}

export function EstimatedMark({ className }: { className?: string }) {
  return (
    <span
      className={clsx(
        "rounded bg-solar-500/15 px-1 text-[0.625rem] font-semibold uppercase tracking-wide text-solar-300",
        className,
      )}
      title="Modelled or inferred value, not a direct measurement"
    >
      est
      <span className="sr-only"> — modelled or inferred, not directly measured</span>
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={clsx("animate-pulse rounded-lg bg-void-800/80", className)}
    />
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-panel border border-dashed border-void-700 px-6 py-16 text-center">
      <h3 className="font-display text-lg text-starlight-100">{title}</h3>
      {description ? (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-starlight-400">{description}</p>
      ) : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}

export function ErrorNotice({ message, className }: { message: string; className?: string }) {
  return (
    <div
      role="alert"
      className={clsx(
        "rounded-lg border border-ember-500/40 bg-ember-500/10 px-4 py-3 text-sm text-ember-300",
        className,
      )}
    >
      {message}
    </div>
  );
}

/**
 * Horizontal bar for a 0–1 or 0–100 value.
 *
 * Accessible as a `meter`, with `aria-valuetext` carrying the formatted figure
 * so a screen reader announces "0.82 of 1" rather than a bare number.
 */
export function Meter({
  value,
  max = 1,
  fillClass = "bg-aurora-400",
  label,
  valueText,
  className,
}: {
  value: number;
  max?: number;
  fillClass?: string;
  label: string;
  valueText?: string;
  className?: string;
}) {
  const fraction = Math.max(0, Math.min(1, value / max));
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Number(value.toFixed(3))}
      aria-valuetext={valueText}
      className={clsx("h-1.5 w-full overflow-hidden rounded-full bg-void-700", className)}
    >
      <div
        className={clsx("h-full rounded-full transition-[width] duration-500", fillClass)}
        style={{ width: `${fraction * 100}%` }}
      />
    </div>
  );
}

/**
 * Artistic-rendering disclosure.
 *
 * Every planetary surface in this app is invented. Saying so once in a footnote
 * would not be enough, so the notice travels with the imagery it describes.
 */
export function ArtisticNotice({
  basis,
  className,
}: {
  basis?: string[];
  className?: string;
}) {
  return (
    <p className={clsx("text-xs leading-relaxed text-starlight-400", className)}>
      <span className="font-semibold text-solar-300">Artistic rendering.</span> No exoplanet
      surface has ever been imaged.
      {basis && basis.length > 0 ? (
        <> This appearance is inferred from {basis.join(", ")}.</>
      ) : (
        <> This appearance is a visualisation, not an observation.</>
      )}
    </p>
  );
}
