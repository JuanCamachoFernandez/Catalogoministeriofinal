import { useEffect, useMemo, useState } from "react";
import { type Pagination, type ProductiveUnitFairParticipation } from "../api";
import { Empty, PaginationBar, SearchField, StatusBadge } from "../ui";

const PARTICIPATIONS_PER_PAGE = 5;

const formatDate = (value?: string | null) => {
  if (!value) return "No registrado";
  const parsed = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(parsed);
};

export function ProductiveUnitParticipationsSection({
  participations,
}: {
  participations: ProductiveUnitFairParticipation[];
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filteredParticipations = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("es");
    if (!normalized) return participations;
    return participations.filter((item) =>
      [item.nombre_feria, item.ubicacion, item.departamento]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(normalized),
    );
  }, [participations, query]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredParticipations.length / PARTICIPATIONS_PER_PAGE),
  );
  const safePage = Math.min(page, totalPages);
  const startIndex = (safePage - 1) * PARTICIPATIONS_PER_PAGE;
  const visibleParticipations = filteredParticipations.slice(
    startIndex,
    startIndex + PARTICIPATIONS_PER_PAGE,
  );

  useEffect(() => {
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pagination: Pagination = {
    page: safePage,
    per_page: PARTICIPATIONS_PER_PAGE,
    pages: totalPages,
    total: filteredParticipations.length,
    has_prev: safePage > 1,
    has_next: safePage < totalPages,
  };

  return (
    <section className="admin-unit-detail-section">
      <div className="admin-unit-detail-section-heading">
        <div>
          <h3>Participación en ferias</h3>
          <p>Historial de participación de la unidad productiva.</p>
        </div>
      </div>

      {participations.length ? (
        <>
          <div className="admin-unit-products-toolbar">
            <SearchField
              value={query}
              onChange={setQuery}
              placeholder="Buscar feria o ubicación..."
            />
          </div>

          {visibleParticipations.length ? (
            <div className="table-wrap admin-requests-table admin-unit-fairs-table">
              <table>
                <thead>
                  <tr>
                    <th>Feria</th>
                    <th>Ubicación</th>
                    <th>Fechas</th>
                    <th>Participación</th>
                    <th>Estado de feria</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleParticipations.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.nombre_feria}</strong>
                        {item.observaciones && <small>{item.observaciones}</small>}
                      </td>
                      <td>
                        {item.ubicacion}
                        <small>{item.departamento}</small>
                      </td>
                      <td>
                        {formatDate(item.fecha_inicio)}
                        <small>al {formatDate(item.fecha_fin)}</small>
                      </td>
                      <td>
                        <StatusBadge value={item.estado} />
                      </td>
                      <td>
                        <StatusBadge value={item.estado_feria} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="No se encontraron participaciones"
              description="Pruebe con otra búsqueda."
            />
          )}

          <PaginationBar pagination={pagination} onPageChange={setPage} />
        </>
      ) : (
        <Empty title="Sin participaciones" />
      )}
    </section>
  );
}
