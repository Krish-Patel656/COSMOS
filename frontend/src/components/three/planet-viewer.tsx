"use client";

import { CanvasShell } from "@/components/three/canvas-shell";
import { PlanetViewerScene } from "@/components/three/planet-viewer-scene";
import { ArtisticNotice } from "@/components/ui/primitives";
import { humanise } from "@/lib/format";
import { useScenePaused } from "@/lib/hooks/use-reduced-motion";
import { usePreferences } from "@/lib/store/preferences";
import type { Appearance } from "@/lib/types";

export function PlanetViewer({
  slug,
  appearance,
  starColor,
}: {
  slug: string;
  appearance: Appearance | null;
  starColor?: string;
}) {
  const paused = useScenePaused();
  const quality = usePreferences((state) => state.renderQuality);

  return (
    <div>
      <CanvasShell
        className="h-[min(52vh,28rem)] overflow-hidden rounded-panel border border-void-700 bg-void-950"
        label={`Close-up artistic rendering of this world. Drag to rotate.`}
        camera={{ position: [0, 0.35, 4.6], fov: 42, near: 0.1, far: 80 }}
        fallback={
          <div
            className="flex h-[min(52vh,28rem)] items-center justify-center rounded-panel border border-void-700"
            style={{
              background: `radial-gradient(circle at 40% 40%, ${appearance?.accent_color ?? "#8d99ad"}, ${appearance?.base_color ?? "#1a2440"} 55%, #04060d)`,
            }}
          >
            <p className="rounded bg-void-950/70 px-3 py-1 text-sm text-starlight-200">
              {humanise(appearance?.surface_type)} world
            </p>
          </div>
        }
      >
        <PlanetViewerScene
          slug={slug}
          appearance={appearance}
          starColor={starColor}
          paused={paused}
          quality={quality}
        />
      </CanvasShell>
      <ArtisticNotice className="mt-3" basis={appearance?.basis} />
    </div>
  );
}
