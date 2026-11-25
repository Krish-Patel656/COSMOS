"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/store/auth";

export function FavoriteStarButton({ slug }: { slug: string }) {
  const queryClient = useQueryClient();
  const signedIn = useAuth((state) => state.status) === "authenticated";

  const { data: favorites } = useQuery({
    queryKey: ["favorites"],
    queryFn: ({ signal }) => api.favorites(signal),
    enabled: signedIn,
  });

  const favourited = Boolean(
    favorites?.some((item) => item.target_type === "star" && item.target_slug === slug),
  );

  const mutation = useMutation({
    mutationFn: async () => {
      if (favourited) await api.removeFavorite("star", slug);
      else await api.addFavorite("star", slug);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
      await queryClient.invalidateQueries({ queryKey: ["favorite-stars"] });
    },
  });

  if (!signedIn) return null;

  return (
    <Button
      size="sm"
      variant={favourited ? "primary" : "secondary"}
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {favourited ? "Star saved" : "Save star"}
    </Button>
  );
}
