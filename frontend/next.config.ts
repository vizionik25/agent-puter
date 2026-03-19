import type { NextConfig } from "next";

/**
 * Backend API base URL.
 * In development this defaults to the local swarm server on port 9999.
 * Override via NEXT_PUBLIC_API_URL in .env.local for staging/production.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        /**
         * Proxy all /api/* requests from the Next.js dev server to the Python backend.
         * This avoids CORS issues in development — the browser only ever sees
         * the same-origin Next.js server, which forwards requests internally.
         */
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
