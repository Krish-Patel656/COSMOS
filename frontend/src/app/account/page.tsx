"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { PlanetCard } from "@/components/planets/planet-card";
import { Button, ButtonLink } from "@/components/ui/button";
import { EmptyState, Panel, SectionHeading } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useCompare } from "@/lib/store/compare";
import { useAuth } from "@/lib/store/auth";

export default function AccountPage() {
  const status = useAuth((state) => state.status);
  const user = useAuth((state) => state.user);

  if (status === "idle" || status === "loading") {
    return (
      <PageShell>
        <p className="text-starlight-400">Checking session…</p>
      </PageShell>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <PageShell>
        <EmptyState
          title="Sign in to keep a notebook"
          description="Favourites, named collections and saved comparisons require an account."
          action={<ButtonLink href="/login" variant="primary">Sign in</ButtonLink>}
        />
      </PageShell>
    );
  }

  return <AccountBody displayName={user.display_name} />;
}

function AccountBody({ displayName }: { displayName: string }) {
  const queryClient = useQueryClient();
  const replaceCompare = useCompare((state) => state.replace);
  const [collectionName, setCollectionName] = useState("");

  const planets = useQuery({
    queryKey: ["favorite-planets"],
    queryFn: ({ signal }) => api.favoritePlanets(signal),
  });
  const stars = useQuery({
    queryKey: ["favorite-stars"],
    queryFn: ({ signal }) => api.favoriteStars(signal),
  });
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: ({ signal }) => api.collections(signal),
  });
  const comparisons = useQuery({
    queryKey: ["saved-comparisons"],
    queryFn: ({ signal }) => api.savedComparisons(signal),
  });

  const createCollection = useMutation({
    mutationFn: () => api.createCollection(collectionName),
    onSuccess: async () => {
      setCollectionName("");
      await queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const deleteCollection = useMutation({
    mutationFn: (id: number) => api.deleteCollection(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const deleteComparison = useMutation({
    mutationFn: (id: number) => api.deleteComparison(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-comparisons"] });
    },
  });

  return (
    <PageShell>
      <SectionHeading
        eyebrow="Notebook"
        title={`Hello, ${displayName}`}
        description="Worlds you mark stay attached to this account. Collections are private unless you publish them."
      />

      <section className="mb-12">
        <h2 className="mb-4 font-display text-2xl">Favourite planets</h2>
        {planets.data && planets.data.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2">
            {planets.data.map((planet) => (
              <PlanetCard key={planet.slug} planet={planet} compact />
            ))}
          </div>
        ) : (
          <EmptyState title="No favourite planets yet" action={<ButtonLink href="/explore">Explore</ButtonLink>} />
        )}
      </section>

      <section className="mb-12">
        <h2 className="mb-4 font-display text-2xl">Favourite stars</h2>
        {stars.data && stars.data.length > 0 ? (
          <ul className="grid gap-3 sm:grid-cols-2">
            {stars.data.map((star) => (
              <li key={star.slug}>
                <Link
                  href={`/systems/${star.slug}`}
                  className="block rounded-panel border border-void-700 px-4 py-3 hover:border-void-500"
                >
                  <span className="font-display text-starlight-50">{star.name}</span>
                  <span className="mt-1 block text-xs text-starlight-400">
                    {star.spectral_type} · {star.planet_count} planets
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-starlight-400">Star a host from any system page once favourites for stars are added from the map.</p>
        )}
      </section>

      <section className="mb-12">
        <h2 className="mb-4 font-display text-2xl">Collections</h2>
        <form
          className="mb-4 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (collectionName.trim()) createCollection.mutate();
          }}
        >
          <input
            value={collectionName}
            onChange={(event) => setCollectionName(event.target.value)}
            placeholder="New collection name"
            className="h-10 flex-1 rounded-lg border border-void-700 bg-void-900 px-3 text-sm"
          />
          <Button type="submit" disabled={createCollection.isPending}>
            Create
          </Button>
        </form>
        <div className="grid gap-4 md:grid-cols-2">
          {(collections.data ?? []).map((collection) => (
            <Panel key={collection.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-lg">{collection.name}</h3>
                  <p className="text-xs text-starlight-400">
                    {collection.items.length} items
                    {collection.description ? ` · ${collection.description}` : ""}
                  </p>
                </div>
                <Button size="sm" variant="danger" onClick={() => deleteCollection.mutate(collection.id)}>
                  Delete
                </Button>
              </div>
              <ul className="mt-3 space-y-1 text-sm">
                {collection.items.map((item) => (
                  <li key={item.id}>
                    <Link
                      href={item.target_type === "planet" ? `/planets/${item.target_slug}` : `/systems/${item.target_slug}`}
                      className="text-aurora-300"
                    >
                      {item.target_slug}
                    </Link>
                  </li>
                ))}
              </ul>
            </Panel>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl">Saved comparisons</h2>
        {(comparisons.data ?? []).length === 0 ? (
          <EmptyState title="No saved comparisons" action={<ButtonLink href="/compare">Compare</ButtonLink>} />
        ) : (
          <ul className="space-y-3">
            {comparisons.data?.map((comparison) => (
              <li
                key={comparison.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-panel border border-void-700 px-4 py-3"
              >
                <div>
                  <p className="font-medium">{comparison.name}</p>
                  <p className="text-xs text-starlight-400">{comparison.planet_slugs.join(", ")}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => replaceCompare(comparison.planet_slugs)}
                  >
                    Load
                  </Button>
                  <ButtonLink size="sm" href={`/compare?slugs=${comparison.planet_slugs.join(",")}`}>
                    Open
                  </ButtonLink>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => deleteComparison.mutate(comparison.id)}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </PageShell>
  );
}
