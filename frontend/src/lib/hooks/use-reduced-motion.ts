"use client";

import { useEffect, useState } from "react";

import { usePreferences } from "@/lib/store/preferences";

const QUERY = "(prefers-reduced-motion: reduce)";

/**
 * Track the OS-level reduced-motion preference.
 *
 * CSS already neutralises declarative animation, but the 3D scenes animate
 * inside a `requestAnimationFrame` loop that no stylesheet can reach. Components
 * read this hook to stop orbital motion, planetary rotation and camera
 * auto-rotation, leaving a static — and still fully explorable — scene.
 *
 * Initialises to `false` and corrects after mount so that server and client
 * render the same markup on the first pass.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(QUERY);
    setReduced(media.matches);

    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

/**
 * Whether 3D scenes should hold still.
 *
 * True when the operating system asks for reduced motion, or when the user has
 * asked for it explicitly in the display settings. The in-app toggle can only
 * add stillness, never override a system preference that requests it.
 */
export function useScenePaused(): boolean {
  const systemPreference = useReducedMotion();
  const forced = usePreferences((state) => state.forceReducedMotion);
  return systemPreference || forced;
}
