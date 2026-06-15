import type { Metadata } from "next";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "AI Trade Flow",
  description: "AI-driven auto-trading platform — crypto / 台股 / 美股",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
