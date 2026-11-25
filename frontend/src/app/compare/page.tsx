"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { PlanetViewer } from "@/components/three/planet-viewer";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorNotice, Panel, SectionHeading } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { clsx, formatEsi, formatScore } from "@/lib/format";
import { MAX_COMPARE, useCompare } from "@/lib/store/compare";
import { useAuth } from "@/lib/store/auth";

export default function ComparePage() {
  return (
    <Suspense fallback={<PageShell><p className="text-starlight-400">Loading comparison…</p></PageShell>}>
      <CompareClient />
    </Suspense>
  );
}

function CompareClient() {
  const params = useSearchParams();
  const stored = useCompare((state) => state.slugs);
  const replace = useCompare((state) => state.replace);
  const remove = useCompare((state) => state.remove);
  const signedIn = useAuth((state) => state.status) === "authenticated";
  const [name, setName] = useState("My comparison");
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const fromUrl = useMemo(
    () =>
      (params.get("slugs") ?? "")
        .split(",")
        .map((slug) => slug.trim())
        .filter(Boolean),
    [params],
  );

  useEffect(() => {
    if (fromUrl.length >= 2) replace(fromUrl.slice(0, MAX_COMPARE));
  }, [fromUrl, replace]);

  const slugs = stored.length >= 2 ? stored : fromUrl.slice(0, MAX_COMPARE);

  const query = useQuery({
    queryKey: ["compare", slugs],
    queryFn: ({ signal }) => api.compare(slugs, signal),
    enabled: slugs.length >= 2,
  });

  const save = useMutation({
    mutationFn: () => api.saveComparison(name, slugs),
    onSuccess: () => setSavedMsg("Saved to your account."),
  });

  if (slugs.length < 2) {
    return (
      <PageShell>
        <SectionHeading
          eyebrow="Side by side"
          title="Compare worlds"
          description="Add two to four planets from any card, or start with a classic trio."
        />
        <EmptyState
          title="Pick at least two planets"
          description="Earth, TRAPPIST-1 e and Kepler-186 f are a good place to begin."
          action={
            <Button
              variant="primary"
              onClick={() => replace(["earth", "trappist-1-e", "kepler-186-f"])}
            >
              Load Earth / TRAPPIST-1 e / Kepler-186 f
            </Button>
          }
        />
      </PageShell>
    );
  }

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Side by side"
        title="Compare worlds"
        description="Each row declares which direction is better so a highlight is a property of the data, not a decoration."
      />

      {query.isError ? <ErrorNotice message="Could not compare those slugs." className="mb-4" /> : null}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {query.data?.planets.map((planet) => (
          <button
            key={planet.slug}
            type="button"
            onClick={() => remove(planet.slug)}
            className="rounded-full bg-void-800 px-3 py-1 text-sm text-starlight-100"
          >
            {planet.name} ×
          </button>
        ))}
        {signedIn ? (
          <>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="h-9 rounded-lg border border-void-700 bg-void-900 px-3 text-sm"
              aria-label="Comparison name"
            />
            <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
              Save
            </Button>
          </>
        ) : null}
        {savedMsg ? <span className="text-xs text-biosphere-300">{savedMsg}</span> : null}
      </div>

      {query.data ? (
        <>
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {query.data.planets.map((planet) => (
              <Panel key={planet.slug} className="p-3">
                <PlanetViewer
                  slug={planet.slug}
                  appearance={planet.appearance}
                  starColor={planet.star.color_hex ?? undefined}
                />
                <p className="mt-2 text-center font-display text-starlight-50">{planet.name}</p>
              </Panel>
            ))}
          </div>

          <div className="overflow-x-auto rounded-panel border border-void-700">
            <table className="w-full table-fixed text-sm">
              <thead className="bg-void-900/80 text-left text-xs uppercase tracking-wider text-starlight-400">
                <tr>
                  <th className="w-[30%] min-w-[9rem] px-4 py-3">Property</th>
                  {query.data.planets.map((planet) => (
                    <th key={planet.slug} className="min-w-[7.5rem] px-4 py-3">
                      {planet.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {query.data.rows.map((row) => {
                  const winner = winningIndex(row.better, row.values, row.earth_value);
                  return (
                    <tr key={row.key} className="border-t border-void-800">
                      <th className="px-4 py-2.5 text-left font-medium text-starlight-300">
                        {row.label}
                        {row.unit ? <span className="ml-1 text-starlight-500">{row.unit}</span> : null}
                      </th>
                      {row.display.map((cell, index) => (
                        <td
                          key={`${row.key}-${index}`}
                          className={clsx(
                            "px-4 py-2.5 tabular-nums",
                            winner === index ? "text-biosphere-300" : "text-starlight-100",
                          )}
                        >
                          {cell ?? "—"}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {query.data.notes.length > 0 ? (
            <ul className="mt-6 space-y-2 text-xs leading-relaxed text-starlight-400">
              {query.data.notes.map((note) => (
                <li key={note}>• {note}</li>
              ))}
            </ul>
          ) : null}

          <p className="mt-6 text-xs text-starlight-500">
            Habitability {query.data.planets.map((p) => `${p.name} ${formatScore(p.habitability_score)}`).join(" · ")}
            {" · "}
            ESI {query.data.planets.map((p) => `${p.name} ${formatEsi(p.esi)}`).join(" · ")}
          </p>
        </>
      ) : (
        <p className="text-starlight-400">Building the table…</p>
      )}
    </PageShell>
  );
}

function winningIndex(
  better: string,
  values: (number | null)[],
  earth: number | null,
): number | null {
  const known = values
    .map((value, index) => ({ value, index }))
    .filter((entry): entry is { value: number; index: number } => entry.value !== null);
  if (known.length === 0) return null;
  if (better === "higher") return known.reduce((best, entry) => (entry.value > best.value ? entry : best)).index;
  if (better === "lower") return known.reduce((best, entry) => (entry.value < best.value ? entry : best)).index;
  if (better === "closer_to_earth" && earth !== null) {
    return known.reduce((best, entry) =>
      Math.abs(entry.value - earth) < Math.abs(best.value - earth) ? entry : best,
    ).index;
  }
  return null;
}
