// Server-only: read published docs from the committed content/docs directory.
// Pages render these statically at build time (output: "standalone"), so no
// filesystem access is needed at runtime.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { getDoc } from "./docs-manifest";

const DOCS_DIR = join(process.cwd(), "content", "docs");

export function readDocContent(slug: string): string {
  const entry = getDoc(slug);
  if (!entry) {
    throw new Error(`unknown doc slug: ${slug}`);
  }
  return readFileSync(join(DOCS_DIR, entry.file), "utf8");
}
