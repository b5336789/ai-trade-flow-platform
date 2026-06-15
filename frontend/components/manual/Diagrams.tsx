// Hand-drawn SVG diagrams for the illustrated user manual (no external image assets).

export function ArchitectureDiagram() {
  const box = (x: number, y: number, w: number, h: number, fill: string) => (
    <rect x={x} y={y} width={w} height={h} rx={8} fill={fill} stroke="#3f3f46" />
  );
  return (
    <svg viewBox="0 0 820 300" className="w-full rounded-lg border border-neutral-800 bg-neutral-950 p-2">
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6 Z" fill="#71717a" />
        </marker>
      </defs>
      {/* user / scheduler */}
      {box(20, 120, 130, 60, "#1e293b")}
      <text x={85} y={146} textAnchor="middle" fill="#e2e8f0" fontSize="13">使用者 / 排程</text>
      <text x={85} y={164} textAnchor="middle" fill="#94a3b8" fontSize="11">Web · APScheduler</text>

      {/* workflow engine */}
      {box(210, 120, 150, 60, "#312e81")}
      <text x={285} y={146} textAnchor="middle" fill="#e0e7ff" fontSize="13">Workflow 引擎</text>
      <text x={285} y={164} textAnchor="middle" fill="#a5b4fc" fontSize="11">節點圖執行</text>

      {/* nodes column */}
      {box(420, 40, 150, 44, "#14532d")}
      <text x={495} y={67} textAnchor="middle" fill="#dcfce7" fontSize="12">Data Source(行情)</text>
      {box(420, 128, 150, 44, "#3b0764")}
      <text x={495} y={155} textAnchor="middle" fill="#f3e8ff" fontSize="12">策略 / AI 訊號</text>
      {box(420, 216, 150, 44, "#7c2d12")}
      <text x={495} y={243} textAnchor="middle" fill="#ffedd5" fontSize="12">下單 + 風控</text>

      {/* broker / exchange */}
      {box(630, 128, 160, 44, "#0c4a6e")}
      <text x={710} y={150} textAnchor="middle" fill="#e0f2fe" fontSize="12">Broker</text>
      <text x={710} y={165} textAnchor="middle" fill="#7dd3fc" fontSize="10">paper / live · ccxt</text>
      {box(630, 216, 160, 44, "#374151")}
      <text x={710} y={243} textAnchor="middle" fill="#e5e7eb" fontSize="12">交易所 / Claude</text>

      {/* arrows */}
      <line x1={150} y1={150} x2={208} y2={150} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={360} y1={150} x2={418} y2={62} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={360} y1={150} x2={418} y2={150} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={360} y1={150} x2={418} y2={236} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={570} y1={150} x2={628} y2={150} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={570} y1={238} x2={628} y2={238} stroke="#71717a" markerEnd="url(#arrow)" />
      <line x1={710} y1={172} x2={710} y2={214} stroke="#71717a" markerEnd="url(#arrow)" />
    </svg>
  );
}

export function PipelineDiagram() {
  const steps = [
    { label: "Data Source", sub: "BTC/USDT", color: "#14532d" },
    { label: "策略 / AI", sub: "buy/sell/hold", color: "#3b0764" },
    { label: "Order", sub: "下單(風控)", color: "#7c2d12" },
    { label: "Logger", sub: "記錄結果", color: "#1f2937" },
  ];
  return (
    <svg viewBox="0 0 820 100" className="w-full rounded-lg border border-neutral-800 bg-neutral-950 p-2">
      <defs>
        <marker id="arrow2" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6 Z" fill="#71717a" />
        </marker>
      </defs>
      {steps.map((s, i) => {
        const x = 20 + i * 200;
        return (
          <g key={s.label}>
            <rect x={x} y={28} width={160} height={48} rx={8} fill={s.color} stroke="#3f3f46" />
            <text x={x + 80} y={50} textAnchor="middle" fill="#f5f5f5" fontSize="13">{s.label}</text>
            <text x={x + 80} y={67} textAnchor="middle" fill="#a1a1aa" fontSize="11">{s.sub}</text>
            {i < steps.length - 1 && (
              <line x1={x + 160} y1={52} x2={x + 200} y2={52} stroke="#71717a" markerEnd="url(#arrow2)" />
            )}
          </g>
        );
      })}
    </svg>
  );
}

// Tiny representative thumbnails for each dashboard panel.
export function ChartThumb() {
  return (
    <svg viewBox="0 0 120 60" className="h-16 w-full rounded border border-neutral-800 bg-neutral-950">
      {[
        [12, 20, 38], [28, 14, 30], [44, 24, 46], [60, 10, 26], [76, 30, 50], [92, 18, 40],
      ].map(([x, top, bot], i) => (
        <g key={i}>
          <line x1={x} y1={top - 6} x2={x} y2={bot + 6} stroke="#52525b" />
          <rect x={x - 4} y={Math.min(top, bot)} width={8} height={Math.abs(bot - top)} fill={i % 2 ? "#ef4444" : "#22c55e"} />
        </g>
      ))}
    </svg>
  );
}

export function GraphThumb() {
  return (
    <svg viewBox="0 0 120 60" className="h-16 w-full rounded border border-neutral-800 bg-neutral-950">
      <line x1={28} y1={30} x2={58} y2={30} stroke="#71717a" />
      <line x1={62} y1={30} x2={92} y2={30} stroke="#71717a" />
      <rect x={8} y={22} width={20} height={16} rx={3} fill="#14532d" />
      <rect x={50} y={22} width={20} height={16} rx={3} fill="#3b0764" />
      <rect x={92} y={22} width={20} height={16} rx={3} fill="#7c2d12" />
    </svg>
  );
}

export function TableThumb() {
  return (
    <svg viewBox="0 0 120 60" className="h-16 w-full rounded border border-neutral-800 bg-neutral-950">
      {[14, 26, 38, 50].map((y, i) => (
        <g key={y}>
          <rect x={10} y={y - 7} width={40} height={5} rx={2} fill="#52525b" />
          <rect x={60} y={y - 7} width={24} height={5} rx={2} fill={i === 0 ? "#52525b" : "#22c55e"} />
          <rect x={90} y={y - 7} width={20} height={5} rx={2} fill="#3f3f46" />
        </g>
      ))}
    </svg>
  );
}
