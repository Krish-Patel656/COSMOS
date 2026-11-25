import type { ReactNode } from "react";

import { clsx } from "@/lib/format";

export function PageShell({
  children,
  className,
  wide = false,
}: {
  children: ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <div
      className={clsx(
        "mx-auto w-full px-4 py-10 sm:px-6 lg:px-8",
        wide ? "max-w-[90rem]" : "max-w-7xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
