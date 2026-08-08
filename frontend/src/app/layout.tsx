import type { ReactNode } from "react";

import "./globals.css";

export const metadata = {
  title: "FoodFlow Platform Foundation",
  description:
    "Empty application foundation for the next FoodFlow platform iteration.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en-NZ">
      <body>{children}</body>
    </html>
  );
}
