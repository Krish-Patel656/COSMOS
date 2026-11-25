"use client";

import { Billboard, Text } from "@react-three/drei";

/**
 * In-scene caption that does not use Drei's Html portal.
 *
 * Html mounts a second React root into the DOM from inside the R3F render loop.
 * On React 19 that races with unmount and throws "Attempted to synchronously
 * unmount a root while React was already rendering." Troika text stays in the
 * WebGL tree, so labels never leave the canvas.
 */
export function SceneLabel({
  children,
  position,
  highlighted = false,
  fontSize = 0.28,
}: {
  children: string;
  position: [number, number, number];
  highlighted?: boolean;
  fontSize?: number;
}) {
  return (
    <Billboard position={position} follow>
      <Text
        fontSize={fontSize}
        color={highlighted ? "#04060d" : "#e6edff"}
        outlineWidth={highlighted ? 0.045 : 0.03}
        outlineColor={highlighted ? "#7dd3fc" : "#04060d"}
        anchorX="center"
        anchorY="middle"
        maxWidth={8}
      >
        {children}
      </Text>
    </Billboard>
  );
}
