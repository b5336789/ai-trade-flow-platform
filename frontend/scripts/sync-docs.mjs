// Copy the curated repo docs into frontend/content/docs so the website can render
// them. The Docker frontend build context is frontend/ only, so the synced copies
// are committed; this script just refreshes them from the repo-root docs/.
// Guarded: if ../docs is absent (e.g. inside the Docker build context), it no-ops
// and leaves the committed copies in place.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(here, "..");
const repoDocs = join(frontendRoot, "..", "docs");
const outDir = join(frontendRoot, "content", "docs");

// Keep in sync with lib/docs-manifest.ts
const FILES = [
  "architecture.md",
  "backend.md",
  "api-reference.md",
  "strategies.md",
  "backtesting.md",
  "workflow.md",
  "configuration.md",
  "testing.md",
  "go-live-checklist.md",
];

if (!existsSync(repoDocs)) {
  console.log("[sync-docs] ../docs not present — using committed content/docs as-is.");
  process.exit(0);
}

mkdirSync(outDir, { recursive: true });
let copied = 0;
for (const file of FILES) {
  const src = join(repoDocs, file);
  if (!existsSync(src)) {
    console.warn(`[sync-docs] missing source: ${file} (skipped)`);
    continue;
  }
  writeFileSync(join(outDir, file), readFileSync(src));
  copied += 1;
}
console.log(`[sync-docs] synced ${copied}/${FILES.length} docs into content/docs.`);
