"use client";

import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, type DesignResponse, type StrategySpec } from "@/lib/api";

interface ChatMessage {
  role: "user" | "ai" | "error";
  text: string;
}

interface DesignChatProps {
  priorSpec: StrategySpec | null;
  onDesigned: (design: DesignResponse) => void;
}

const EXAMPLES = [
  "RSI 低於 30 進場、高於 70 出場",
  "20 日均線向上穿越 60 日均線就買進",
  "收盤跌破布林通道下軌買進、回到中軌賣出",
];

export function DesignChat({ priorSpec, onDesigned }: DesignChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const design = useMutation({
    mutationFn: (message: string) => api.designStrategy(message, priorSpec ?? undefined),
    onSuccess: (data, message) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", text: message },
        { role: "ai", text: data.explanation },
      ]);
      onDesigned(data);
      queueScroll();
    },
    onError: (err: unknown, message) => {
      const text = err instanceof Error ? err.message : "策略生成失敗";
      setMessages((prev) => [...prev, { role: "user", text: message }, { role: "error", text }]);
      queueScroll();
    },
  });

  function queueScroll() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || design.isPending) return;
    setDraft("");
    design.mutate(trimmed);
  }

  return (
    <section className="flex h-full min-h-[520px] flex-col rounded-lg border border-border bg-surface-1">
      <header className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="h-1.5 w-1.5 rounded-sm bg-accent" />
        <h2 className="font-display text-[15px] font-semibold">與 AI 設計策略</h2>
        <span className="rounded-sm bg-accent-dim px-1.5 py-0.5 text-[11px] font-medium text-accent">
          AI 生成
        </span>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="space-y-3 text-[13px] text-muted">
            <p>用白話描述你的進出場規則,AI 會生成一支可回測的策略。例如:</p>
            <ul className="space-y-1.5">
              {EXAMPLES.map((ex) => (
                <li key={ex}>
                  <button
                    onClick={() => submit(ex)}
                    className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-left hover:border-accent hover:bg-surface-3"
                  >
                    {ex}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {messages.map((m, i) => (
          <ChatBubble key={i} message={m} />
        ))}
        {design.isPending && (
          <div className="flex items-center gap-2 text-[13px] text-accent">
            <span className="h-1.5 w-1.5 animate-pulse rounded-sm bg-accent" />
            AI 生成中…
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(draft);
        }}
        className="flex items-end gap-2 border-t border-border p-3"
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(draft);
            }
          }}
          rows={2}
          placeholder={priorSpec ? "繼續調整這支策略…" : "描述你的策略規則…"}
          className="min-h-[44px] flex-1 resize-none rounded-md border border-border bg-surface-2 px-3 py-2 text-[13px] outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={design.isPending || !draft.trim()}
          className="rounded-md bg-accent px-4 py-2 text-[13px] font-semibold text-bg disabled:opacity-40"
        >
          送出
        </button>
      </form>
    </section>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[85%] rounded-md rounded-tr-sm bg-surface-3 px-3 py-2 text-[13px]">
        {message.text}
      </div>
    );
  }
  if (message.role === "error") {
    return (
      <div className="max-w-[90%] rounded-md border border-error/40 bg-error/10 px-3 py-2 text-[13px] text-error">
        ⚠ {message.text}
      </div>
    );
  }
  return (
    <div className="max-w-[90%] rounded-md rounded-tl-sm border border-accent/30 bg-accent-dim px-3 py-2 text-[13px] text-text">
      {message.text}
    </div>
  );
}
