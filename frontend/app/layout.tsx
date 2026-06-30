import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gemini Trail",
  description: "Post-apocalyptic cross-country survival. Long Beach to Washington, DC.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-ash-900 text-sand-200 min-h-screen">{children}</body>
    </html>
  );
}
