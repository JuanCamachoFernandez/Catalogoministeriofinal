import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Pagination } from "../../compartido";

const PAGINAS_POR_BLOQUE = 5;

type ElementoPaginacion = number | "ellipsis-start" | "ellipsis-end";

function obtenerPaginasVisibles(
  paginaActual: number,
  totalPaginas: number,
): ElementoPaginacion[] {
  const totalSeguro = Math.max(1, totalPaginas);
  const paginaSegura = Math.min(Math.max(1, paginaActual), totalSeguro);
  const mitadBloque = Math.floor(PAGINAS_POR_BLOQUE / 2);
  let inicioVisible = Math.max(1, paginaSegura - mitadBloque);
  let finVisible = Math.min(
    totalSeguro,
    inicioVisible + PAGINAS_POR_BLOQUE - 1,
  );

  inicioVisible = Math.max(1, finVisible - PAGINAS_POR_BLOQUE + 1);
  finVisible = Math.min(
    totalSeguro,
    inicioVisible + PAGINAS_POR_BLOQUE - 1,
  );
  const elementos: ElementoPaginacion[] = [];

  if (inicioVisible > 1) {
    elementos.push(1);
    if (inicioVisible > 2) elementos.push("ellipsis-start");
  }

  for (let page = inicioVisible; page <= finVisible; page += 1) {
    elementos.push(page);
  }

  if (finVisible < totalSeguro) {
    if (finVisible < totalSeguro - 1) elementos.push("ellipsis-end");
    elementos.push(totalSeguro);
  }

  return elementos;
}

export function BarraPaginacion({
  pagination,
  onPage,
  onPageChange,
  mobileLabel = "Ver más resultados",
  scrollTargetId,
  scrollOnDesktop = true,
  mobileCompact = true,
}: {
  pagination: Pagination;
  onPage?: (page: number) => void;
  onPageChange?: (page: number) => void;
  mobileLabel?: string;
  scrollTargetId?: string;
  scrollOnDesktop?: boolean;
  mobileCompact?: boolean;
}) {
  const changePage = onPage ?? onPageChange ?? (() => undefined);

  if (!pagination.total) return null;

  const totalPaginas = Math.max(1, pagination.pages);
  const paginasVisibles = obtenerPaginasVisibles(
    pagination.page,
    totalPaginas,
  );

  const selectDesktopPage = (page: number) => {
    changePage(page);
    if (
      scrollOnDesktop &&
      !navigator.userAgent.toLowerCase().includes("jsdom")
    ) {
      window.requestAnimationFrame(() => {
        const target = scrollTargetId
          ? document.getElementById(scrollTargetId)
          : null;
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        else window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
  };

  return (
    <div
      className={`pagination${mobileCompact ? "" : " pagination-full-mobile"}`}
      aria-label="Paginación"
    >
      <span className="pagination-summary">
        Página {pagination.page} de {totalPaginas} ·{" "}
        {pagination.total} registros
      </span>
      <div className="pagination-desktop-controls">
        <button
          className="btn-outline pagination-arrow"
          disabled={!pagination.has_prev}
          onClick={() => selectDesktopPage(pagination.page - 1)}
          aria-label="Página anterior"
        >
          <ChevronLeft size={18} />
        </button>
        <div className="pagination-pages" aria-label="Páginas disponibles">
          {paginasVisibles.map((elemento) => {
            if (typeof elemento !== "number") {
              return (
                <span
                  className="pagination-ellipsis"
                  key={elemento}
                  aria-hidden="true"
                >
                  …
                </span>
              );
            }

            const page = elemento;
            return (
              <button
                className={`pagination-page${page === pagination.page ? " active" : ""}`}
                key={page}
                disabled={page === pagination.page}
                onClick={() => selectDesktopPage(page)}
                aria-label={`Ir a la página ${page}`}
                aria-current={page === pagination.page ? "page" : undefined}
              >
                {page}
              </button>
            );
          })}
        </div>
        <button
          className="btn-outline pagination-arrow"
          disabled={!pagination.has_next}
          onClick={() => selectDesktopPage(pagination.page + 1)}
          aria-label="Página siguiente"
        >
          <ChevronRight size={18} />
        </button>
      </div>
      {mobileCompact && pagination.has_next && (
        <button
          className="btn pagination-mobile-more"
          onClick={(event) => {
            event.currentTarget.blur();
            changePage(pagination.page + 1);
          }}
        >
          {mobileLabel}
        </button>
      )}
    </div>
  );
}
