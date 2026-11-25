"use client";

import { useEffect, useRef, useState } from "react";

import { clsx } from "@/lib/format";
import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { type RenderQuality, usePreferences } from "@/lib/store/preferences";

const QUALITY_OPTIONS: { value: RenderQuality; label: string; hint: string }[] = [
  { value: "low", label: "Low", hint: "No post-processing, coarse geometry" },
  { value: "medium", label: "Medium", hint: "Balanced" },
  { value: "high", label: "High", hint: "Full bloom and fine geometry" },
];

/**
 * Display and accessibility controls.
 *
 * These are deliberately in the header rather than buried on a settings page.
 * A user on an integrated GPU, or one for whom the drifting scenes are
 * uncomfortable, needs to find them in the first few seconds — not after
 * struggling through the site first.
 */
export function DisplaySettings() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const systemReducedMotion = useReducedMotion();

  const flatMode = usePreferences((state) => state.flatMode);
  const renderQuality = usePreferences((state) => state.renderQuality);
  const forceReducedMotion = usePreferences((state) => state.forceReducedMotion);
  const showScienceNotes = usePreferences((state) => state.showScienceNotes);
  const setFlatMode = usePreferences((state) => state.setFlatMode);
  const setRenderQuality = usePreferences((state) => state.setRenderQuality);
  const setForceReducedMotion = usePreferences((state) => state.setForceReducedMotion);
  const setShowScienceNotes = usePreferences((state) => state.setShowScienceNotes);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!panelRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={panelRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label="Display and accessibility settings"
        className="rounded-lg p-2 text-starlight-300 transition-colors hover:bg-void-800/60 hover:text-starlight-100"
      >
        <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
          <circle cx="10" cy="10" r="2.6" />
          <path d="M10 1.8v2.2M10 16v2.2M3.2 3.2l1.6 1.6M15.2 15.2l1.6 1.6M1.8 10h2.2M16 10h2.2M3.2 16.8l1.6-1.6M15.2 4.8l1.6-1.6" strokeLinecap="round" />
        </svg>
      </button>

      {open ? (
        <div className="absolute right-0 top-11 z-50 w-80 rounded-panel border border-void-700 bg-void-900/97 p-4 shadow-2xl backdrop-blur-xl">
          <h2 className="mb-3 font-display text-sm font-semibold text-starlight-50">
            Display &amp; accessibility
          </h2>

          <div className="space-y-4">
            <Toggle
              label="Flat mode"
              description="Replace every 3D scene with an equivalent 2D view. Useful on low-powered hardware or if moving scenes are uncomfortable."
              checked={flatMode}
              onChange={setFlatMode}
            />

            <Toggle
              label="Reduce motion"
              description={
                systemReducedMotion
                  ? "Your system already requests reduced motion, which COSMOS is honouring."
                  : "Stop orbital motion, planetary rotation and camera drift."
              }
              checked={forceReducedMotion || systemReducedMotion}
              disabled={systemReducedMotion}
              onChange={setForceReducedMotion}
            />

            <Toggle
              label="Show science notes"
              description="Inline explanations of where each number comes from and how reliable it is."
              checked={showScienceNotes}
              onChange={setShowScienceNotes}
            />

            <fieldset disabled={flatMode} className={clsx(flatMode && "opacity-50")}>
              <legend className="text-sm font-medium text-starlight-100">Render quality</legend>
              <p className="mb-2 text-xs leading-relaxed text-starlight-400">
                Controls resolution, geometry detail and post-processing.
              </p>
              <div className="flex gap-1.5">
                {QUALITY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setRenderQuality(option.value)}
                    aria-pressed={renderQuality === option.value}
                    title={option.hint}
                    className={clsx(
                      "flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors",
                      renderQuality === option.value
                        ? "bg-aurora-500 text-void-950"
                        : "bg-void-800 text-starlight-300 hover:bg-void-700",
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </fieldset>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={clsx("flex cursor-pointer gap-3", disabled && "cursor-not-allowed opacity-70")}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className={clsx(
          "mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors",
          checked ? "bg-aurora-500" : "bg-void-600",
        )}
      >
        <span
          className={clsx(
            "size-4 rounded-full bg-void-950 transition-transform",
            checked && "translate-x-4",
          )}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-starlight-100">{label}</span>
        <span className="block text-xs leading-relaxed text-starlight-400">{description}</span>
      </span>
    </label>
  );
}
