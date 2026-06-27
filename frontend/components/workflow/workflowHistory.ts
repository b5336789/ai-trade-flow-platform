export interface WorkflowHistory<TSnapshot> {
  past: TSnapshot[];
  future: TSnapshot[];
  limit: number;
}

export function createWorkflowHistory<TSnapshot>(limit: number): WorkflowHistory<TSnapshot> {
  return { past: [], future: [], limit };
}

export function pushWorkflowSnapshot<TSnapshot>(
  history: WorkflowHistory<TSnapshot>,
  snapshot: TSnapshot,
) {
  history.past.push(snapshot);
  if (history.past.length > history.limit) history.past.shift();
  history.future = [];
}

export function resetWorkflowHistory<TSnapshot>(history: WorkflowHistory<TSnapshot>) {
  history.past = [];
  history.future = [];
}

export function undoWorkflowSnapshot<TSnapshot>(
  history: WorkflowHistory<TSnapshot>,
  current: TSnapshot,
): TSnapshot | null {
  const prev = history.past.pop();
  if (!prev) return null;
  history.future.push(current);
  return prev;
}

export function redoWorkflowSnapshot<TSnapshot>(
  history: WorkflowHistory<TSnapshot>,
  current: TSnapshot,
): TSnapshot | null {
  const next = history.future.pop();
  if (!next) return null;
  history.past.push(current);
  return next;
}
