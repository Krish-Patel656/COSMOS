import { CanvasTexture } from "three";

/**
 * Soft circular halo used by the stellar map.
 *
 * A plain camera-facing quad reads as a square once hundreds of them overlap.
 * This texture fades to transparent at the edges so additive blending stays round.
 */
let texture: CanvasTexture | null = null;

export function starGlowTexture(): CanvasTexture {
  if (texture) return texture;

  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  if (!context) {
    texture = new CanvasTexture(canvas);
    return texture;
  }

  const centre = size / 2;
  const gradient = context.createRadialGradient(centre, centre, 0, centre, centre, centre);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.18, "rgba(255,255,255,0.55)");
  gradient.addColorStop(0.45, "rgba(255,255,255,0.12)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);

  texture = new CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}
