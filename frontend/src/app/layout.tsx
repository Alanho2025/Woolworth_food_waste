import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/shared/ui/AppShell";
import { QueryProvider } from "@/shared/ui/QueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FoodFlow Auckland",
    template: "%s · FoodFlow Auckland",
  },
  description: "Auckland's live food rescue coordination network",
};

interface RootLayoutProps {
  readonly children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en-NZ">
      <body>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
