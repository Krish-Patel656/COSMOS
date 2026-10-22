"use client";

import { create } from "zustand";

import { ApiError, REFRESH_TOKEN_KEY, api, clearTokens, hasStoredSession, setTokens } from "../api";
import type { User } from "../types";

export type AuthStatus = "idle" | "loading" | "authenticated" | "anonymous";

interface AuthState {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, displayName: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

function readRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  status: "idle",
  error: null,

  /**
   * Restore a session from stored tokens on first load.
   *
   * Access tokens are short-lived, so an expired one is the normal case for a
   * returning user rather than an error: a 401 triggers one refresh attempt
   * before the session is treated as genuinely gone.
   */
  bootstrap: async () => {
    if (!hasStoredSession()) {
      set({ status: "anonymous", user: null });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await api.me();
      set({ user, status: "authenticated", error: null });
      return;
    } catch (error) {
      if (!(error instanceof ApiError) || !error.isUnauthorized) {
        set({ status: "anonymous", user: null });
        return;
      }
    }

    const refreshToken = readRefreshToken();
    if (!refreshToken) {
      clearTokens();
      set({ status: "anonymous", user: null });
      return;
    }

    try {
      const tokens = await api.refresh(refreshToken);
      setTokens(tokens);
      set({ user: tokens.user, status: "authenticated", error: null });
    } catch {
      clearTokens();
      set({ status: "anonymous", user: null });
    }
  },

  login: async (email, password) => {
    set({ status: "loading", error: null });
    try {
      const tokens = await api.login(email, password);
      setTokens(tokens);
      set({ user: tokens.user, status: "authenticated", error: null });
    } catch (error) {
      set({ status: "anonymous", user: null, error: describe(error) });
      throw error;
    }
  },

  register: async (email, displayName, password) => {
    set({ status: "loading", error: null });
    try {
      const tokens = await api.register(email, displayName, password);
      setTokens(tokens);
      set({ user: tokens.user, status: "authenticated", error: null });
    } catch (error) {
      set({ status: "anonymous", user: null, error: describe(error) });
      throw error;
    }
  },

  logout: () => {
    clearTokens();
    set({ user: null, status: "anonymous", error: null });
  },

  clearError: () => set({ error: null }),
}));
