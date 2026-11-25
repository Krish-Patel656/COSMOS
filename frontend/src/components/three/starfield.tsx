"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { AdditiveBlending, BufferAttribute, type Points } from "three";

/**
 * Background star field.
 *
 * Decorative rather than astrometric: these are not catalogued stars, and the
 * scenes that *do* plot real positions (the stellar map) use measured
 * coordinates instead. Positions are generated once from a fixed sequence so the
 * backdrop does not shimmer between renders.
 *
 * Colours are sampled along the Planckian locus so the field has the faint
 * blue/white/orange variety a real sky has, rather than reading as grey dust.
 */
const PALETTE: [number, number, number][] = [
  [0.61, 0.69, 1.0], // hot blue
  [0.79, 0.84, 1.0],
  [1.0, 1.0, 1.0],
  [1.0, 0.96, 0.92],
  [1.0, 0.82, 0.63], // cool orange
];

/** Deterministic pseudo-random sequence, so the backdrop is stable. */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function Starfield({
  count = 2400,
  radius = 320,
  drift = true,
  size = 1.1,
}: {
  count?: number;
  radius?: number;
  drift?: boolean;
  size?: number;
}) {
  const pointsRef = useRef<Points>(null);

  const { positions, colors } = useMemo(() => {
    const random = mulberry32(0x5eed);
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i += 1) {
      // Uniform on a spherical shell: acos of a uniform variate, otherwise the
      // points bunch at the poles.
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      const r = radius * (0.75 + random() * 0.25);

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi);
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      const tint = PALETTE[Math.floor(random() * PALETTE.length)] ?? PALETTE[2]!;
      // Most stars are faint; a few are bright. Cubing a uniform variate gives
      // that distribution cheaply.
      const brightness = 0.35 + Math.pow(random(), 3) * 0.65;
      colors[i * 3] = tint[0] * brightness;
      colors[i * 3 + 1] = tint[1] * brightness;
      colors[i * 3 + 2] = tint[2] * brightness;
    }

    return { positions, colors };
  }, [count, radius]);

  useFrame((_, delta) => {
    // An extremely slow rotation keeps the backdrop from feeling like a painted
    // wall without ever being fast enough to notice directly.
    if (drift && pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.004;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <primitive
          attach="attributes-position"
          object={new BufferAttribute(positions, 3)}
        />
        <primitive attach="attributes-color" object={new BufferAttribute(colors, 3)} />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        sizeAttenuation={false}
        vertexColors
        transparent
        opacity={0.85}
        depthWrite={false}
        blending={AdditiveBlending}
      />
    </points>
  );
}
