"use client";

import { useMemo } from "react";
import { OrbitControls } from "@react-three/drei";

import { CanvasShell } from "@/components/three/canvas-shell";
import { PlanetMesh } from "@/components/three/planet-mesh";
import { Starfield } from "@/components/three/starfield";
import { StarMesh } from "@/components/three/star-mesh";
import { useScenePaused } from "@/lib/hooks/use-reduced-motion";
import { orbitPosition } from "@/lib/scene";
import { QUALITY_SEGMENTS, usePreferences } from "@/lib/store/preferences";

const HERO_WORLDS = [
  { slug: "hero-earth", color: "#2e7d5b", accent: "#8fbf7f", atmosphere: "#7ec8f5", radius: 0.42, au: 6.2, banded: false, clouds: 0.55 },
  { slug: "hero-ice", color: "#cfe4f0", accent: "#ffffff", atmosphere: "#d8ecf8", radius: 0.34, au: 9.4, banded: false, clouds: 0.3 },
  { slug: "hero-giant", color: "#c9a06a", accent: "#f0dcc0", atmosphere: "#e8d3b0", radius: 0.95, au: 13.6, banded: true, clouds: 0.95 },
];

export function HeroScene() {
  const paused = useScenePaused();
  const quality = usePreferences((state) => state.renderQuality);
  const segments = QUALITY_SEGMENTS[quality];

  return (
    <CanvasShell
      className="pointer-events-none absolute inset-0"
      label="Decorative 3D visualisation of a planetary system behind the COSMOS introduction."
      camera={{ position: [0, 6.5, 16], fov: 48, near: 0.1, far: 400 }}
      fallback={<div className="absolute inset-0 bg-void-950" />}
      loading={<div className="absolute inset-0 bg-void-950" />}
    >
      <color attach="background" args={["#04060d"]} />
      <Starfield count={quality === "low" ? 800 : 2000} drift={!paused} />
      <ambientLight intensity={0.1} />
      <StarMesh radius={1.35} colorHex="#fff4ea" segments={segments} animate={!paused} lightIntensity={55} />
      {HERO_WORLDS.map((world, index) => (
        <HeroPlanet key={world.slug} world={world} index={index} paused={paused} segments={segments} />
      ))}
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate={!paused}
        autoRotateSpeed={0.18}
        enableDamping
        dampingFactor={0.08}
      />
    </CanvasShell>
  );
}

function HeroPlanet({
  world,
  index,
  paused,
  segments,
}: {
  world: (typeof HERO_WORLDS)[number];
  index: number;
  paused: boolean;
  segments: number;
}) {
  const start = useMemo(() => orbitPosition(world.au, 0.04 * index, 0.12 + index * 0.22), [world, index]);

  return (
    <group position={[start.x, 0, start.z]}>
      <PlanetMesh
        slug={world.slug}
        radius={world.radius}
        appearance={{
          surface_type: world.banded ? "gas_giant" : "terrestrial",
          base_color: world.color,
          accent_color: world.accent,
          atmosphere_color: world.atmosphere,
          atmosphere_opacity: 0.45,
          cloud_coverage: world.clouds,
          roughness: 0.7,
          metalness: 0.05,
          emissive_intensity: 0,
          has_rings: world.banded,
          banded: world.banded,
          basis: [],
          is_artistic: true,
        }}
        segments={Math.max(32, segments / 2)}
        spin={paused ? 0 : 0.08}
      />
    </group>
  );
}
