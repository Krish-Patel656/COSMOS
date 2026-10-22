/**
 * Typed client for the COSMOS API.
 *
 * Requests go to `/api/backend/*` on the Next origin, which `next.config.ts`
 * rewrites to the FastAPI service. That keeps the browser same-origin (no CORS
 * preflights) and means the backend host is configured in one place.
 */

import type {
  CatalogueStats,
  Collection,
  ComparisonResponse,
  Favorite,
  FavoriteTargetType,
  HighlightsResponse,
  PlanetDetail,
  PlanetFilters,
  PlanetPage,
  PlanetWithStar,
  SavedComparison,
  SearchResponse,
  SimulationPreset,
  SimulationRequest,
  SimulationResponse,
  StarMapPoint,
  StarPage,
  StarSummary,
  SystemDetail,
  TokenPair,
  User,
} from "./types";

const BROWSER_BASE = "/api/backend";
/** Server components bypass the rewrite and talk to the backend directly. */
const SERVER_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}/api/v1`;

export const ACCESS_TOKEN_KEY = "cosmos.access_token";
export const REFRESH_TOKEN_KEY = "cosmos.refresh_token";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

function baseUrl(): string {
  return typeof window === "undefined" ? SERVER_BASE : BROWSER_BASE;
}

function storedToken(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Private browsing modes can throw on localStorage access.
    return null;
  }
}

export function setTokens(tokens: Pick<TokenPair, "access_token" | "refresh_token">): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasStoredSession(): boolean {
  return storedToken(ACCESS_TOKEN_KEY) !== null;
}

/**
 * Serialise query parameters.
 *
 * Arrays become repeated keys (`?spectral_class=G&spectral_class=K`) because
 * that is what FastAPI's `List[str] = Query()` expects. Empty strings, nulls and
 * NaN are dropped so that a cleared filter input does not send `?min_radius=`
 * and trigger a 422.
 */
export function buildQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const entry of value) {
        if (entry !== undefined && entry !== null && entry !== "") {
          search.append(key, String(entry));
        }
      }
    } else if (typeof value === "number") {
      if (Number.isFinite(value)) search.append(key, String(value));
    } else if (typeof value === "boolean") {
      search.append(key, value ? "true" : "false");
    } else {
      search.append(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
  /** Next.js fetch cache revalidation window, in seconds, for server requests. */
  revalidate?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = false, signal, revalidate } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = storedToken(ACCESS_TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const init: RequestInit & { next?: { revalidate: number } } = {
    method,
    headers,
    signal,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
  if (revalidate !== undefined && typeof window === "undefined") {
    init.next = { revalidate };
  }

  const response = await fetch(`${baseUrl()}${path}`, init);

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? safeJson(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, extractMessage(payload, response.status), payload);
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Turn a FastAPI error body into a sentence.
 *
 * Validation failures arrive as an array of per-field objects; surfacing
 * `[object Object]` to a user is worse than useless, so those are flattened into
 * "field: message" pairs.
 */
function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            const location = Array.isArray((entry as { loc?: unknown[] }).loc)
              ? (entry as { loc: unknown[] }).loc.slice(1).join(".")
              : "";
            const message = String((entry as { msg: unknown }).msg);
            return location ? `${location}: ${message}` : message;
          }
          return String(entry);
        })
        .join("; ");
    }
  }
  return `Request failed with status ${status}`;
}

// --- Catalogue -------------------------------------------------------------

export const api = {
  stats: (signal?: AbortSignal) =>
    request<CatalogueStats>("/stats", { signal, revalidate: 600 }),

  search: (query: string, limit = 12, signal?: AbortSignal) =>
    request<SearchResponse>(`/search${buildQuery({ q: query, limit })}`, { signal }),

  highlights: (perSection = 8, signal?: AbortSignal) =>
    request<HighlightsResponse>(`/highlights${buildQuery({ per_section: perSection })}`, {
      signal,
      revalidate: 600,
    }),

  planets: (filters: PlanetFilters = {}, signal?: AbortSignal) =>
    request<PlanetPage>(`/planets${buildQuery(filters as Record<string, unknown>)}`, { signal }),

  planet: (slug: string, signal?: AbortSignal) =>
    request<PlanetDetail>(`/planets/${encodeURIComponent(slug)}`, { signal, revalidate: 3600 }),

  similarPlanets: (slug: string, limit = 6, signal?: AbortSignal) =>
    request<PlanetWithStar[]>(
      `/planets/${encodeURIComponent(slug)}/similar${buildQuery({ limit })}`,
      { signal, revalidate: 3600 },
    ),

  planetSiblings: (slug: string, signal?: AbortSignal) =>
    request<PlanetWithStar[]>(`/planets/${encodeURIComponent(slug)}/system`, {
      signal,
      revalidate: 3600,
    }),

  randomPlanet: (signal?: AbortSignal) =>
    request<PlanetWithStar>("/planets/random", { signal }),

  systems: (
    params: {
      q?: string;
      min_planets?: number;
      max_distance_ly?: number;
      spectral_class?: string[];
      sort?: "distance" | "planet_count" | "habitability" | "name";
      order?: "asc" | "desc";
      limit?: number;
      offset?: number;
    } = {},
    signal?: AbortSignal,
  ) => request<StarPage>(`/systems${buildQuery(params)}`, { signal }),

  system: (slug: string, signal?: AbortSignal) =>
    request<SystemDetail>(`/systems/${encodeURIComponent(slug)}`, { signal, revalidate: 3600 }),

  star: (slug: string, signal?: AbortSignal) =>
    request<StarSummary>(`/stars/${encodeURIComponent(slug)}`, { signal, revalidate: 3600 }),

  stellarMap: (
    params: {
      max_distance_ly?: number;
      limit?: number;
      require_planets?: boolean;
      sort_by?: "distance" | "habitability";
    } = {},
    signal?: AbortSignal,
  ) => request<StarMapPoint[]>(`/stars/map${buildQuery(params)}`, { signal, revalidate: 3600 }),

  compare: (slugs: string[], signal?: AbortSignal) =>
    request<ComparisonResponse>(`/compare${buildQuery({ slugs })}`, { signal }),

  simulate: (payload: SimulationRequest, signal?: AbortSignal) =>
    request<SimulationResponse>("/simulate", { method: "POST", body: payload, signal }),

  simulationPresets: (signal?: AbortSignal) =>
    request<{ presets: SimulationPreset[] }>("/simulate/presets", {
      signal,
      revalidate: 3600,
    }),

  // --- Auth ----------------------------------------------------------------

  register: (email: string, displayName: string, password: string) =>
    request<TokenPair>("/auth/register", {
      method: "POST",
      body: { email, display_name: displayName, password },
    }),

  login: (email: string, password: string) =>
    request<TokenPair>("/auth/login", { method: "POST", body: { email, password } }),

  refresh: (refreshToken: string) =>
    request<TokenPair>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),

  me: (signal?: AbortSignal) => request<User>("/auth/me", { auth: true, signal }),

  // --- Saved content -------------------------------------------------------

  favorites: (signal?: AbortSignal) =>
    request<Favorite[]>("/me/favorites", { auth: true, signal }),

  addFavorite: (targetType: FavoriteTargetType, targetSlug: string, note?: string) =>
    request<Favorite>("/me/favorites", {
      method: "POST",
      auth: true,
      body: { target_type: targetType, target_slug: targetSlug, note: note ?? null },
    }),

  removeFavorite: (targetType: FavoriteTargetType, targetSlug: string) =>
    request<void>(`/me/favorites/${targetType}/${encodeURIComponent(targetSlug)}`, {
      method: "DELETE",
      auth: true,
    }),

  favoritePlanets: (signal?: AbortSignal) =>
    request<PlanetWithStar[]>("/me/favorites/planets", { auth: true, signal }),

  favoriteStars: (signal?: AbortSignal) =>
    request<StarSummary[]>("/me/favorites/stars", { auth: true, signal }),

  collections: (signal?: AbortSignal) =>
    request<Collection[]>("/me/collections", { auth: true, signal }),

  createCollection: (name: string, description?: string, isPublic = false) =>
    request<Collection>("/me/collections", {
      method: "POST",
      auth: true,
      body: { name, description: description ?? null, is_public: isPublic },
    }),

  updateCollection: (
    id: number,
    patch: { name?: string; description?: string; is_public?: boolean },
  ) => request<Collection>(`/me/collections/${id}`, { method: "PATCH", auth: true, body: patch }),

  deleteCollection: (id: number) =>
    request<void>(`/me/collections/${id}`, { method: "DELETE", auth: true }),

  addCollectionItem: (
    id: number,
    targetType: FavoriteTargetType,
    targetSlug: string,
    note?: string,
  ) =>
    request<Collection>(`/me/collections/${id}/items`, {
      method: "POST",
      auth: true,
      body: { target_type: targetType, target_slug: targetSlug, note: note ?? null },
    }),

  removeCollectionItem: (id: number, itemId: number) =>
    request<Collection>(`/me/collections/${id}/items/${itemId}`, {
      method: "DELETE",
      auth: true,
    }),

  savedComparisons: (signal?: AbortSignal) =>
    request<SavedComparison[]>("/me/comparisons", { auth: true, signal }),

  saveComparison: (name: string, planetSlugs: string[]) =>
    request<SavedComparison>("/me/comparisons", {
      method: "POST",
      auth: true,
      body: { name, planet_slugs: planetSlugs },
    }),

  deleteComparison: (id: number) =>
    request<void>(`/me/comparisons/${id}`, { method: "DELETE", auth: true }),
};
