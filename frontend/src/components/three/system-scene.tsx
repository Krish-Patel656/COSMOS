"use client";

import { OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { type Group, Vector3 } from "three";

import { PlanetMesh } from "./planet-mesh";
import { SceneLabel } from "./scene-label";
import { Starfield } from "./starfield";
import { StarMesh } from "./star-mesh";
import { HabitableZoneBands, OrbitPath } from "./orbits";
import {
  SCENE_INNER_RADIUS,
  createOrbitScale,
  orbitPosition,
  orbitSpeed,
  planetDisplayRadius,
  starDisplayRadius,
} from "@/lib/scene";
import { QUALITY_SEGMENTS, type RenderQuality } from "@/lib/store/preferences";
import type { PlanetSummary, SystemDetail } from "@/lib/types";

/** Stable per-planet starting phase, so a system does not render as a line-up. */
function phaseFromSlug(slug: string): number {
  let hash = 5381;
  for (let i = 0; i < slug.length; i += 1) {
    hash = (hash * 33) ^ slug.charCodeAt(i);
  }
  return ((hash >>> 0) % 1000) / 1000;
}

interface SceneProps {
  system: SystemDetail;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
  showHabitableZone: boolean;
  showOrbits: boolean;
  /** True under reduced-motion: orbital and rotational motion both stop. */
  paused: boolean;
  quality: RenderQuality;
}

export function SystemScene({
  system,
  selectedSlug,
  onSelect,
  showHabitableZone,
  showOrbits,
  paused,
  quality,
}: SceneProps) {
  const segments = QUALITY_SEGMENTS[quality];
  const starRadius = starDisplayRadius(system.radius_solar);
  const starColor = system.color_hex ?? "#fff4ea";

  const scale = useMemo(
    () => createOrbitScale(system.planets.map((planet) => planet.semi_major_axis_au)),
    [system.planets],
  );

  const zone = system.habitable_zone;
  const zoneRadii = useMemo(() => {
    if (!zone) return null;
    return {
      conservativeInner: scale.toScene(zone.runaway_greenhouse_au),
      conservativeOuter: scale.toScene(zone.maximum_greenhouse_au),
      optimisticInner: scale.toScene(zone.recent_venus_au),
      optimisticOuter: scale.toScene(zone.early_mars_au),
    };
  }, [zone, scale]);

  const starPosition = useMemo(() => new Vector3(0, 0, 0), []);

  return (
    <>
      <color attach="background" args={["#04060d"]} />
      <Starfield count={quality === "low" ? 900 : 2200} drift={!paused} />
      <ambientLight intensity={0.12} />

      <StarMesh
        radius={starRadius}
        colorHex={starColor}
        segments={segments}
        animate={!paused}
        lightIntensity={70}
      />

      {zoneRadii ? (
        <HabitableZoneBands {...zoneRadii} visible={showHabitableZone} />
      ) : null}

      {system.planets.map((planet, index) => {
        const sceneRadius = planet.semi_major_axis_au
          ? scale.toScene(planet.semi_major_axis_au)
          : SCENE_INNER_RADIUS + index * 1.6;

        return (
          <OrbitingPlanet
            key={planet.slug}
            planet={planet}
            sceneRadius={sceneRadius}
            selected={selectedSlug === planet.slug}
            onSelect={onSelect}
            showOrbit={showOrbits}
            paused={paused}
            segments={segments}
            starPosition={starPosition}
            starColor={starColor}
          />
        );
      })}

      <OrbitControls
        enablePan={false}
        enableDamping
        dampingFactor={0.06}
        minDistance={starRadius * 2.5}
        maxDistance={70}
        minPolarAngle={0.15}
        maxPolarAngle={Math.PI - 0.15}
        autoRotate={!paused && selectedSlug === null}
        autoRotateSpeed={0.22}
        makeDefault
      />

      {quality !== "low" ? (
        <EffectComposer enableNormalPass={false}>
          <Bloom
            intensity={0.85}
            luminanceThreshold={0.55}
            luminanceSmoothing={0.3}
            mipmapBlur
          />
          <Vignette offset={0.26} darkness={0.62} eskil={false} />
        </EffectComposer>
      ) : null}
    </>
  );
}

function OrbitingPlanet({
  planet,
  sceneRadius,
  selected,
  onSelect,
  showOrbit,
  paused,
  segments,
  starPosition,
  starColor,
}: {
  planet: PlanetSummary;
  sceneRadius: number;
  selected: boolean;
  onSelect: (slug: string) => void;
  showOrbit: boolean;
  paused: boolean;
  segments: number;
  starPosition: Vector3;
  starColor: string;
}) {
  const groupRef = useRef<Group>(null);
  const phaseRef = useRef(phaseFromSlug(planet.slug));

  const eccentricity = planet.eccentricity ?? 0;
  const speed = orbitSpeed(planet.orbital_period_days);
  const displayRadius = planetDisplayRadius(planet.radius_earth);

  // Set the initial position synchronously so the planet never renders at the
  // origin for one frame before the first useFrame tick.
  const initial = useMemo(
    () => orbitPosition(sceneRadius, eccentricity, phaseRef.current),
    [sceneRadius, eccentricity],
  );

  useFrame((_, delta) => {
    const group = groupRef.current;
    if (!group) return;
    if (!paused && speed > 0) {
      phaseRef.current = (phaseRef.current + speed * delta) % 1;
    }
    const position = orbitPosition(sceneRadius, eccentricity, phaseRef.current);
    group.position.set(position.x, 0, position.z);
  });

  return (
    <>
      {showOrbit ? (
        <OrbitPath
          semiMajorAxis={sceneRadius}
          eccentricity={eccentricity}
          highlighted={selected}
        />
      ) : null}

      <group ref={groupRef} position={[initial.x, 0, initial.z]}>
        <mesh
          onClick={(event) => {
            event.stopPropagation();
            onSelect(planet.slug);
          }}
          onPointerOver={(event) => {
            event.stopPropagation();
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
          // An invisible sphere a little larger than the planet, so that an
          // Earth-sized world is still a comfortable click target.
          visible={false}
        >
          <sphereGeometry args={[Math.max(displayRadius * 1.6, 0.38), 12, 8]} />
        </mesh>

        <PlanetMesh
          slug={planet.slug}
          radius={displayRadius}
          appearance={planet.appearance}
          lightPosition={starPosition}
          lightColor={starColor}
          segments={segments}
          spin={paused ? 0 : 0.05}
        />

        {selected ? <SelectionRing radius={displayRadius} paused={paused} /> : null}

        <SceneLabel
          highlighted={selected}
          position={[0, displayRadius + 0.42, 0]}
        >
          {planet.letter ?? planet.name}
        </SceneLabel>
      </group>
    </>
  );
}

function SelectionRing({ radius, paused }: { radius: number; paused: boolean }) {
  const ringRef = useRef<Group>(null);

  useFrame((state) => {
    const ring = ringRef.current;
    if (!ring) return;
    // Always face the camera, so the selection indicator reads as a halo rather
    // than as a disc seen edge-on.
    ring.quaternion.copy(state.camera.quaternion);
    if (!paused) {
      ring.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 2.2) * 0.04);
    }
  });

  return (
    <group ref={ringRef}>
      <mesh>
        <ringGeometry args={[radius * 1.55, radius * 1.72, 64]} />
        <meshBasicMaterial color="#7dd3fc" transparent opacity={0.85} depthWrite={false} />
      </mesh>
    </group>
  );
}
