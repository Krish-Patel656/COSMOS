"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** The comparison endpoint accepts two to four planets. */
export const MAX_COMPARE = 4;

interface CompareState {
  slugs: string[];
  toggle: (slug: string) => void;
  add: (slug: string) => boolean;
  remove: (slug: string) => void;
  clear: () => void;
  replace: (slugs: string[]) => void;
  has: (slug: string) => boolean;
  isFull: () => boolean;
}

export const useCompare = create<CompareState>()(
  persist(
    (set, get) => ({
      slugs: [],

      toggle: (slug) => {
        const { slugs } = get();
        if (slugs.includes(slug)) {
          set({ slugs: slugs.filter((entry) => entry !== slug) });
        } else if (slugs.length < MAX_COMPARE) {
          set({ slugs: [...slugs, slug] });
        }
      },

      add: (slug) => {
        const { slugs } = get();
        if (slugs.includes(slug)) return true;
        if (slugs.length >= MAX_COMPARE) return false;
        set({ slugs: [...slugs, slug] });
        return true;
      },

      remove: (slug) => set({ slugs: get().slugs.filter((entry) => entry !== slug) }),
      clear: () => set({ slugs: [] }),
      replace: (slugs) => set({ slugs: slugs.slice(0, MAX_COMPARE) }),
      has: (slug) => get().slugs.includes(slug),
      isFull: () => get().slugs.length >= MAX_COMPARE,
    }),
    { name: "cosmos.compare", version: 1 },
  ),
);
