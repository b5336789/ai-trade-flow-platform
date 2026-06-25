import { api, type Workflow, type WorkflowGraph } from "@/lib/api";

const graphWithPosition = {
  nodes: [
    {
      id: "logger-1",
      type: "logger",
      params: {},
      position: { x: 42, y: 128 },
    },
  ],
  edges: [],
} satisfies WorkflowGraph;

const updateWorkflow: (id: number, name: string, graph: WorkflowGraph) => Promise<Workflow> = api.updateWorkflow;
const deleteWorkflow: (id: number) => Promise<void> = api.deleteWorkflow;

void graphWithPosition;
void updateWorkflow;
void deleteWorkflow;
