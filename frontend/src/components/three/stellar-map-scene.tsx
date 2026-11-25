"use client";

import { Line, OrbitControls } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import { AdditiveBlending, type Sprite } from "three";

import { SceneLabel } from "./scene-label";
import { starGlowTexture } from "./star-glow";
import { Starfield } from "./starfield";
import { mapPointSize, mapPosition, mapScale } from "@/lib/scene";
import { bandStyle, bandForScore } from "@/lib/scores";
import type { RenderQuality } from "@/lib/store/preferences";
import type { StarMapPoint } from "@/lib/types";

/** Distance shells, in light years, drawn as reference rings. */
const DISTANCE_SHELLS_LY = [10, 25, 50, 100];
const LY_PER_PC = 3.26156;

interface MapSceneProps {
  stars: StarMapPoint[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
  /** Colour stars by their best planet's habitability instead of by temperature. */
  colorByHabitability: boolean;
  showShells: boolean;
  paused: boolean;
  quality: RenderQuality;
}

/**
 * Interactive map of nearby stars.
 *
 * Positions are real: the backend precomputes equatorial cartesian coordinates
 * from right ascension, declination and distance, and only the radial scale is
 * compressed here (square root), so directions on the sky are preserved exactly
 * while nearby systems stay separated enough to click.
 */
export function StellarMapScene({
  stars,
  selectedSlug,
  onSelect,
  colorByHabitability,
  showShells,
  paused,
  quality,
}: MapSceneProps) {
  const placed = useMemo(
    () =>
      stars
        .map((star) => ({ star, position: mapPosition(star.x_pc, star.y_pc, star.z_pc) }))
        .filter(
          (entry): entry is { star: StarMapPoint; position: NonNullable<typeof entry.position> } =>
            entry.position !== null,
        ),
    [stars],
  );

  return (
    <>
      <color attach="background" args={["#04060d"]} />
      <Starfield count={quality === "low" ? 1200 : 3000} radius={600} drift={!paused} size={0.9} />
      <ambientLight intensity={0.5} />

      {showShells
        ? DISTANCE_SHELLS_LY.map((lightYears) => (
            <DistanceShell key={lightYears} lightYears={lightYears} />
          ))
        : null}

      {placed.map(({ star, position }) => (
        <MapStar
          key={star.slug}
          star={star}
          x={position.x}
          y={position.y}
          z={position.z}
          selected={selectedSlug === star.slug}
          onSelect={onSelect}
          colorByHabitability={colorByHabitability}
          paused={paused}
        />
      ))}

      <OrbitControls
        enablePan
        enableDamping
        dampingFactor={0.08}
        minDistance={3}
        maxDistance={260}
        autoRotate={!paused && selectedSlug === null}
        autoRotateSpeed={0.12}
        makeDefault
      />
    </>
  );
}

function DistanceShell({ lightYears }: { lightYears: number }) {
  const radius = mapScale(lightYears / LY_PER_PC);

  const points = useMemo(() => {
    const result: [number, number, number][] = [];
    for (let i = 0; i <= 96; i += 1) {
      const angle = (i / 96) * Math.PI * 2;
      result.push([Math.cos(angle) * radius, 0, Math.sin(angle) * radius]);
    }
    return result;
  }, [radius]);

  return (
    <group>
      <Line points={points} color="#273355" lineWidth={1} transparent opacity={0.55} />
      <SceneLabel position={[radius, 0, 0]} fontSize={0.7}>
        {`${lightYears} ly`}
      </SceneLabel>
    </group>
  );
}

function MapStar({
  star,
  x,
  y,
  z,
  selected,
  onSelect,
  colorByHabitability,
  paused,
}: {
  star: StarMapPoint;
  x: number;
  y: number;
  z: number;
  selected: boolean;
  onSelect: (slug: string) => void;
  colorByHabitability: boolean;
  paused: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const glowRef = useRef<Sprite>(null);
  const glowMap = useMemo(() => starGlowTexture(), []);

  const size = mapPointSize(star.radius_solar, star.planet_count, star.is_solar_system);
  const color = colorByHabitability
    ? bandStyle(bandForScore(star.best_habitability_score)).hex
    : (star.color_hex ?? "#cad7ff");
  const glowSize = size * (selected || hovered ? 6.2 : 4.4);

  useFrame((state) => {
    const glow = glowRef.current;
    if (!glow) return;
    const pulse = selected && !paused ? 1 + Math.sin(state.clock.elapsedTime * 2.4) * 0.08 : 1;
    glow.scale.set(glowSize * pulse, glowSize * pulse, 1);
  });

  const showLabel = selected || hovered || star.is_solar_system;

  return (
    <group position={[x, y, z]}>
      <mesh
        onClick={(event) => {
          event.stopPropagation();
          onSelect(star.slug);
        }}
        onPointerOver={(event) => {
          event.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[size, 16, 12]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>

      <sprite ref={glowRef} scale={[glowSize, glowSize, 1]}>
        <spriteMaterial
          map={glowMap}
          color={color}
          transparent
          opacity={selected ? 0.85 : hovered ? 0.55 : 0.28}
          blending={AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </sprite>

      {showLabel ? (
        <SceneLabel highlighted={selected} position={[0, size * 3.2, 0]} fontSize={0.55}>
          {star.name}
        </SceneLabel>
      ) : null}
    </group>
  );
}
