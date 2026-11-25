"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/store/auth";

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // The catalogue is a static snapshot between ingest runs, so aggressive
        // caching costs nothing in freshness and avoids refetching 6,000-planet
        // pages when the user navigates back.
        staleTime: 5 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // A 404 or a validation failure will not succeed on retry.
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  // Held in state so React's strict-mode double-invoke does not discard the
  // cache on the second render pass.
  const [queryClient] = useState(createQueryClient);
  const bootstrap = useAuth((state) => state.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
