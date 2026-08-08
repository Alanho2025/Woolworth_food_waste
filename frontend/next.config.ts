import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const frontendDirectory = dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  outputFileTracingRoot: resolve(frontendDirectory, ".."),
  reactStrictMode: true,
  typescript: {
    // Never silently ship a type error. `npm run typecheck` is the gate, and
    // the build must fail on the same condition (clean_code_spec 8.5).
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
