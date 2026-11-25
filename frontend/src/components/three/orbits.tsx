"use client";

import { Line } from "@react-three/drei";
import { useMemo } from "react";
import { DoubleSide } from "three";

import { sampleOrbit } from "@/lib/scene";

export function OrbitPath({
  semiMajorAxis,
  eccentricity,
  color = "#3b4a73",
  highlighted = false,
  segments = 128,
}: {
  semiMajorAxis: number;
  eccentricity: number;
  color?: string;
  highlighted?: boolean;
  segments?: number;
}) {
  const points = useMemo(
    () => sampleOrbit(semiMajorAxis, eccentricity, segments),
    [semiMajorAxis, eccentricity, segments],
  );

  return (
    <Line
      points={points}
      color={highlighted ? "#7dd3fc" : color}
      lineWidth={highlighted ? 1.8 : 1}
      transparent
      opacity={highlighted ? 0.9 : 0.4}
      depthWrite={false}
    />
  );
}

/**
 * Habitable-zone annuli.
 *
 * Two nested bands: the conservative zone (runaway greenhouse to maximum
 * greenhouse) and the optimistic one (recent Venus to early Mars), following
 * Kopparapu et al. (2013). Drawing both makes visible how much of the "is this
 * planet in the habitable zone?" question is a matter of which limit you accept,
 * which a single band would hide.
 *
 * Radii arrive already converted to scene units, because the AU-to-scene mapping
 * is logarithmic and system-specific.
 */
export function HabitableZoneBands({
  conservativeInner,
  conservativeOuter,
  optimisticInner,
  optimisticOuter,
  visible = true,
}: {
  conservativeInner: number;
  conservativeOuter: number;
  optimisticInner: number;
  optimisticOuter: number;
  visible?: boolean;
}) {
  if (!visible) return null;

  return (
    <group>
      {/* Drawn marginally below the orbital plane so the orbit lines stay on top
          instead of z-fighting with the translucent fill. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <ringGeometry args={[optimisticInner, optimisticOuter, 128]} />
        <meshBasicMaterial
          color="#34d399"
          transparent
          opacity={0.055}
          side={DoubleSide}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <ringGeometry args={[conservativeInner, conservativeOuter, 128]} />
        <meshBasicMaterial
          color="#34d399"
          transparent
          opacity={0.12}
          side={DoubleSide}
          depthWrite={false}
        />
      </mesh>

      <ZoneEdge radius={conservativeInner} opacity={0.5} />
      <ZoneEdge radius={conservativeOuter} opacity={0.5} />
      <ZoneEdge radius={optimisticInner} opacity={0.25} />
      <ZoneEdge radius={optimisticOuter} opacity={0.25} />
    </group>
  );
}

function ZoneEdge({ radius, opacity }: { radius: number; opacity: number }) {
  const points = useMemo(() => {
    const result: [number, number, number][] = [];
    for (let i = 0; i <= 128; i += 1) {
      const angle = (i / 128) * Math.PI * 2;
      result.push([Math.cos(angle) * radius, 0, Math.sin(angle) * radius]);
    }
    return result;
  }, [radius]);

  return (
    <Line
      points={points}
      color="#6ee7b7"
      lineWidth={1}
      transparent
      opacity={opacity}
      depthWrite={false}
    />
  );
}
