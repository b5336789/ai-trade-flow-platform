import { Suspense } from "react";
import { BacktestPanel } from "@/components/BacktestPanel";
export default function BacktestPage() { return <Suspense fallback={null}><BacktestPanel /></Suspense>; }
