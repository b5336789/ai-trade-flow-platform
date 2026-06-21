"use client";

import type { WorkflowSignalDTO } from "@/lib/api";

export function SignalTraceDrawer({
  signal,
  onClose,
}: {
  signal: WorkflowSignalDTO | null;
  onClose: () => void;
}) {
  if (!signal) return null;

  return (
    <aside
      className="signal-trace-drawer"
      role="dialog"
      aria-label="Signal derivation"
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: 340,
        background: "var(--surface-1, #111317)",
        borderLeft: "1px solid var(--border, rgba(255,255,255,.08))",
        overflowY: "auto",
        zIndex: 50,
        padding: "20px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <strong style={{ fontFamily: "var(--font-display, 'Space Grotesk', sans-serif)", fontSize: 15 }}>
          {signal.symbol} · {signal.action.toUpperCase()} · conf {signal.confidence.toFixed(2)}
        </strong>
        <button
          onClick={onClose}
          aria-label="Close"
          style={{
            background: "none",
            border: "none",
            color: "var(--text-muted, #8A9099)",
            fontSize: 18,
            cursor: "pointer",
            lineHeight: 1,
            padding: "4px 6px",
          }}
        >
          ×
        </button>
      </header>

      <p
        style={{
          color: "var(--text-muted, #8A9099)",
          fontSize: 11,
          margin: 0,
          fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
        }}
      >
        {new Date(signal.timestamp).toLocaleString()} · price {signal.price}
      </p>

      <ol
        style={{
          margin: 0,
          padding: 0,
          listStyle: "none",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {signal.trace_json.map((step, i) => (
          <li
            key={`${step.node_id}-${i}`}
            style={{
              background: "var(--surface-2, #16181D)",
              border: "1px solid var(--border, rgba(255,255,255,.08))",
              borderRadius: "var(--r-md, 6px)",
              padding: "8px 10px",
              fontSize: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: 4,
                color: "var(--text-muted, #8A9099)",
              }}
            >
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: "var(--surface-3, #1E2127)",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </span>
              <code
                style={{
                  fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
                  fontSize: 11,
                  color: "var(--text, #E7E9EC)",
                }}
              >
                {step.type}
              </code>
              <span
                style={{
                  color: "var(--text-faint, #5B616B)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
                }}
              >
                {step.node_id}
              </span>
            </div>
            <pre
              style={{
                margin: 0,
                padding: 0,
                fontSize: 10,
                fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
                color: "var(--text-muted, #8A9099)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {JSON.stringify(step.summary, null, 2)}
            </pre>
          </li>
        ))}
      </ol>

      <footer
        style={{
          marginTop: "auto",
          paddingTop: 12,
          borderTop: "1px solid var(--border, rgba(255,255,255,.08))",
          fontSize: 12,
          color: "var(--text-muted, #8A9099)",
          fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
        }}
      >
        Result: <strong style={{ color: "var(--text, #E7E9EC)" }}>{signal.action.toUpperCase()}</strong>
        {" "}· confidence <strong style={{ color: "var(--text, #E7E9EC)" }}>{signal.confidence.toFixed(2)}</strong>
      </footer>
    </aside>
  );
}
