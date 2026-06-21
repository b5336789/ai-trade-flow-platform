import type { WorkflowGraph } from "@/lib/api";
import { NODE_CATALOG } from "./nodeCatalog";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// Mirrors backend app/workflow/engine.py structural checks: duplicate ids, cycles,
// and required-input nodes with no incoming edge. A graph valid here will not be
// rejected by the engine for structure.
export function validateGraph(graph: WorkflowGraph): ValidationResult {
  const errors: string[] = [];
  const ids = graph.nodes.map((n) => n.id);

  // duplicate ids
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  if (dupes.length) errors.push(`重複節點 id: ${[...new Set(dupes)].join(", ")}`);

  // required-input nodes with no incoming edge
  const incoming = new Map<string, number>();
  for (const id of ids) incoming.set(id, 0);
  for (const e of graph.edges) incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1);
  for (const n of graph.nodes) {
    if (NODE_CATALOG[n.type].hasInput && (incoming.get(n.id) ?? 0) === 0) {
      errors.push(`節點 ${n.id} (${NODE_CATALOG[n.type].title}) 缺少輸入`);
    }
  }

  // cycle detection (DFS over adjacency)
  const adj = new Map<string, string[]>();
  for (const id of ids) adj.set(id, []);
  for (const e of graph.edges) adj.get(e.source)?.push(e.target);
  const state = new Map<string, 0 | 1 | 2>(); // 0=unseen,1=in-stack,2=done
  let hasCycle = false;
  const visit = (u: string) => {
    state.set(u, 1);
    for (const v of adj.get(u) ?? []) {
      const s = state.get(v) ?? 0;
      if (s === 1) hasCycle = true;
      else if (s === 0) visit(v);
    }
    state.set(u, 2);
  };
  for (const id of ids) if ((state.get(id) ?? 0) === 0) visit(id);
  if (hasCycle) errors.push("流程有循環 (cycle)");

  return { valid: errors.length === 0, errors };
}
