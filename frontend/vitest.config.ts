import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // The 3D scenes need a real WebGL context, which jsdom cannot provide. They
    // are excluded here and covered by the pure functions they delegate their
    // maths to (scene scaling, orbit sampling, colour derivation), which is where
    // the logic that can actually be wrong lives.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
