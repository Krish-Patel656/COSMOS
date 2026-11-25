"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { ErrorNotice, Panel, SectionHeading } from "@/components/ui/primitives";
import { useAuth } from "@/lib/store/auth";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuth((state) => state.login);
  const error = useAuth((state) => state.error);
  const status = useAuth((state) => state.status);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await login(email, password);
      router.push("/account");
    } catch {
      // Error is stored on the auth slice.
    }
  }

  return (
    <PageShell className="max-w-md">
      <SectionHeading title="Sign in" description="Save favourites, collections and comparisons." />
      <Panel className="p-6">
        <form className="space-y-4" onSubmit={(event) => void onSubmit(event)}>
          {error ? <ErrorNotice message={error} /> : null}
          <label className="block text-sm">
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3"
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3"
            />
          </label>
          <Button type="submit" variant="primary" className="w-full" disabled={status === "loading"}>
            {status === "loading" ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-starlight-400">
          No account yet?{" "}
          <Link href="/register" className="text-aurora-300">
            Create one
          </Link>
        </p>
      </Panel>
    </PageShell>
  );
}
