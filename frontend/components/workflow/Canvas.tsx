"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  useReactFlow,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import { useCallback, useMemo } from "react";
import type { NodeType } from "@/lib/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, NODE_CATALOG, type NodeCategory } from "./nodeCatalog";
import { TradeNode } from "./TradeNode";
import type { TradeNodeData, useWorkflowState } from "./useWorkflowState";

const CATS: NodeCategory[] = ["data", "strategy", "logic", "order", "output"];

export function Canvas({ wf, onInit }: { wf: ReturnType<typeof useWorkflowState>; onInit?: (i: ReactFlowInstance) => void }) {
  const nodeTypes = useMemo(() => ({ trade: TradeNode }), []);
  const { screenToFlowPosition } = useReactFlow();

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData("application/reactflow");
      if (!raw) return;
      const payload = JSON.parse(raw) as { type: NodeType; savedStrategyId?: number; name?: string };
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      if (payload.savedStrategyId !== undefined) {
        wf.addNode("strategy", position, { savedStrategyId: payload.savedStrategyId, params: { name: payload.name } });
      } else {
        wf.addNode(payload.type, position);
      }
    },
    [screenToFlowPosition, wf],
  );

  const minimapColor = useCallback(
    (n: Node) => NODE_CATALOG[(n.data as TradeNodeData).nodeType].colorVar,
    [],
  );

  return (
    <div className="relative h-full w-full" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={wf.nodes}
        edges={wf.edges}
        nodeTypes={nodeTypes}
        onNodesChange={wf.onNodesChange}
        onEdgesChange={wf.onEdgesChange}
        onConnect={wf.onConnect}
        onNodeClick={(_, n) => wf.setSelectedId(n.id)}
        onPaneClick={() => wf.setSelectedId(null)}
        onInit={onInit}
        deleteKeyCode={["Backspace", "Delete"]}
        onNodesDelete={() => wf.setSelectedId(null)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} />
        <Controls />
        <MiniMap nodeColor={minimapColor} pannable zoomable className="!bg-surface-2" />
        <Panel position="bottom-left">
          <div className="flex flex-wrap gap-2 rounded-md border border-border bg-surface-1/90 px-2 py-1 text-[10px]">
            {CATS.map((c) => (
              <span key={c} className="flex items-center gap-1 text-muted">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: CATEGORY_COLOR[c] }} />
                {CATEGORY_LABEL[c]}
              </span>
            ))}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
