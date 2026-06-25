import { api, type WorkflowGraph } from "@/lib/api";

const graphWithPosition: WorkflowGraph = {
  nodes: [
    {
      id: "logger-1",
      type: "logger",
      params: {},
      position: { x: 42, y: 128 },
    },
  ],
  edges: [],
};

void api.updateWorkflow(7, "existing workflow", graphWithPosition);
void api.deleteWorkflow(7);
