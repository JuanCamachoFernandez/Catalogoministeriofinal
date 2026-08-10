import { useQuery } from "@tanstack/react-query";
import { FileDown, FileSpreadsheet, FileText, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { api, errorApi } from "../../../compartido";
import {
  CajaError,
  Campo,
  EstadoCarga,
  SelectorBuscable,
  useRetroalimentacion,
} from "../../../compartido/componentes";

type Option = { value: string; label: string };
type ReportOptions = {
  resources: Array<Option & { columns: Option[] }>;
  actions: string[];
  sectors: Option[];
  productive_units: Option[];
  departments: string[];
};

type Filters = Record<string, string>;

const RESOURCE_OPTIONS: Option[] = [
  { value: "general", label: "Reporte general" },
  { value: "solicitudes", label: "Solicitudes de registro" },
  { value: "unidades_productivas", label: "Unidades productivas" },
  { value: "sectores_productivos", label: "Sectores productivos" },
  { value: "productos", label: "Productos" },
  { value: "ferias", label: "Ferias y eventos" },
  { value: "administradores", label: "Administradores" },
  { value: "auditoria", label: "Auditoría" },
];

const STATUS_OPTIONS: Record<string, Option[]> = {
  solicitudes: [
    { value: "", label: "Todos los estados" },
    { value: "PENDING", label: "Pendientes" },
    { value: "APPROVED", label: "Aprobadas" },
    { value: "REJECTED", label: "Rechazadas" },
  ],
  unidades_productivas: [
    { value: "", label: "Todos los estados" },
    { value: "ACTIVE", label: "Activas" },
    { value: "INACTIVE", label: "Inactivas" },
  ],
  sectores_productivos: [
    { value: "", label: "Todos los estados" },
    { value: "ACTIVE", label: "Activos" },
    { value: "INACTIVE", label: "Inactivos" },
  ],
  productos: [
    { value: "", label: "Todos los estados" },
    { value: "DRAFT", label: "En preparación" },
    { value: "AVAILABLE", label: "Disponibles" },
    { value: "OUT_OF_STOCK", label: "Agotados" },
    { value: "RETIRED", label: "Retirados" },
  ],
  ferias: [
    { value: "", label: "Todos los estados" },
    { value: "DRAFT", label: "En preparación" },
    { value: "PUBLISHED", label: "Publicadas" },
    { value: "FINISHED", label: "Finalizadas" },
    { value: "DISABLED", label: "Canceladas" },
  ],
  administradores: [
    { value: "", label: "Todos los estados" },
    { value: "ACTIVE", label: "Activos" },
    { value: "INACTIVE", label: "Inactivos" },
    { value: "LOCKED", label: "Bloqueados" },
  ],
};

const PRESENCE_OPTIONS: Option[] = [
  { value: "", label: "Todos" },
  { value: "true", label: "Sí tiene" },
  { value: "false", label: "No tiene" },
];

const defaultFilters = (): Filters => ({});

const reportFilename = (label: string, format: "pdf" | "xlsx") => {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  const timestamp = [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("-") + `_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
  const filenameLabel = label.toLocaleLowerCase("es").startsWith("reporte ")
    ? label.slice("Reporte ".length)
    : label;
  const safeLabel = filenameLabel
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `Reporte_${safeLabel}_${timestamp}.${format}`;
};

export default function PaginaReportesAdministracion() {
  const [resource, setResource] = useState("general");
  const [format, setFormat] = useState<"pdf" | "xlsx">("pdf");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [downloading, setDownloading] = useState(false);
  const feedback = useRetroalimentacion();
  const optionsQuery = useQuery({
    queryKey: ["report-options"],
    queryFn: () => api.get<ReportOptions>("/reports/options").then((response) => response.data),
  });
  const options = optionsQuery.data;
  const selectedLabel = RESOURCE_OPTIONS.find((item) => item.value === resource)?.label ?? "Reporte";

  const setFilter = (name: string, value: string) =>
    setFilters((current) => ({ ...current, [name]: value }));

  const activeFilterCount = useMemo(
    () => Object.values(filters).filter(Boolean).length,
    [filters],
  );

  const download = async () => {
    setDownloading(true);
    try {
      const response = await api.get<Blob>(`/reports/${resource}`, {
        params: {
          format,
          ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== "")),
        },
        responseType: "blob",
      });
      const filename = reportFilename(selectedLabel, format);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      feedback.success("Reporte generado", `${selectedLabel} en ${format === "pdf" ? "PDF" : "Excel"}.`);
    } catch (error) {
      feedback.error("No se pudo generar el reporte", errorApi(error));
    } finally {
      setDownloading(false);
    }
  };

  if (optionsQuery.isLoading) return <EstadoCarga label="Preparando reportes..." />;
  if (optionsQuery.error) return <CajaError mensaje={errorApi(optionsQuery.error)} />;

  const statusOptions = STATUS_OPTIONS[resource];
  const organizationReport = ["solicitudes", "unidades_productivas"].includes(resource);

  return (
    <section className="admin-page reports-page">
      <header className="page-heading reports-heading">
        <div>
          <span className="eyebrow">Información institucional</span>
          <h1>Reportes</h1>
          <p>Seleccione el contenido, aplique los filtros necesarios y elija el formato de descarga.</p>
        </div>
        <span className="heading-icon"><FileDown /></span>
      </header>

      <div className="reports-workspace">
        <section className="reports-config-section">
          <div className="reports-section-heading">
            <span>01</span>
            <div><h2>Contenido del reporte</h2><p>El reporte general incluye todos los apartados.</p></div>
          </div>
          <SelectorBuscable
            value={resource}
            options={RESOURCE_OPTIONS}
            onChange={(value) => {
              setResource(value);
              setFilters(defaultFilters());
            }}
            searchable={false}
            placeholder="Seleccione un apartado"
            ariaLabel="Seleccionar contenido del reporte"
          />
        </section>

        <section className="reports-config-section reports-filter-section">
          <div className="reports-section-heading reports-filter-heading">
            <span>02</span>
            <div><h2>Filtros</h2><p>{resource === "general" ? "Se incluirán todos los registros disponibles." : "Deje los filtros en Todos para obtener el reporte completo."}</p></div>
            {activeFilterCount > 0 && (
              <button type="button" className="reports-clear-button" onClick={() => setFilters(defaultFilters())}>
                <RotateCcw size={16} /> Limpiar filtros
              </button>
            )}
          </div>

          <div className="reports-dynamic-filters" key={resource}>
            {resource === "general" ? (
              <div className="reports-general-message">
                <FileText aria-hidden="true" />
                <div><strong>Reporte consolidado</strong><span>Solicitudes, unidades, sectores, productos, ferias, administradores y auditoría.</span></div>
              </div>
            ) : (
              <>
                <Campo label="Búsqueda general">
                  <input className="input" value={filters.q ?? ""} onChange={(event) => setFilter("q", event.target.value)} placeholder="Nombre o palabra clave" />
                </Campo>

                {statusOptions && (
                  <Campo label="Estado">
                    <SelectorBuscable value={filters.status ?? ""} options={statusOptions} onChange={(value) => setFilter("status", value)} searchable={false} placeholder="Todos los estados" ariaLabel="Filtrar por estado" />
                  </Campo>
                )}

                {organizationReport && (
                  <>
                    <Campo label="Sector productivo">
                      <SelectorBuscable value={filters.sector_id ?? ""} options={[{ value: "", label: "Todos los sectores" }, ...(options?.sectors ?? [])]} onChange={(value) => setFilter("sector_id", value)} placeholder="Todos los sectores" searchPlaceholder="Buscar sector..." ariaLabel="Filtrar por sector" />
                    </Campo>
                    <Campo label="Departamento">
                      <SelectorBuscable value={filters.department ?? ""} options={[{ value: "", label: "Todos los departamentos" }, ...(options?.departments.map((item) => ({ value: item, label: item })) ?? [])]} onChange={(value) => setFilter("department", value)} placeholder="Todos los departamentos" searchPlaceholder="Buscar departamento..." ariaLabel="Filtrar por departamento" />
                    </Campo>
                    <Campo label="NIT">
                      <SelectorBuscable value={filters.has_nit ?? ""} options={PRESENCE_OPTIONS} onChange={(value) => setFilter("has_nit", value)} searchable={false} placeholder="Todos" ariaLabel="Filtrar por NIT" />
                    </Campo>
                    <Campo label="Registro SEPREC">
                      <SelectorBuscable value={filters.has_seprec ?? ""} options={PRESENCE_OPTIONS} onChange={(value) => setFilter("has_seprec", value)} searchable={false} placeholder="Todos" ariaLabel="Filtrar por SEPREC" />
                    </Campo>
                    <Campo label="Registro PRO-BOLIVIA">
                      <SelectorBuscable value={filters.has_pro_bolivia ?? ""} options={PRESENCE_OPTIONS} onChange={(value) => setFilter("has_pro_bolivia", value)} searchable={false} placeholder="Todos" ariaLabel="Filtrar por PRO-BOLIVIA" />
                    </Campo>
                    <Campo label="Redes sociales">
                      <SelectorBuscable value={filters.has_social ?? ""} options={PRESENCE_OPTIONS} onChange={(value) => setFilter("has_social", value)} searchable={false} placeholder="Todos" ariaLabel="Filtrar por redes sociales" />
                    </Campo>
                  </>
                )}

                {resource === "productos" && (
                  <>
                    <Campo label="Unidad productiva">
                      <SelectorBuscable value={filters.productive_unit_id ?? ""} options={[{ value: "", label: "Todas las unidades" }, ...(options?.productive_units ?? [])]} onChange={(value) => setFilter("productive_unit_id", value)} placeholder="Todas las unidades" searchPlaceholder="Buscar unidad..." ariaLabel="Filtrar por unidad productiva" />
                    </Campo>
                    <Campo label="Precio mínimo (Bs)"><input className="input" type="number" min="0" step="0.01" value={filters.price_min ?? ""} onChange={(event) => setFilter("price_min", event.target.value)} /></Campo>
                    <Campo label="Precio máximo (Bs)"><input className="input" type="number" min={filters.price_min || "0"} step="0.01" value={filters.price_max ?? ""} onChange={(event) => setFilter("price_max", event.target.value)} /></Campo>
                  </>
                )}

                {resource === "ferias" && (
                  <>
                    <Campo label="Lugar"><input className="input" value={filters.location ?? ""} onChange={(event) => setFilter("location", event.target.value)} placeholder="Lugar, dirección o departamento" /></Campo>
                    <Campo label="Desde"><input className="input" type="date" max={filters.date_to || undefined} value={filters.date_from ?? ""} onChange={(event) => setFilter("date_from", event.target.value)} /></Campo>
                    <Campo label="Hasta"><input className="input" type="date" min={filters.date_from || undefined} value={filters.date_to ?? ""} onChange={(event) => setFilter("date_to", event.target.value)} /></Campo>
                  </>
                )}

                {resource === "auditoria" && (
                  <>
                    <Campo label="Acción">
                      <SelectorBuscable value={filters.action ?? ""} options={[{ value: "", label: "Todas las acciones" }, ...(options?.actions.map((item) => ({ value: item, label: item.replaceAll("_", " ") })) ?? [])]} onChange={(value) => setFilter("action", value)} placeholder="Todas las acciones" searchPlaceholder="Buscar acción..." ariaLabel="Filtrar por acción" />
                    </Campo>
                    <Campo label="Desde"><input className="input" type="date" max={filters.date_to || undefined} value={filters.date_from ?? ""} onChange={(event) => setFilter("date_from", event.target.value)} /></Campo>
                    <Campo label="Hasta"><input className="input" type="date" min={filters.date_from || undefined} value={filters.date_to ?? ""} onChange={(event) => setFilter("date_to", event.target.value)} /></Campo>
                  </>
                )}
              </>
            )}
          </div>
        </section>

        <section className="reports-config-section reports-export-section">
          <div className="reports-section-heading">
            <span>03</span>
            <div><h2>Formato de descarga</h2><p>Ambos formatos incluyen la información filtrada.</p></div>
          </div>
          <div className="reports-format-control" role="group" aria-label="Formato del reporte">
            <button type="button" className={format === "pdf" ? "active" : ""} onClick={() => setFormat("pdf")}><FileText /> PDF</button>
            <button type="button" className={format === "xlsx" ? "active" : ""} onClick={() => setFormat("xlsx")}><FileSpreadsheet /> Excel</button>
          </div>
          <button type="button" className="reports-download-button" disabled={downloading} onClick={() => void download()}>
            <FileDown /> {downloading ? "Generando reporte..." : "Generar y descargar"}
          </button>
        </section>
      </div>
    </section>
  );
}
