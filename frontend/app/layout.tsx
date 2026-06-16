import type { Metadata, Viewport } from "next";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "AI Trade Flow — AI 驅動自動交易平台",
  description: "AI-driven auto-trading platform — crypto / 台股 / 美股",
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant" className="font-sans">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
