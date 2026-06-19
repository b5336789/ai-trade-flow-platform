import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono, Noto_Sans_TC } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Providers } from "./providers";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const code = JetBrains_Mono({ subsets: ["latin"], variable: "--font-code", display: "swap" });
const cjk = Noto_Sans_TC({ weight: ["400", "500", "700"], subsets: ["latin"], variable: "--font-cjk", display: "swap", preload: false });

export const metadata: Metadata = {
  title: "AI Trade Flow",
  description: "AI-driven auto-trading platform — crypto / 台股 / 美股",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${display.variable} ${code.variable} ${cjk.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
