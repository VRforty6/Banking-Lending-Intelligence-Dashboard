import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "HMDA Lending Intelligence",
  description: "Interactive lending analytics over the validated HMDA warehouse.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">{children}</body>
    </html>
  );
}
