import type { NextConfig } from "next";

const apiOrigin = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // three.js ships large ES modules; letting Next tree-shake per-import keeps the
  // client bundle from pulling in the entire library for a handful of classes.
  experimental: {
    optimizePackageImports: ["three", "@react-three/drei"],
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },

  async rewrites() {
    // Proxying the API through the Next origin keeps the browser on one origin,
    // which sidesteps CORS preflights entirely in development and lets the
    // deployed frontend talk to a backend on a different host without exposing
    // that host to the client.
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
