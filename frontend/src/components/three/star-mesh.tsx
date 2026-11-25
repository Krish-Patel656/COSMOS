"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { AdditiveBlending, Color, type Mesh, type PointLight } from "three";

import { CORONA_FRAGMENT, CORONA_VERTEX, STAR_FRAGMENT, STAR_VERTEX } from "./shaders";

function hotterShade(hex: string): Color {
  // The granulation highlight is the same hue pushed towards white, which is
  // what rising convection cells actually look like: hotter, hence bluer.
  const color = new Color(hex);
  return color.lerp(new Color("#ffffff"), 0.45);
}

export interface StarMeshProps {
  radius: number;
  colorHex?: string | null;
  /** Scales the emissive output, which bloom then picks up. */
  intensity?: number;
  /** Illumination reaching the planets. */
  lightIntensity?: number;
  segments?: number;
  animate?: boolean;
  showCorona?: boolean;
  seed?: number;
}

/**
 * A star: animated photosphere, a billboarded corona, and the point light that
 * illuminates the system's planets.
 *
 * The glow comes from bloom in post-processing rather than a large transparent
 * sphere, so the disc stays sharp when the camera moves in close.
 */
export function StarMesh({
  radius,
  colorHex,
  intensity = 1.6,
  lightIntensity = 60,
  segments = 64,
  animate = true,
  showCorona = true,
  seed = 7.3,
}: StarMeshProps) {
  const surfaceRef = useRef<Mesh>(null);
  const coronaRef = useRef<Mesh>(null);
  const lightRef = useRef<PointLight>(null);
  const hex = colorHex ?? "#fff4ea";

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor: { value: new Color(hex) },
      uHotColor: { value: hotterShade(hex) },
      uIntensity: { value: intensity },
      uSeed: { value: seed },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const coronaUniforms = useMemo(
    () => ({
      uColor: { value: new Color(hex) },
      uOpacity: { value: 0.42 },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useEffect(() => {
    uniforms.uColor.value.set(hex);
    uniforms.uHotColor.value.copy(hotterShade(hex));
    uniforms.uIntensity.value = intensity;
    coronaUniforms.uColor.value.set(hex);
  }, [hex, intensity, uniforms, coronaUniforms]);

  useFrame((state, delta) => {
    if (animate) {
      uniforms.uTime.value = state.clock.elapsedTime;
      if (surfaceRef.current) surfaceRef.current.rotation.y += delta * 0.015;
    }
    // The corona plane always faces the camera; a fixed quad would reveal itself
    // as flat the moment the camera orbits.
    if (coronaRef.current) coronaRef.current.quaternion.copy(state.camera.quaternion);
  });

  return (
    <group>
      <mesh ref={surfaceRef}>
        <sphereGeometry args={[radius, segments, Math.max(16, segments / 2)]} />
        <shaderMaterial
          vertexShader={STAR_VERTEX}
          fragmentShader={STAR_FRAGMENT}
          uniforms={uniforms}
        />
      </mesh>

      {showCorona ? (
        <mesh ref={coronaRef}>
          <planeGeometry args={[radius * 7, radius * 7]} />
          <shaderMaterial
            vertexShader={CORONA_VERTEX}
            fragmentShader={CORONA_FRAGMENT}
            uniforms={coronaUniforms}
            transparent
            depthWrite={false}
            blending={AdditiveBlending}
          />
        </mesh>
      ) : null}

      <pointLight
        ref={lightRef}
        color={hex}
        intensity={lightIntensity}
        distance={0}
        decay={1.4}
      />
    </group>
  );
}
