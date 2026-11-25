"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api";
import { EM_DASH, clsx, formatDistance, formatScore } from "@/lib/format";
import { bandForScore, bandStyle } from "@/lib/scores";
import type { SearchHit } from "@/lib/types";

function hrefFor(hit: SearchHit): string {
  return hit.kind === "planet" ? `/planets/${hit.slug}` : `/systems/${hit.slug}`;
}

/**
 * Search across stars and planets.
 *
 * Implemented as an ARIA combobox with a listbox popup rather than a plain input
 * plus a styled div, so that arrow-key navigation and the announcement of the
 * active option work the way a keyboard or screen-reader user expects.
 */
export function GlobalSearch({ className }: { className?: string }) {
  const router = useRouter();
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(term.trim()), 180);
    return () => clearTimeout(timer);
  }, [term]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", debounced],
    queryFn: ({ signal }) => api.search(debounced, 8, signal),
    enabled: debounced.length >= 2,
    staleTime: 60_000,
  });

  const hits = useMemo(() => data?.hits ?? [], [data]);

  useEffect(() => setActiveIndex(-1), [hits]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  // Cmd/Ctrl-K is the conventional shortcut and costs nothing to support.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function commit(hit: SearchHit) {
    setOpen(false);
    setTerm("");
    router.push(hrefFor(hit));
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => (hits.length === 0 ? -1 : (index + 1) % hits.length));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) =>
        hits.length === 0 ? -1 : (index - 1 + hits.length) % hits.length,
      );
    } else if (event.key === "Enter") {
      const hit = hits[activeIndex];
      if (hit) {
        event.preventDefault();
        commit(hit);
      } else if (term.trim().length > 0) {
        event.preventDefault();
        setOpen(false);
        router.push(`/explore?q=${encodeURIComponent(term.trim())}`);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
    }
  }

  const showPopup = open && debounced.length >= 2;
  const activeId = activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined;

  return (
    <div ref={containerRef} className={clsx("relative", className)}>
      <div className="relative">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-starlight-400" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showPopup}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          aria-label="Search stars and exoplanets"
          placeholder="Search TRAPPIST-1, Kepler-186f, Proxima…"
          value={term}
          onChange={(event) => {
            setTerm(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="h-10 w-full rounded-lg border border-void-700 bg-void-900/80 pl-9 pr-16 text-sm text-starlight-100 placeholder:text-starlight-500 focus:border-aurora-500 focus:outline-none"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-void-600 bg-void-800 px-1.5 py-0.5 font-mono text-[0.625rem] text-starlight-400 sm:block">
          ⌘K
        </kbd>
      </div>

      {showPopup ? (
        <div className="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-lg border border-void-700 bg-void-900/95 shadow-2xl backdrop-blur-xl">
          <ul id={listboxId} role="listbox" aria-label="Search results">
            {hits.map((hit, index) => {
              const style = bandStyle(bandForScore(hit.habitability_score));
              return (
                <li
                  key={`${hit.kind}-${hit.slug}`}
                  id={`${listboxId}-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                >
                  <Link
                    href={hrefFor(hit)}
                    onClick={() => {
                      setOpen(false);
                      setTerm("");
                    }}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2.5 transition-colors",
                      index === activeIndex ? "bg-void-800" : "hover:bg-void-800/60",
                    )}
                  >
                    <span
                      className={clsx(
                        "shrink-0 rounded px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wide",
                        hit.kind === "planet"
                          ? "bg-aurora-500/15 text-aurora-300"
                          : "bg-solar-500/15 text-solar-300",
                      )}
                    >
                      {hit.kind}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-starlight-100">
                        {hit.name}
                      </span>
                      <span className="block truncate text-xs text-starlight-400">
                        {hit.subtitle}
                      </span>
                    </span>
                    <span className="shrink-0 text-right text-xs tabular-nums">
                      <span className={clsx("block font-semibold", style.text)}>
                        {hit.habitability_score === null ? EM_DASH : formatScore(hit.habitability_score)}
                      </span>
                      <span className="block text-starlight-500">
                        {formatDistance(hit.distance_ly)}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>

          {hits.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-starlight-400">
              {isFetching ? "Searching…" : `Nothing matches “${debounced}”.`}
            </p>
          ) : (
            <Link
              href={`/explore?q=${encodeURIComponent(debounced)}`}
              onClick={() => setOpen(false)}
              className="block border-t border-void-700 px-3 py-2 text-center text-xs font-medium text-aurora-300 hover:bg-void-800/60"
            >
              See all results in the explorer
            </Link>
          )}
        </div>
      ) : null}
    </div>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      aria-hidden
    >
      <circle cx="8.5" cy="8.5" r="5.5" />
      <path d="M12.8 12.8 17 17" strokeLinecap="round" />
    </svg>
  );
}
