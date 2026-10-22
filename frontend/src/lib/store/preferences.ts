"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type RenderQuality = "low" | "medium" | "high";

interface PreferencesState {
  /**
   * When true, every 3D scene is replaced by an equivalent 2D/DOM view.
   *
   * Offered as an explicit, persisted choice rather than only as an automatic
   * fallback: WebGL can be available and still unusable, on a low-powered
   * machine or for a user who finds the moving scenes uncomfortable.
   */
  flatMode: boolean;
  renderQuality: RenderQuality;
  /** Overrides the OS preference when the user asks for stillness explicitly. */
  forceReducedMotion: boolean;
  showScienceNotes: boolean;
  setFlatMode: (value: boolean) => void;
  setRenderQuality: (value: RenderQuality) => void;
  setForceReducedMotion: (value: boolean) => void;
  setShowScienceNotes: (value: boolean) => void;
}

export const usePreferences = create<PreferencesState>()(
  persist(
    (set) => ({
      flatMode: false,
      renderQuality: "high",
      forceReducedMotion: false,
      showScienceNotes: true,
      setFlatMode: (flatMode) => set({ flatMode }),
      setRenderQuality: (renderQuality) => set({ renderQuality }),
      setForceReducedMotion: (forceReducedMotion) => set({ forceReducedMotion }),
      setShowScienceNotes: (showScienceNotes) => set({ showScienceNotes }),
    }),
    { name: "cosmos.preferences", version: 1 },
  ),
);

/** Device pixel ratio ceiling per quality tier, fed to the R3F canvas. */
export const QUALITY_DPR: Record<RenderQuality, [number, number]> = {
  low: [0.6, 1],
  medium: [0.8, 1.5],
  high: [1, 2],
};

/** Sphere tessellation per quality tier. */
export const QUALITY_SEGMENTS: Record<RenderQuality, number> = {
  low: 24,
  medium: 48,
  high: 96,
};
