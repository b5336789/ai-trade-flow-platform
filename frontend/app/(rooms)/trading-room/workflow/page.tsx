import { Suspense } from "react";
import { WorkflowBuilder } from "@/components/workflow/WorkflowBuilder";

export default function WorkflowPage() {
  return (
    <Suspense fallback={null}>
      <WorkflowBuilder />
    </Suspense>
  );
}
