"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { api } from "@/lib/api";
import { MAX_COMPARE, useCompare } from "@/lib/store/compare";
import { useAuth } from "@/lib/store/auth";

export function PlanetActions({
  slug,
  name,
  starSlug,
  dense = false,
}: {
  slug: string;
  name: string;
  starSlug: string;
  dense?: boolean;
}) {
  const queryClient = useQueryClient();
  const status = useAuth((state) => state.status);
  const signedIn = status === "authenticated";
  const has = useCompare((state) => state.has(slug));
  const toggle = useCompare((state) => state.toggle);
  const isFull = useCompare((state) => state.slugs.length >= MAX_COMPARE);
  const [note, setNote] = useState<string | null>(null);

  const { data: favorites } = useQuery({
    queryKey: ["favorites"],
    queryFn: ({ signal }) => api.favorites(signal),
    enabled: signedIn,
  });
  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: ({ signal }) => api.collections(signal),
    enabled: signedIn,
  });

  const favourited = Boolean(
    favorites?.some((item) => item.target_type === "planet" && item.target_slug === slug),
  );

  const favoriteMutation = useMutation({
    mutationFn: async () => {
      if (favourited) await api.removeFavorite("planet", slug);
      else await api.addFavorite("planet", slug);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
      await queryClient.invalidateQueries({ queryKey: ["favorite-planets"] });
    },
  });

  const collectionMutation = useMutation({
    mutationFn: (collectionId: number) => api.addCollectionItem(collectionId, "planet", slug),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["collections"] });
      setNote(`Saved to collection`);
    },
  });

  function onCompare() {
    if (!has && isFull) {
      setNote(`Comparison is full (${MAX_COMPARE} worlds).`);
      return;
    }
    toggle(slug);
  }

  const size = dense ? "sm" : "sm";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Button
        size={size}
        variant={has ? "primary" : "ghost"}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onCompare();
        }}
      >
        {has ? "In compare" : "Compare"}
      </Button>

      {signedIn ? (
        <Button
          size={size}
          variant={favourited ? "primary" : "ghost"}
          disabled={favoriteMutation.isPending}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            favoriteMutation.mutate();
          }}
        >
          {favourited ? "Favourited" : "Favourite"}
        </Button>
      ) : null}

      <ButtonLink size={size} variant="ghost" href={`/systems/${starSlug}`}>
        System
      </ButtonLink>
      <ButtonLink size={size} variant="ghost" href={`/simulator?baseline=${slug}`}>
        Simulate
      </ButtonLink>

      {signedIn && collections && collections.length > 0 ? (
        <label className="sr-only">
          Add {name} to a collection
          <select
            className="ml-1 h-8 rounded-lg bg-void-800 px-2 text-xs text-starlight-200"
            defaultValue=""
            onChange={(event) => {
              const id = Number(event.target.value);
              if (id) collectionMutation.mutate(id);
              event.target.value = "";
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <option value="">Collection…</option>
            {collections.map((collection) => (
              <option key={collection.id} value={collection.id}>
                {collection.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {note ? (
        <span className="text-[0.65rem] text-starlight-400" role="status">
          {note}
        </span>
      ) : null}
    </div>
  );
}
