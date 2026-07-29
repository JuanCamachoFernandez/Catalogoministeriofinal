import { ChevronDown, LogIn, Store, UserPlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { InstitutionalSeal } from "./Layouts";

export function PublicHeader() {
  const [accessOpen, setAccessOpen] = useState(false);
  const accessMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!accessOpen) return;
    const closeOnOutside = (event: PointerEvent) => {
      if (!accessMenuRef.current?.contains(event.target as Node)) {
        setAccessOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccessOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accessOpen]);

  return (
    <header className="public-header">
      <div className="container public-header-content">
        <Link
          to="/catalogo"
          className="brand"
          aria-label="Ferias Productivas Bolivia"
        >
          <Store aria-hidden="true" />
          <span>Ferias Productivas Bolivia</span>
        </Link>
        <Link
          to="/catalogo"
          className="header-seal-link"
          aria-label="Ir al catálogo"
        >
          <InstitutionalSeal className="header-seal" />
        </Link>
        <nav className="public-actions" aria-label="Acceso">
          <div className="access-menu" ref={accessMenuRef}>
            <button
              type="button"
              className="public-action public-action-login"
              aria-expanded={accessOpen}
              aria-haspopup="menu"
              onClick={() => setAccessOpen((open) => !open)}
            >
              <LogIn aria-hidden="true" />
              <span>Ingresar</span>
              <ChevronDown className="access-chevron" aria-hidden="true" />
            </button>
            {accessOpen && (
              <div className="access-dropdown" role="menu">
                <Link
                  to="/login"
                  role="menuitem"
                  onClick={() => setAccessOpen(false)}
                >
                  <LogIn aria-hidden="true" />
                  <span>
                    <strong>Iniciar sesión</strong>
                    <small>Acceder a su cuenta</small>
                  </span>
                </Link>
                <Link
                  to="/solicitud-registro"
                  role="menuitem"
                  onClick={() => setAccessOpen(false)}
                >
                  <UserPlus aria-hidden="true" />
                  <span>
                    <strong>Registrarse</strong>
                    <small>Registrar una Unidad Productiva</small>
                  </span>
                </Link>
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}
