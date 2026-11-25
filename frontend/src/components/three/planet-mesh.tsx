"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  AdditiveBlending,
  BackSide,
  Color,
  DoubleSide,
  type Group,
  type Mesh,
  type ShaderMaterial,
  Vector3,
} from "three";

import {
  ATMOSPHERE_FRAGMENT,
  ATMOSPHERE_VERTEX,
  PLANET_FRAGMENT,
  PLANET_VERTEX,
} from "./shaders";
import type { Appearance } from "@/lib/types";

const DEFAULT_APPEARANCE: Appearance = {
  surface_type: "unknown",
  base_color: "#6f7a90",
  accent_color: "#8d99ad",
  atmosphere_color: "#8ab4f8",
  atmosphere_opacity: 0.18,
  cloud_coverage: 0.2,
  roughness: 0.8,
  metalness: 0.05,
  emissive_intensity: 0,
  has_rings: false,
  banded: false,
  basis: [],
  is_artistic: true,
};

/**
 * Deterministic per-planet noise offset.
 *
 * Derived from the slug so that a given world looks identical on every visit and
 * on every machine. A random seed would make the same planet unrecognisable
 * between page loads, which would undercut the whole point of giving it a face.
 */
function seedFromSlug(slug: string): number {
  let hash = 2166136261;
  for (let i = 0; i < slug.length; i += 1) {
    hash ^= slug.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return ((hash >>> 0) % 10000) / 100;
}

export interface PlanetMeshProps {
  slug: string;
  radius: number;
  appearance?: Appearance | null;
  /** World position of the illuminating star. */
  lightPosition?: Vector3;
  lightColor?: string;
  segments?: number;
  /** Rotations per second. Zero holds the planet still. */
  spin?: number;
  /** Axial tilt in radians, purely illustrative. */
  tilt?: number;
  /** Multiplies the atmosphere thickness; raised slightly for close-up views. */
  atmosphereScale?: number;
  showAtmosphere?: boolean;
}

/**
 * A procedurally textured planet.
 *
 * The appearance is an illustration derived from measured bulk properties, never
 * an observation. See `shaders.ts` and the `ArtisticNotice` that accompanies
 * every scene using this component.
 */
export function PlanetMesh({
  slug,
  radius,
  appearance,
  lightPosition,
  lightColor = "#fff4ea",
  segments = 64,
  spin = 0.04,
  tilt = 0.4,
  atmosphereScale = 1,
  showAtmosphere = true,
}: PlanetMeshProps) {
  const look = appearance ?? DEFAULT_APPEARANCE;
  const groupRef = useRef<Group>(null);
  const surfaceRef = useRef<Mesh>(null);
  const surfaceMaterialRef = useRef<ShaderMaterial>(null);
  const atmosphereMaterialRef = useRef<ShaderMaterial>(null);

  const worldPosition = useMemo(() => new Vector3(), []);
  const lightDirection = useMemo(() => new Vector3(), []);
  const starPosition = useMemo(() => lightPosition ?? new Vector3(0, 0, 0), [lightPosition]);

  const surfaceUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uBaseColor: { value: new Color(look.base_color) },
      uAccentColor: { value: new Color(look.accent_color) },
      uLightDirection: { value: new Vector3(1, 0, 0) },
      uLightColor: { value: new Color(lightColor) },
      uCloudCoverage: { value: look.cloud_coverage },
      uBanded: { value: look.banded ? 1 : 0 },
      uRoughness: { value: look.roughness },
      uEmissive: { value: look.emissive_intensity },
      uNoiseScale: { value: look.banded ? 2.1 : 2.8 },
      uSeed: { value: seedFromSlug(slug) },
      uAmbient: { value: 0.08 },
      uOctaves: { value: 5 },
    }),
    // Built once; values are synced below so that changing the appearance (in the
    // simulator, for instance) does not rebuild the material and restart its
    // animation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const atmosphereUniforms = useMemo(
    () => ({
      uColor: { value: new Color(look.atmosphere_color) },
      uLightDirection: { value: new Vector3(1, 0, 0) },
      uOpacity: { value: look.atmosphere_opacity },
      uPower: { value: 2.4 },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useEffect(() => {
    surfaceUniforms.uBaseColor.value.set(look.base_color);
    surfaceUniforms.uAccentColor.value.set(look.accent_color);
    surfaceUniforms.uCloudCoverage.value = look.cloud_coverage;
    surfaceUniforms.uBanded.value = look.banded ? 1 : 0;
    surfaceUniforms.uRoughness.value = look.roughness;
    surfaceUniforms.uEmissive.value = look.emissive_intensity;
    surfaceUniforms.uNoiseScale.value = look.banded ? 2.1 : 2.8;
    surfaceUniforms.uSeed.value = seedFromSlug(slug);
    surfaceUniforms.uLightColor.value.set(lightColor);
    atmosphereUniforms.uColor.value.set(look.atmosphere_color);
    atmosphereUniforms.uOpacity.value = look.atmosphere_opacity;
  }, [look, slug, lightColor, surfaceUniforms, atmosphereUniforms]);

  useFrame((state, delta) => {
    const surface = surfaceRef.current;
    if (!surface) return;

    if (spin !== 0) {
      surface.rotation.y += spin * delta;
    }

    surfaceUniforms.uTime.value = state.clock.elapsedTime;

    // Recomputed every frame because the planet moves along its orbit, so the
    // direction to its star changes continuously.
    surface.getWorldPosition(worldPosition);
    lightDirection.copy(starPosition).sub(worldPosition);
    if (lightDirection.lengthSq() === 0) {
      lightDirection.set(1, 0, 0);
    }
    lightDirection.normalize();

    surfaceUniforms.uLightDirection.value.copy(lightDirection);
    atmosphereUniforms.uLightDirection.value.copy(lightDirection);
  });

  const atmosphereRadius = radius * (1 + 0.075 * atmosphereScale);
  const hasAtmosphere = showAtmosphere && look.atmosphere_opacity > 0.02;

  return (
    <group ref={groupRef} rotation={[0, 0, tilt]}>
      <mesh ref={surfaceRef}>
        <sphereGeometry args={[radius, segments, Math.max(16, segments / 2)]} />
        <shaderMaterial
          ref={surfaceMaterialRef}
          vertexShader={PLANET_VERTEX}
          fragmentShader={PLANET_FRAGMENT}
          uniforms={surfaceUniforms}
        />
      </mesh>

      {hasAtmosphere ? (
        <mesh>
          <sphereGeometry args={[atmosphereRadius, Math.max(32, segments / 2), 24]} />
          <shaderMaterial
            ref={atmosphereMaterialRef}
            vertexShader={ATMOSPHERE_VERTEX}
            fragmentShader={ATMOSPHERE_FRAGMENT}
            uniforms={atmosphereUniforms}
            transparent
            depthWrite={false}
            blending={AdditiveBlending}
            side={BackSide}
          />
        </mesh>
      ) : null}

      {look.has_rings ? (
        <mesh rotation={[Math.PI / 2 - 0.12, 0, 0]}>
          <ringGeometry args={[radius * 1.45, radius * 2.3, 96]} />
          <meshBasicMaterial
            color={look.accent_color}
            transparent
            opacity={0.28}
            side={DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ) : null}
    </group>
  );
}
