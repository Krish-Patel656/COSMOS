"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { GlobalSearch } from "@/components/search/global-search";
import { DisplaySettings } from "@/components/settings/display-settings";
import { clsx } from "@/lib/format";
import { useAuth } from "@/lib/store/auth";

const LINKS = [
  { href: "/explore", label: "Explore" },
  { href: "/map", label: "Stellar map" },
  { href: "/compare", label: "Compare" },
  { href: "/simulator", label: "Simulator" },
  { href: "/methodology", label: "Methodology" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const status = useAuth((state) => state.status);
  const user = useAuth((state) => state.user);
  const logout = useAuth((state) => state.logout);

  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <header className="sticky top-0 z-40 border-b border-void-800 bg-void-950/95 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label="COSMOS home">
          <LogoMark className="size-7" />
          <span className="font-display text-lg font-semibold tracking-tight text-starlight-50">
            COSMOS
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 xl:flex">
          {LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={clsx(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-void-800 text-starlight-50"
                    : "text-starlight-300 hover:bg-void-800/60 hover:text-starlight-100",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto hidden min-w-0 flex-1 justify-end md:flex">
          <GlobalSearch className="w-full max-w-sm" />
        </div>

        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <DisplaySettings />

          {status === "authenticated" && user ? (
            <div className="hidden items-center gap-2 sm:flex">
              <Link
                href="/account"
                className="rounded-lg px-3 py-2 text-sm font-medium text-starlight-200 hover:bg-void-800/60"
              >
                {user.display_name}
              </Link>
              <button
                type="button"
                onClick={logout}
                className="rounded-lg px-2 py-2 text-sm text-starlight-400 hover:bg-void-800/60 hover:text-starlight-200"
              >
                Sign out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="hidden rounded-lg bg-void-800/80 px-3 py-2 text-sm font-medium text-starlight-100 ring-1 ring-void-600 hover:bg-void-700 sm:block"
            >
              Sign in
            </Link>
          )}

          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            aria-label="Toggle navigation menu"
            className="rounded-lg p-2 text-starlight-300 hover:bg-void-800/60 xl:hidden"
          >
            <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
              {mobileOpen ? (
                <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
              ) : (
                <path d="M3 6h14M3 10h14M3 14h14" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {mobileOpen ? (
        <div id="mobile-nav" className="border-t border-void-800 bg-void-950/95 px-4 py-4 xl:hidden">
          <GlobalSearch className="mb-4 md:hidden" />
          <nav aria-label="Primary mobile" className="flex flex-col gap-1">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-starlight-200 hover:bg-void-800/60"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href={status === "authenticated" ? "/account" : "/login"}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-starlight-200 hover:bg-void-800/60"
            >
              {status === "authenticated" ? "My collections" : "Sign in"}
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <defs>
        <radialGradient id="cosmos-logo-core" cx="50%" cy="45%" r="55%">
          <stop offset="0%" stopColor="#f8f7ff" />
          <stop offset="55%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#0284c7" />
        </radialGradient>
      </defs>
      <ellipse
        cx="16"
        cy="16"
        rx="15"
        ry="5.5"
        fill="none"
        stroke="#34d399"
        strokeOpacity="0.55"
        strokeWidth="1.2"
        transform="rotate(-22 16 16)"
      />
      <circle cx="16" cy="16" r="7" fill="url(#cosmos-logo-core)" />
      <circle cx="28.2" cy="11.2" r="1.9" fill="#fcd34d" />
    </svg>
  );
}
