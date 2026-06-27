"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "active-market";
const DEFAULT_MARKET = "crypto";

/** The ONLY place that drives --up/--down inversion for 台股 (red-up). */
function applyDataMarket(market: string) {
  if (typeof document === "undefined") return;
  if (market === "tw_stock") document.documentElement.dataset.market = "tw";
  else delete document.documentElement.dataset.market;
}

interface MarketContextValue {
  market: string;
  setMarket: (m: string) => void;
}

const MarketContext = createContext<MarketContextValue | null>(null);

export function MarketProvider({ children }: { children: React.ReactNode }) {
  const [market, setMarketState] = useState<string>(DEFAULT_MARKET);

  // Hydrate from localStorage once, and apply data-market for the restored market.
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const m = stored || DEFAULT_MARKET;
    setMarketState(m);
    applyDataMarket(m);
  }, []);

  const setMarket = useCallback((m: string) => {
    setMarketState(m);
    applyDataMarket(m);
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, m);
  }, []);

  return <MarketContext.Provider value={{ market, setMarket }}>{children}</MarketContext.Provider>;
}

export function useActiveMarket(): MarketContextValue {
  const ctx = useContext(MarketContext);
  if (!ctx) throw new Error("useActiveMarket must be used within MarketProvider");
  return ctx;
}
