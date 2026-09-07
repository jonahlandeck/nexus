import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // @nexus/auth ships as TypeScript source.
  transpilePackages: ["@nexus/auth"],
};

// Makes `getCloudflareContext()` work in `next dev` (bindings from wrangler.jsonc
// via a local miniflare). No-op in production builds.
initOpenNextCloudflareForDev();

export default nextConfig;
