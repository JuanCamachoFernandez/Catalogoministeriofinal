import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, CircleHelp } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import {
  api,
  type CanonicalFair,
  type FairParticipation,
  type Paged,
  type ProductiveUnit,
} from "../../../compartido";
import {
  BarraPaginacion,
  CajaError,
  CampoBusqueda,
  EstadoCarga,
  EstadoVacio,
  InsigniaEstado,
  Modal,
  useElementosPaginacionAdaptable,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { datosPagina, mensaje } from "../utilidades/administracionCompartida";

export default function PaginaParticipacionesFeria() {
  const navigate = useNavigate();
  const { fairId = "" } = useParams();
  const [page, setPage] = useState(1);
  const [unitSearch, setUnitSearch] = useState("");
  const [showHelp, setShowHelp] = useState(false);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const qc = useQueryClient();
  const feedback = useRetroalimentacion();

  const fair = useQuery({
    queryKey: ["canonical-fair", fairId],
    queryFn: () =>
      api
        .get<CanonicalFair>(`/admin/fairs/${fairId}`)
        .then((response) => response.data),
    enabled: Boolean(fairId),
  });

  const list = useQuery({
    queryKey: ["fair-participations", fairId, page],
    queryFn: () =>
      api
        .get<Paged<FairParticipation>>(`/admin/fairs/${fairId}/participations`, {
          params: { page, per_page: 10 },
        })
        .then((response) => response.data),
    enabled: Boolean(fairId),
  });
  const assigned = useQuery({
    queryKey: ["fair-participations", fairId, "assigned-options"],
    queryFn: () =>
      api
        .get<Paged<FairParticipation>>(`/admin/fairs/${fairId}/participations`, {
          params: { per_page: 500 },
        })
        .then((response) => response.data.items),
    enabled: Boolean(fairId),
  });
  const participationData = datosPagina(list.data);
  const visibleParticipations = useElementosPaginacionAdaptable(
    participationData.items,
    participationData.pagination,
    fairId,
  );

  const units = useQuery({
    queryKey: ["productive-units", "options"],
    queryFn: () =>
      api
        .get<Paged<ProductiveUnit>>("/admin/productive-units", {
          params: { per_page: 100, estado: "ACTIVE" },
        })
        .then((response) => response.data.items),
  });

  const assignedUnitIds = new Set(
    (assigned.data ?? []).map((participation) => participation.productive_unit_id),
  );
  const availableUnits = (units.data ?? []).filter(
    (unit) => !assignedUnitIds.has(unit.id),
  );
  const normalizedUnitSearch = unitSearch.trim().toLocaleLowerCase("es");
  const suggestedUnits = normalizedUnitSearch
    ? availableUnits
        .filter((unit) =>
          unit.nombre_comercial.toLocaleLowerCase("es").includes(normalizedUnitSearch),
        )
        .slice(0, 8)
    : [];
  const listedUnits = normalizedUnitSearch
    ? availableUnits.filter((unit) =>
        unit.nombre_comercial.toLocaleLowerCase("es").includes(normalizedUnitSearch),
      )
    : availableUnits;
  const allFilteredSelected =
    listedUnits.length > 0 &&
    listedUnits.every((unit) => selectedUnitIds.includes(unit.id));

  const toggleUnitSelection = (unitId: string) => {
    setSelectedUnitIds((current) =>
      current.includes(unitId)
        ? current.filter((item) => item !== unitId)
        : [...current, unitId],
    );
  };

  const toggleSelectAllFiltered = () => {
    setSelectedUnitIds((current) => {
      if (allFilteredSelected) {
        const filteredIds = new Set(listedUnits.map((unit) => unit.id));
        return current.filter((item) => !filteredIds.has(item));
      }
      const next = new Set(current);
      listedUnits.forEach((unit) => next.add(unit.id));
      return Array.from(next);
    });
  };

  const act = async (path: string, successMessage: string) => {
    try {
      await api.post(path);
      await qc.invalidateQueries({
        queryKey: ["fair-participations", fairId],
      });
      await qc.invalidateQueries({
        queryKey: ["fair-participations", fairId, "assigned-options"],
      });
      setPage(1);
      feedback.success("Operación completada", successMessage);
    } catch (error) {
      feedback.error("No se pudo actualizar", mensaje(error));
    }
  };

  const assignUnits = async () => {
    if (!selectedUnitIds.length) return;
    try {
      const responses = await Promise.all(
        selectedUnitIds.map((productiveUnitId) =>
          api
            .post<FairParticipation>(`/admin/fairs/${fairId}/participations`, {
              productive_unit_id: productiveUnitId,
              observaciones: null,
            })
            .then((response) => response.data),
        ),
      );
      const authorizedCount = responses.filter(
        (response) => response.estado === "AUTHORIZED",
      ).length;
      setUnitSearch("");
      setSelectedUnitIds([]);
      setSelectorOpen(false);
      await qc.invalidateQueries({
        queryKey: ["fair-participations", fairId],
      });
      await qc.invalidateQueries({
        queryKey: ["fair-participations", fairId, "assigned-options"],
      });
      setPage(1);
      feedback.success(
        responses.length === 1
          ? authorizedCount === 1
            ? "Unidad asignada y autorizada"
            : "Unidad asignada"
          : "Unidades asignadas",
        responses.length === 1
          ? authorizedCount === 1
            ? "La unidad cumple las reglas de negocio y quedó autorizada automáticamente."
            : "La unidad fue agregada a la feria y quedó pendiente de autorización."
          : `${responses.length} unidades procesadas. ${authorizedCount} quedaron autorizadas automáticamente.`,
      );
    } catch (error) {
      feedback.error("No se pudieron asignar las unidades", mensaje(error));
    }
  };

  if (fair.isLoading) return <EstadoCarga />;
  if (fair.error || !fair.data) {
    return <CajaError mensaje={mensaje(fair.error ?? "Feria no encontrada")} />;
  }

  return (
    <section className="admin-unit-registration-page">
      <button
        type="button"
        className="back-navigation"
        onClick={() => navigate("/admin/ferias")}
      >
        {"←"} Volver al listado
      </button>

      <div className="registration-intro">
        <div className="fair-participation-intro">
          <div>
          <span className="eyebrow">Participaciones</span>
          <h1>{fair.data.nombre}</h1>
          <p>
            Al agregar una Unidad Productiva, sus productos disponibles para la
            feria se incluirán automáticamente.
          </p>
          </div>
          <button
            type="button"
            className="fair-participation-help-button"
            onClick={() => setShowHelp(true)}
          >
            <CircleHelp size={18} />
            Cómo funciona
          </button>
        </div>
      </div>

      <section className="admin-page">
        <div className="toolbar admin-requests-toolbar admin-fairs-toolbar fair-participation-toolbar">
          <div className="fair-participation-search">
            <CampoBusqueda
              value={unitSearch}
              onChange={(value) => {
                setUnitSearch(value);
              }}
              placeholder="Buscar unidad productiva por nombre..."
            />
            {normalizedUnitSearch ? (
              <div className="fair-participation-suggestions" role="listbox">
                {suggestedUnits.length ? (
                  suggestedUnits.map((unit) => (
                    <button
                      key={unit.id}
                      type="button"
                      className="fair-participation-suggestion"
                      onClick={() => toggleUnitSelection(unit.id)}
                    >
                      <span>{unit.nombre_comercial}</span>
                      <strong>
                        {selectedUnitIds.includes(unit.id) ? "Seleccionada" : "Seleccionar"}
                      </strong>
                    </button>
                  ))
                ) : (
                  <p className="fair-participation-empty">
                    No hay unidades disponibles con ese nombre.
                  </p>
                )}
              </div>
            ) : null}
          </div>
          <div
            className={`admin-sector-filter fair-participation-selector ${selectorOpen ? "is-open" : ""}`}
          >
            <button
              type="button"
              className="admin-sector-filter-trigger"
              onClick={() => setSelectorOpen((current) => !current)}
              aria-expanded={selectorOpen}
              aria-haspopup="listbox"
            >
              <span>
                {selectedUnitIds.length
                  ? `${selectedUnitIds.length} unidad(es) seleccionada(s)`
                  : "Seleccionar unidades"}
              </span>
              <ChevronDown size={18} />
            </button>
            {selectorOpen ? (
              <div className="admin-sector-filter-menu" role="listbox">
                <div className="admin-sector-filter-actions">
                  <button
                    type="button"
                    disabled={!listedUnits.length}
                    onClick={toggleSelectAllFiltered}
                  >
                    {allFilteredSelected ? "Quitar selección" : "Seleccionar todo"}
                  </button>
                </div>
                <div className="admin-sector-filter-options">
                  {listedUnits.length ? (
                    listedUnits.map((unit) => (
                      <label key={unit.id}>
                        <input
                          type="checkbox"
                          checked={selectedUnitIds.includes(unit.id)}
                          onChange={() => toggleUnitSelection(unit.id)}
                        />
                        <span>{unit.nombre_comercial}</span>
                      </label>
                    ))
                  ) : (
                    <p className="admin-sector-filter-empty">
                      No hay unidades disponibles con ese filtro.
                    </p>
                  )}
                </div>
              </div>
            ) : null}
          </div>
          <button
            className="admin-units-create-button"
            disabled={!selectedUnitIds.length}
            onClick={() => void assignUnits()}
          >
            {selectedUnitIds.length > 1 ? "Asignar unidades" : "Asignar unidad"}
          </button>
        </div>

{list.isLoading && !visibleParticipations.length ? (
          <EstadoCarga />
        ) : list.error ? (
          <CajaError mensaje={mensaje(list.error)} />
        ) : visibleParticipations.length ? (
          <>
            <div className="table-wrap admin-requests-table">
              <table>
                <thead>
                  <tr>
                    <th>Unidad Productiva</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleParticipations.map((participation) => (
                    <tr key={participation.id}>
                      <td>{participation.nombre_comercial}</td>
                      <td>
                        <InsigniaEstado value={participation.estado} />
                      </td>
                      <td>
                        <div className="admin-admins-actions">
                          {participation.estado === "PENDING" ? (
                            <button
                              className="btn-small admin-fair-action-manage"
                              onClick={() =>
                                void act(
                                  `/admin/fairs/${fairId}/participations/${participation.id}/authorize`,
                                  "La participación fue autorizada correctamente.",
                                )
                              }
                            >
                              Autorizar
                            </button>
                          ) : null}
                          {participation.estado === "PENDING" ||
                          participation.estado === "AUTHORIZED" ? (
                            <button
                              className="btn-small"
                              onClick={() =>
                                void act(
                                  `/admin/fairs/${fairId}/participations/${participation.id}/revoke`,
                                  "La participación fue retirada correctamente.",
                                )
                              }
                            >
                              Retirar
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <BarraPaginacion
              pagination={participationData.pagination}
              onPageChange={setPage}
              mobileLabel="Ver más participaciones"
            />
          </>
        ) : (
          <EstadoVacio title="Sin participaciones" />
        )}
      </section>

      {showHelp ? (
        <Modal
          title="Cómo funciona la participación en ferias"
          className="admin-sector-modal"
          onClose={() => setShowHelp(false)}
        >
          <div className="admin-sector-modal-content fair-participation-help">
            <p className="admin-sector-modal-intro">
              Esta sección le ayuda a decidir qué unidades pueden ingresar a la feria y cuáles
              todavía deben quedar pendientes.
            </p>
            <ol className="fair-participation-help-list">
              <li>
                <strong>Busque, seleccione y asigne una Unidad Productiva.</strong>
                El buscador solo muestra unidades activas que todavía no fueron agregadas a esta
                feria.
              </li>
              <li>
                <strong>Si cumple las reglas, se autoriza automáticamente.</strong>
                La unidad debe estar activa y tener al menos 3 productos publicables.
              </li>
              <li>
                <strong>Si no cumple las reglas, queda pendiente.</strong>
                En ese caso podrá autorizarla más adelante, cuando ya tenga la información o los
                productos necesarios.
              </li>
            </ol>
            <div className="fair-participation-help-rules">
              <p><strong>Reglas clave</strong></p>
              <ul>
                <li>
                  <InsigniaEstado value="AUTHORIZED" /> la unidad se publica en la feria con sus
                  productos válidos.
                </li>
                <li>
                  <InsigniaEstado value="PENDING" /> la unidad fue agregada, pero todavía no
                  aparece en la feria.
                </li>
                <li>
                  <InsigniaEstado value="REVOKED" /> la unidad fue retirada y deja de mostrarse en
                  la feria.
                </li>
              </ul>
            </div>
            <div className="modal-actions admin-sector-modal-actions">
              <button type="button" className="admin-unit-action-button" onClick={() => setShowHelp(false)}>
                Entendido
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </section>
  );
}
