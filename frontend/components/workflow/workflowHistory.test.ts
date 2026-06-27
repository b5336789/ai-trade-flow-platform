import { deepEqual } from "node:assert/strict";
import { test } from "node:test";
import {
  createWorkflowHistory,
  resetWorkflowHistory,
  undoWorkflowSnapshot,
  pushWorkflowSnapshot,
} from "./workflowHistory";

type SavedGraph = { workflowId: number | null; graphLabel: string };

test("loading a saved workflow clears undo history so save cannot overwrite it with the previous draft", () => {
  const history = createWorkflowHistory<SavedGraph>(50);
  const draftGraph = { workflowId: null, graphLabel: "unsaved draft" };
  const loadedWorkflow = { workflowId: 7, graphLabel: "loaded workflow #7" };

  pushWorkflowSnapshot(history, draftGraph);
  resetWorkflowHistory(history);

  const graphAfterUndo = undoWorkflowSnapshot(history, loadedWorkflow) ?? loadedWorkflow;

  deepEqual(graphAfterUndo, loadedWorkflow);
});
