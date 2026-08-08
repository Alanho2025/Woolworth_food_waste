import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "FoodFlow Auckland",
  description: "Food rescue coordination for Auckland",
};

interface RootLayoutProps {
  readonly children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en-NZ">
      <body>{children}</body>
    </html>
  );
}
