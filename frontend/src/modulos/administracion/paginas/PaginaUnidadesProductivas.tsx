import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Eye, Plus, UserRoundCheck, UserRoundX } from "lucide-react";
import {
  api,
  type Paged,
  type ProductiveSector,
  type ProductiveUnit,
} from "../../../compartido";
import {
  EstadoVacio,
  CajaError,
  EstadoCarga,
  BarraPaginacion,
  CampoBusqueda,
  SelectorBuscable,
  InsigniaEstado,
  BotonConfirmacion,
  useElementosPaginacionAdaptable,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { FormularioDirectoUnidadProductiva } from "../componentes/FormularioDirectoUnidadProductiva";
import { PaginaDetalleUnidadProductiva } from "../componentes/PaginaDetalleUnidadProductiva";
import { mensaje, datosPagina } from "../utilidades/administracionCompartida";

const UNIT_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "ACTIVE", label: "Activas" },
  { value: "DISABLED", label: "Inhabilitadas" },
];

export default function PaginaUnidadesProductivas() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const [creating, setCreating] = useState(false);
  const [viewingId, setViewingId] = useState("");
  const [sectorIds, setSectorIds] = useState<string[]>([]);
  const [sectorMenuOpen, setSectorMenuOpen] = useState(false);
  const sectorMenuRef = useRef<HTMLDivElement | null>(null);
  const qc = useQueryClient();
  const feedback = useRetroalimentacion();
  const sectorFilter = useMemo(() => sectorIds.join(","), [sectorIds]);
  const deletedFilter =
    estado === "DISABLED" ? "true" : estado === "ACTIVE" ? "false" : undefined;
  const statusFilter = estado === "ACTIVE" ? "ACTIVE" : undefined;

  const sectors = useQuery({
    queryKey: ["productive-sectors", "active"],
    queryFn: () =>
      api
        .get<Paged<ProductiveSector>>("/productive-sectors", {
          params: { per_page: 100 },
        })
        .then((response) => response.data.items),
  });

  const list = useQuery({
    queryKey: ["productive-units", q, estado, sectorFilter, page],
    queryFn: () =>
      api
        .get<Paged<ProductiveUnit>>("/admin/productive-units", {
          params: {
            q: q || undefined,
            estado: statusFilter,
            sector_ids: sectorFilter || undefined,
            page,
            per_page: 10,
            include_deleted: deletedFilter ? undefined : true,
            deleted: deletedFilter,
          },
        })
        .then((response) => response.data),
  });

  const data = datosPagina(list.data);
  const displayedUnits = useElementosPaginacionAdaptable(
    data.items,
    data.pagination,
    `${q}|${estado}|${sectorFilter}`,
  );
  const selectedSectorLabel = useMemo(() => {
    if (!sectorIds.length) return "Todos los sectores";
    if (sectorIds.length === 1) {
      return (
        sectors.data?.find((item) => item.id === sectorIds[0])?.nombre ??
        "1 sector"
      );
    }
    return `${sectorIds.length} sectores`;
  }, [sectorIds, sectors.data]);

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => {
      if (!sectorMenuRef.current?.contains(event.target as Node)) {
        setSectorMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  const changeUnitState = async (
    item: ProductiveUnit,
    action: "disable" | "restore",
  ) => {
    try {
      if (action === "disable") {
        await api.delete(`/admin/productive-units/${item.id}`);
      } else {
        await api.post(`/admin/productive-units/${item.id}/restore`);
      }
      await qc.invalidateQueries({ queryKey: ["productive-units"] });
      feedback.success(
        "Operación completada",
        action === "disable"
          ? "La unidad productiva fue inhabilitada correctamente."
          : "La unidad productiva fue restaurada correctamente.",
      );
    } catch (error) {
      feedback.error("No se pudo actualizar", mensaje(error));
    }
  };

  if (creating) {
    return (
      <section className="admin-unit-registration-page">
        <button
          type="button"
          className="back-navigation"
          onClick={() => setCreating(false)}
        >
          ← Volver al listado
        </button>
        <div className="registration-intro">
          <div>
            <span className="eyebrow">Registrar Unidad Productiva</span>
            <h1>Nueva Unidad Productiva</h1>
          </div>
        </div>
        <FormularioDirectoUnidadProductiva
          onClose={() => setCreating(false)}
          onCreated={async () => {
            await qc.invalidateQueries({ queryKey: ["productive-units"] });
            setCreating(false);
          }}
        />
      </section>
    );
  }

  if (viewingId) {
    return (
      <PaginaDetalleUnidadProductiva
        unitId={viewingId}
        onBack={() => setViewingId("")}
        onChanged={() =>
          qc.invalidateQueries({ queryKey: ["productive-units"] })
        }
      />
    );
  }

  return (
    <section className="admin-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Directorio</span>
          <h1>Unidades Productivas</h1>
        </div>
        <button
          className="admin-units-create-button"
          onClick={() => setCreating(true)}
        >
          <Plus aria-hidden="true" />
          Registrar Unidad
        </button>
      </div>
      <div className="toolbar admin-units-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar Unidad Productiva..."
        />
        <SelectorBuscable
          value={estado}
          options={UNIT_STATUS_OPTIONS}
          onChange={(value) => {
            setEstado(value);
            setPage(1);
          }}
          placeholder="Todos los estados"
          searchPlaceholder="Buscar estado..."
          ariaLabel="Filtrar por estado"
        />
        <div
          className={`admin-sector-filter ${sectorMenuOpen ? "is-open" : ""}`}
          ref={sectorMenuRef}
        >
          <button
            type="button"
            className="admin-sector-filter-trigger"
            aria-expanded={sectorMenuOpen}
            aria-label="Filtrar por sectores"
            onClick={() => setSectorMenuOpen((current) => !current)}
          >
            <span>{selectedSectorLabel}</span>
            <ChevronDown size={18} />
          </button>
          {sectorMenuOpen && (
            <div className="admin-sector-filter-menu">
              {sectors.isLoading ? (
                <p className="admin-sector-filter-empty">Cargando sectores...</p>
              ) : sectors.error ? (
                <p className="admin-sector-filter-empty">
                  No se pudieron cargar los sectores.
                </p>
              ) : (
                <>
                  <div className="admin-sector-filter-actions">
                    <button
                      type="button"
                      onClick={() => {
                        setSectorIds([]);
                        setPage(1);
                      }}
                    >
                      Limpiar
                    </button>
                  </div>
                  <div className="admin-sector-filter-options">
                    {sectors.data?.map((sector) => (
                      <label key={sector.id}>
                        <input
                          type="checkbox"
                          checked={sectorIds.includes(sector.id)}
                          onChange={() => {
                            setSectorIds((current) =>
                              current.includes(sector.id)
                                ? current.filter((id) => id !== sector.id)
                                : [...current, sector.id],
                            );
                            setPage(1);
                          }}
                        />
                        <span>{sector.nombre}</span>
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
      {list.isLoading && !displayedUnits.length ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : displayedUnits.length ? (
        <>
          <div className="table-wrap admin-requests-table admin-units-table">
            <table>
              <thead>
                <tr>
                  <th>Unidad Productiva</th>
                  <th>Representante</th>
                  <th>Departamento</th>
                  <th>Correo</th>
                  <th>Teléfono</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {displayedUnits.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.nombre_comercial}</strong>
                    </td>
                    <td>{item.nombre_representante}</td>
                    <td>{item.departamento}</td>
                    <td>{item.correo_electronico}</td>
                    <td>{item.telefono_whatsapp}</td>
                    <td>
                      <InsigniaEstado
                        value={item.deleted_at ? "LOGICALLY_DELETED" : item.estado}
                      />
                    </td>
                    <td>
                      <div className="admin-admins-actions">
                        <button
                          type="button"
                          className="btn-small"
                          onClick={() => setViewingId(item.id)}
                          aria-label={`Ver ${item.nombre_comercial}`}
                          title="Ver"
                        >
                          <Eye size={16} />
                        </button>
                        <BotonConfirmacion
                          className="btn-small admin-sector-action-disable"
                          question="La unidad productiva y su cuenta quedarán inhabilitadas hasta que las restaures."
                          confirmLabel="Inhabilitar"
                          onConfirm={() => {
                            void changeUnitState(item, "disable");
                          }}
                          title="Inhabilitar"
                          aria-label={`Inhabilitar ${item.nombre_comercial}`}
                          disabled={Boolean(item.deleted_at)}
                        >
                          <UserRoundX size={16} />
                        </BotonConfirmacion>
                        <button
                          type="button"
                          className="btn-small admin-sector-action-enable"
                          disabled={!item.deleted_at}
                          aria-label={`Restaurar ${item.nombre_comercial}`}
                          title={
                            item.deleted_at
                              ? "Restaura la unidad productiva y reactiva su cuenta asociada."
                              : "Restaurar solo aplica a unidades inhabilitadas."
                          }
                          onClick={() => {
                            void changeUnitState(item, "restore");
                          }}
                        >
                          <UserRoundCheck size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <BarraPaginacion pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <EstadoVacio title="No hay Unidades Productivas" />
      )}
    </section>
  );
}
