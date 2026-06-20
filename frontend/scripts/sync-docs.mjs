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

// Single source of truth: derive the file list from lib/docs-manifest.ts so the
// manifest and the synced/committed files can never drift apart.
function filesFromManifest() {
  const manifest = readFileSync(join(frontendRoot, "lib", "docs-manifest.ts"), "utf8");
  const files = [...manifest.matchAll(/\bfile:\s*"([^"]+)"/g)].map((m) => m[1]);
  if (files.length === 0) {
    throw new Error("[sync-docs] no file: entries found in docs-manifest.ts");
  }
  return files;
}

const FILES = filesFromManifest();

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
