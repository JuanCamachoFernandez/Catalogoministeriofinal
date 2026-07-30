import { useLayoutEffect, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { SelloInstitucional } from "../../../aplicacion/disenios/DisenioGestion";
import { EncabezadoPublico } from "./EncabezadoPublico";

function PublicFooter() {
  return (
    <footer className="public-footer">
      <div className="container public-footer-content">
        <SelloInstitucional className="footer-seal" />
        <div>
          <strong>Ferias Productivas Bolivia</strong>
          <p>
            Promoviendo la producción boliviana y el contacto directo con sus
            productores.
          </p>
        </div>
      </div>
    </footer>
  );
}

export function EstructuraPublica({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();

  useLayoutEffect(() => {
    const root = document.documentElement;
    const previousBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, 0);
    root.scrollTop = 0;
    document.body.scrollTop = 0;
    root.style.scrollBehavior = previousBehavior;
  }, [pathname]);

  return (
    <>
      <EncabezadoPublico />
      <main className="container public-main">{children}</main>
      <PublicFooter />
    </>
  );
}
