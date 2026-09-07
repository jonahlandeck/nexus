import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// Minimal config: no R2 incremental cache. nexus is a low-traffic console with
// no ISR pages, and every extra binding is one more thing to provision on the
// free tier. Add `incrementalCache: r2IncrementalCache` here later if needed.
export default defineCloudflareConfig({});
