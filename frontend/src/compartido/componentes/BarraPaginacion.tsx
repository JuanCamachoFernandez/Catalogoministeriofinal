import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Pagination } from "../../compartido";

export function BarraPaginacion({
  pagination,
  onPage,
  onPageChange,
  mobileLabel = "Ver más resultados",
  scrollTargetId,
  scrollOnDesktop = true,
}: {
  pagination: Pagination;
  onPage?: (page: number) => void;
  onPageChange?: (page: number) => void;
  mobileLabel?: string;
  scrollTargetId?: string;
  scrollOnDesktop?: boolean;
}) {
  const changePage = onPage ?? onPageChange ?? (() => undefined);
  if (!pagination.total) return null;
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
    <div className="pagination" aria-label="Paginación">
      <span className="pagination-summary">
        Página {pagination.page} de {Math.max(1, pagination.pages)} ·{" "}
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
          {Array.from({ length: Math.max(1, pagination.pages) }, (_, index) => {
            const page = index + 1;
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
      {pagination.has_next && (
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


