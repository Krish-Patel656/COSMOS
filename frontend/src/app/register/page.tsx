"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { ErrorNotice, Panel, SectionHeading } from "@/components/ui/primitives";
import { useAuth } from "@/lib/store/auth";

export default function RegisterPage() {
  const router = useRouter();
  const register = useAuth((state) => state.register);
  const error = useAuth((state) => state.error);
  const status = useAuth((state) => state.status);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await register(email, displayName, password);
      router.push("/account");
    } catch {
      // Error is stored on the auth slice.
    }
  }

  return (
    <PageShell className="max-w-md">
      <SectionHeading
        title="Create an account"
        description="Favourites and collections stay on this device’s API database."
      />
      <Panel className="p-6">
        <form className="space-y-4" onSubmit={(event) => void onSubmit(event)}>
          {error ? <ErrorNotice message={error} /> : null}
          <label className="block text-sm">
            Display name
            <input
              required
              minLength={2}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3"
            />
          </label>
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
              minLength={10}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-void-700 bg-void-900 px-3"
            />
            <span className="mt-1 block text-xs text-starlight-500">
              At least 10 characters, mixing two of: lower, upper, digits, symbols.
            </span>
          </label>
          <Button type="submit" variant="primary" className="w-full" disabled={status === "loading"}>
            {status === "loading" ? "Creating…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-starlight-400">
          Already registered?{" "}
          <Link href="/login" className="text-aurora-300">
            Sign in
          </Link>
        </p>
      </Panel>
    </PageShell>
  );
}
