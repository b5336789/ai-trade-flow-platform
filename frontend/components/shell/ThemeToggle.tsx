"use client";
import { Monitor, Sun, Moon } from "lucide-react";
import { useTheme, type ThemePreference } from "@/app/providers";

const OPTS: { value: ThemePreference; label: string; Icon: typeof Monitor }[] = [
  { value: "system", label: "系統主題", Icon: Monitor },
  { value: "light", label: "亮色主題", Icon: Sun },
  { value: "dark", label: "暗色主題", Icon: Moon },
];

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  return (
    <div
      role="radiogroup"
      aria-label="主題"
      className="flex items-center gap-0.5 rounded-md border border-border bg-surface-2 p-0.5"
    >
      {OPTS.map(({ value, label, Icon }) => {
        const active = preference === value;
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setPreference(value)}
            className={`rounded p-1.5 transition-colors ${
              active ? "bg-accent-dim text-accent" : "text-muted hover:text-text"
            }`}
          >
            <Icon size={14} />
          </button>
        );
      })}
    </div>
  );
}
