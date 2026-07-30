import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { LimiteErrores } from "./LimiteErrores";
import { ProveedorAutenticacion } from "../../modulos/autenticacion/contexto/ContextoAutenticacion";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 30 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function ProveedoresAplicacion({ children }: { children: ReactNode }) {
  return (
    <LimiteErrores>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ProveedorAutenticacion>{children}</ProveedorAutenticacion>
        </BrowserRouter>
      </QueryClientProvider>
    </LimiteErrores>
  );
}
