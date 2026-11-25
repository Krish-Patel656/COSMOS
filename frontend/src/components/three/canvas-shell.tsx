"use client";

import { AdaptiveDpr, Preload } from "@react-three/drei";
import { Canvas, type CanvasProps } from "@react-three/fiber";
import {
  type ReactNode,
  Suspense,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ACESFilmicToneMapping } from "three";

import { clsx } from "@/lib/format";
import { QUALITY_DPR, usePreferences } from "@/lib/store/preferences";

/**
 * Probe for a usable WebGL2 context.
 *
 * Checked once at module level on first call and cached. A missing context is
 * not an error state to apologise for — the 2D fallback is a first-class view,
 * so this only decides which of the two to mount.
 */
let webglSupport: boolean | null = null;

function detectWebgl(): boolean {
  if (webglSupport !== null) return webglSupport;
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const context =
      canvas.getContext("webgl2") ??
      canvas.getContext("webgl") ??
      canvas.getContext("experimental-webgl");
    webglSupport = context !== null;
  } catch {
    webglSupport = false;
  }
  return webglSupport;
}

export function useWebglAvailable(): boolean | null {
  // Starts as null (undetermined) so the server and the first client render
  // agree, and neither view flashes before the probe has run.
  const [available, setAvailable] = useState<boolean | null>(null);
  useEffect(() => setAvailable(detectWebgl()), []);
  return available;
}

interface CanvasShellProps extends Omit<CanvasProps, "children" | "dpr"> {
  children: ReactNode;
  /** Rendered instead of the canvas in flat mode or when WebGL is unavailable. */
  fallback: ReactNode;
  /** Describes the scene for assistive technology. */
  label: string;
  className?: string;
  /** Shown inside the canvas area while assets and geometry initialise. */
  loading?: ReactNode;
}

/**
 * Wrapper around the R3F canvas that handles the things every scene needs:
 * capability detection, the user's flat-mode and quality preferences, adaptive
 * resolution, and an accessible description.
 *
 * The canvas itself is marked `aria-hidden` and removed from the tab order. A
 * WebGL canvas is an opaque pixel buffer to a screen reader, so every scene is
 * paired with an equivalent DOM list of the same objects — that list is the
 * accessible interface, and it is always present, not only in fallback mode.
 */
export function CanvasShell({
  children,
  fallback,
  label,
  className,
  loading,
  camera,
  ...canvasProps
}: CanvasShellProps) {
  const webgl = useWebglAvailable();
  const flatMode = usePreferences((state) => state.flatMode);
  const renderQuality = usePreferences((state) => state.renderQuality);

  const dpr = useMemo(() => QUALITY_DPR[renderQuality], [renderQuality]);

  if (flatMode || webgl === false) {
    return <>{fallback}</>;
  }

  if (webgl === null) {
    return (
      <div className={clsx("size-full", className)}>
        {loading ?? <CanvasSkeleton />}
      </div>
    );
  }

  return (
    <div className={clsx("size-full", className)}>
      <Canvas
        aria-hidden
        tabIndex={-1}
        dpr={dpr}
        camera={camera}
        gl={{
          antialias: renderQuality !== "low",
          powerPreference: "high-performance",
          alpha: true,
          toneMapping: ACESFilmicToneMapping,
          toneMappingExposure: 1.05,
        }}
        // `demand` would be cheaper, but these scenes animate continuously; the
        // reduced-motion path stops the motion at the source instead.
        frameloop="always"
        {...canvasProps}
      >
        <Suspense fallback={null}>
          {children}
          <Preload all />
        </Suspense>
        <AdaptiveDpr pixelated />
      </Canvas>
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function CanvasSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "flex size-full items-center justify-center rounded-panel bg-void-900/60",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="size-8 animate-spin rounded-full border-2 border-void-600 border-t-aurora-400" />
        <p className="text-xs uppercase tracking-widest text-starlight-400">
          Initialising scene
        </p>
      </div>
    </div>
  );
}
