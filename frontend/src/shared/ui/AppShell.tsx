"use client";

import {
  Bot,
  Boxes,
  HeartHandshake,
  LayoutDashboard,
  MapPinned,
  PackageCheck,
  Plus,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const journeys = [
  { href: "/", label: "Control centre", icon: LayoutDashboard },
  { href: "/donate", label: "Create donation", icon: Plus },
  { href: "/match", label: "Agent match", icon: Bot },
  { href: "/deliveries", label: "Driver route", icon: MapPinned },
  { href: "/confirm", label: "Confirmation", icon: PackageCheck },
  { href: "/rematch", label: "Recovery", icon: RefreshCw },
] as const;

export function AppShell({ children }: { readonly children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Kind KAI home">
          <span className="brand-mark">
            <HeartHandshake size={23} />
          </span>
          <span>
            <strong>Kind KAI</strong>
            <small>Auckland food rescue</small>
          </span>
        </Link>
        <nav aria-label="Journey navigation">
          <p className="nav-label">Live operation</p>
          {journeys.map(({ href, label, icon: Icon }, index) => {
            const isActive =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                className={`nav-item ${isActive ? "active" : ""}`}
                href={href}
                key={href}
              >
                <span className="nav-step">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <Icon size={18} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <span className="network-pulse" />
          <div>
            <strong>Demo network</strong>
            <small>Auckland · NZST</small>
          </div>
          <Boxes size={19} />
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div>
            <span className="eyebrow">Operations / Auckland</span>
          </div>
          <div className="topbar-status">
            <span className="network-pulse" /> Live coordination view
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
