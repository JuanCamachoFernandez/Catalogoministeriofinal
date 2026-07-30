import { lazy } from "react";

export const paginaDiferida = <
  T extends Record<string, unknown>,
  K extends keyof T,
>(
  loader: () => Promise<T>,
  key: K,
) =>
  lazy(() =>
    loader().then((module) => ({
      default: module[key] as React.ComponentType,
    })),
  );
