import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "surface-1": "var(--surface-1)", "surface-2": "var(--surface-2)", "surface-3": "var(--surface-3)",
        border: "var(--border)", "border-strong": "var(--border-strong)",
        text: "var(--text)", muted: "var(--muted)", faint: "var(--faint)",
        accent: "var(--accent)", "accent-dim": "var(--accent-dim)",
        up: "var(--up)", down: "var(--down)",
        warning: "var(--warning)", error: "var(--error)", live: "var(--live)",
        "c-data": "var(--c-data)", "c-strat": "var(--c-strat)", "c-logic": "var(--c-logic)",
        "c-order": "var(--c-order)", "c-out": "var(--c-out)",
      },
      fontFamily: {
        display: ["var(--font-display)", "var(--font-ui)", "var(--font-cjk)", "sans-serif"],
        ui: ["var(--font-ui)", "var(--font-cjk)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        code: ["var(--font-code)", "monospace"],
      },
      borderRadius: { sm: "4px", md: "6px", lg: "8px" },
    },
  },
  plugins: [],
};
export default config;
