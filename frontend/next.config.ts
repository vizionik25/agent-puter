import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Standalone output mode — produces .next/standalone/server.js which bundles
   * only the files needed to run the server. Required by Dockerfile.frontend.
   * See: https://nextjs.org/docs/app/api-reference/next-config-js/output
   */
  output: "standalone",
};

export default nextConfig;
