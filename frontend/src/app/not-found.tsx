import { ButtonLink } from "@/components/ui/button";
import { PageShell } from "@/components/layout/page-shell";

export default function NotFound() {
  return (
    <PageShell>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-aurora-400">404</p>
      <h1 className="mt-2 font-display text-4xl text-starlight-50">This coordinate is empty</h1>
      <p className="mt-3 max-w-lg text-starlight-300">
        That star or planet is not in the loaded catalogue. It may be named differently in the NASA
        archive, or it may not have been ingested yet.
      </p>
      <div className="mt-6 flex gap-3">
        <ButtonLink href="/explore" variant="primary">
          Explorer
        </ButtonLink>
        <ButtonLink href="/map">Stellar map</ButtonLink>
      </div>
    </PageShell>
  );
}
