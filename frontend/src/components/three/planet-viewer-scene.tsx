"use client";

import { OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useMemo } from "react";
import { Vector3 } from "three";

import { PlanetMesh } from "./planet-mesh";
import { Starfield } from "./starfield";
import { QUALITY_SEGMENTS, type RenderQuality } from "@/lib/store/preferences";
import type { Appearance } from "@/lib/types";

/**
 * Close-up of a single world.
 *
 * The illuminating star is placed off to one side rather than behind the camera
 * so that a terminator is visible: a fully lit sphere reads as a flat disc, and
 * the day/night boundary is what gives the globe its shape.
 */
export function PlanetViewerScene({
  slug,
  appearance,
  starColor = "#fff4ea",
  paused,
  quality,
  showAtmosphere = true,
}: {
  slug: string;
  appearance: Appearance | null;
  starColor?: string;
  paused: boolean;
  quality: RenderQuality;
  showAtmosphere?: boolean;
}) {
  const segments = QUALITY_SEGMENTS[quality];
  const lightPosition = useMemo(() => new Vector3(14, 5, 7), []);

  return (
    <>
      <Starfield count={quality === "low" ? 700 : 1800} radius={90} drift={!paused} />
      <ambientLight intensity={0.1} />
      <pointLight position={[14, 5, 7]} intensity={90} color={starColor} decay={1.2} />

      <PlanetMesh
        slug={slug}
        radius={1.5}
        appearance={appearance}
        lightPosition={lightPosition}
        lightColor={starColor}
        segments={segments}
        spin={paused ? 0 : 0.055}
        tilt={0.32}
        atmosphereScale={1.25}
        showAtmosphere={showAtmosphere}
      />

      <OrbitControls
        enablePan={false}
        enableDamping
        dampingFactor={0.07}
        minDistance={2.4}
        maxDistance={9}
        autoRotate={!paused}
        autoRotateSpeed={0.35}
        makeDefault
      />

      {quality !== "low" ? (
        <EffectComposer enableNormalPass={false}>
          <Bloom intensity={0.5} luminanceThreshold={0.65} luminanceSmoothing={0.3} mipmapBlur />
        </EffectComposer>
      ) : null}
    </>
  );
}
