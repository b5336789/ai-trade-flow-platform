import { Suspense } from "react";
import { MarketPanel } from "@/components/MarketPanel";

export default function MarketPage() {
  return (
    <Suspense fallback={null}>
      <MarketPanel />
    </Suspense>
  );
}
