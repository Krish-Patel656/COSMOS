"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";

import { Button, ButtonLink } from "@/components/ui/button";
import { api } from "@/lib/api";
import { MAX_COMPARE, useCompare } from "@/lib/store/compare";

export function CompareTray() {
  const pathname = usePathname();
  const slugs = useCompare((state) => state.slugs);
  const remove = useCompare((state) => state.remove);
  const clear = useCompare((state) => state.clear);

  const { data } = useQuery({
    queryKey: ["compare-tray", slugs],
    queryFn: ({ signal }) => api.compare(slugs, signal),
    enabled: slugs.length >= 2,
  });

  if (slugs.length === 0 || pathname === "/compare") return null;

  const names = new Map((data?.planets ?? []).map((planet) => [planet.slug, planet.name]));

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-void-700 bg-void-950/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <p className="text-xs font-semibold uppercase tracking-wider text-aurora-400">
          Compare ({slugs.length}/{MAX_COMPARE})
        </p>
        <ul className="flex min-w-0 flex-1 flex-wrap gap-2">
          {slugs.map((slug) => (
            <li
              key={slug}
              className="inline-flex items-center gap-1.5 rounded-full bg-void-800 px-2.5 py-1 text-xs text-starlight-100"
            >
              <span className="max-w-[10rem] truncate">{names.get(slug) ?? slug}</span>
              <button
                type="button"
                onClick={() => remove(slug)}
                aria-label={`Remove ${names.get(slug) ?? slug}`}
                className="text-starlight-400 hover:text-ember-300"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={clear}>
            Clear
          </Button>
          {slugs.length >= 2 ? (
            <ButtonLink
              size="sm"
              variant="primary"
              href={`/compare?slugs=${slugs.join(",")}`}
            >
              Compare now
            </ButtonLink>
          ) : (
            <p className="text-xs text-starlight-400">Add one more world</p>
          )}
        </div>
      </div>
    </div>
  );
}
