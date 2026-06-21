"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { L } from "@/lib/labels";

const KEY = "atf-onboarding-dismissed";

const STEPS = [
  { href: "/strategy-lab", title: L.onboarding.step1Title, body: L.onboarding.step1Body, ai: true },
  { href: "/trading-room/backtest", title: L.onboarding.step2Title, body: L.onboarding.step2Body, ai: false },
  { href: "/schedules", title: L.onboarding.step3Title, body: L.onboarding.step3Body, ai: false },
];

export function Onboarding() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Read after mount to avoid SSR/client hydration mismatch.
    setShow(typeof window !== "undefined" && localStorage.getItem(KEY) !== "1");
  }, []);

  if (!show) return null;

  function dismiss() {
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      /* private mode — best effort */
    }
    setShow(false);
  }

  return (
    <section className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-muted">{L.onboarding.title}</h2>
        <button
          onClick={dismiss}
          className="rounded-md bg-surface-2 px-2 py-1 text-xs text-muted hover:bg-surface-3 hover:text-text"
        >
          {L.onboarding.dismiss}
        </button>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {STEPS.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="group rounded-md border border-border bg-surface-2 p-3 hover:border-accent hover:bg-surface-3"
          >
            <div className="flex items-center gap-2">
              {s.ai && <span className="h-1.5 w-1.5 rounded-sm bg-accent" />}
              <span className="font-display text-sm font-semibold text-text">{s.title}</span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted">{s.body}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
