import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  FileDown,
  FileSpreadsheet,
  FileText,
  RotateCcw,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorApi } from "../../../compartido";
import {
  CajaError,
  Campo,
  EstadoCarga,
  SelectorBuscable,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { etiquetaAccionAuditoria } from "../../../compartido/utilidades/etiquetasAuditoria";

type Option = { value: string; label: string };
type ReportOptions = {
  resources: Array<Option & { columns: Option[] }>;
  actions: string[];
  sectors: Option[];
  productive_units: Option[];
  fair_locations: Option[];
  departments: string[];
};

type Filters = Record<string, string | string[]>;

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

const activeFilterWeight = (value: string | string[]) => {
  if (Array.isArray(value)) return value.length ? 1 : 0;
  return value.trim() ? 1 : 0;
};

function SelectorMultipleReportes({
  value,
  options,
  onChange,
  allLabel,
  searchPlaceholder,
  ariaLabel,
}: {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  allLabel: string;
  searchPlaceholder: string;
  ariaLabel: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const storedValues = value.split(",").filter(Boolean);
  const selected = new Set(storedValues);
  const allSelected = !storedValues.length;
  const normalizedQuery = query.trim().toLocaleLowerCase("es");
  const filteredOptions = options.filter((option) =>
    option.label.toLocaleLowerCase("es").includes(normalizedQuery),
  );
  const selectedLabels = storedValues
    .map(
      (selectedValue) =>
        options.find((option) => option.value === selectedValue)?.label,
    )
    .filter(Boolean) as string[];
  const summary = !storedValues.length ? allLabel : selectedLabels.join(", ");

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  const toggleOption = (optionValue: string) => {
    const next = selected.has(optionValue)
      ? storedValues.filter((item) => item !== optionValue)
      : [...storedValues, optionValue];
    onChange(
      !next.length || next.length === options.length ? "" : next.join(","),
    );
  };

  return (
    <div className={`reports-multiselect ${open ? "is-open" : ""}`} ref={root}>
      <button
        type="button"
        className="reports-multiselect-trigger"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => {
          setOpen((current) => !current);
          if (!open) setTimeout(() => searchInput.current?.focus(), 0);
        }}
      >
        <span title={summary}>{summary}</span>
        <ChevronDown size={18} />
      </button>
      {open && (
        <div className="reports-multiselect-menu">
          <label className="reports-multiselect-search">
            <Search size={17} />
            <input
              ref={searchInput}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={searchPlaceholder}
            />
          </label>
          <div
            className="reports-multiselect-options"
            role="listbox"
            aria-multiselectable="true"
          >
            <button
              type="button"
              className="reports-multiselect-option select-all"
              onClick={() => onChange("")}
            >
              <input
                type="checkbox"
                checked={allSelected}
                readOnly
                tabIndex={-1}
              />
              <span>{allLabel}</span>
            </button>
            {filteredOptions.map((option) => (
              <button
                type="button"
                role="option"
                aria-selected={selected.has(option.value)}
                className="reports-multiselect-option"
                key={option.value}
                onClick={() => toggleOption(option.value)}
              >
                <input
                  type="checkbox"
                  checked={selected.has(option.value)}
                  readOnly
                  tabIndex={-1}
                />
                <span>{option.label}</span>
              </button>
            ))}
            {!filteredOptions.length && (
              <p className="reports-multiselect-empty">No hay coincidencias</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const reportFilename = (label: string, format: "pdf" | "xlsx") => {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  const timestamp =
    [now.getFullYear(), pad(now.getMonth() + 1), pad(now.getDate())].join("-") +
    `_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
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
  const [actionMenuOpen, setActionMenuOpen] = useState(false);
  const actionMenuRef = useRef<HTMLDivElement>(null);
  const feedback = useRetroalimentacion();
  const optionsQuery = useQuery({
    queryKey: ["report-options"],
    queryFn: () =>
      api
        .get<ReportOptions>("/reports/options")
        .then((response) => response.data),
  });
  const options = optionsQuery.data;
  const selectedLabel =
    RESOURCE_OPTIONS.find((item) => item.value === resource)?.label ??
    "Reporte";

  const auditActionOptions = useMemo(
    () =>
      (options?.actions ?? []).map((item) => ({
        value: item,
        label: etiquetaAccionAuditoria(item),
      })),
    [options?.actions],
  );

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => {
      if (!actionMenuRef.current?.contains(event.target as Node)) {
        setActionMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  const setFilter = (name: string, value: string | string[]) =>
    setFilters((current) => ({ ...current, [name]: value }));

  const activeFilterCount = useMemo(
    () => Object.values(filters).reduce((count, value) => count + activeFilterWeight(value), 0),
    [filters],
  );
  const minimumPrice =
    filters.price_min === "" || filters.price_min === undefined
      ? null
      : Number(filters.price_min);
  const maximumPrice =
    filters.price_max === "" || filters.price_max === undefined
      ? null
      : Number(filters.price_max);
  const invalidPriceRange =
    minimumPrice !== null &&
    maximumPrice !== null &&
    minimumPrice > maximumPrice;
  const invalidFairDateRange =
    resource === "ferias" &&
    Boolean(filters.date_from) &&
    Boolean(filters.date_to) &&
    filters.date_to <= filters.date_from;

  const reportParams = useMemo(() => {
    const params: Record<string, string> = { format };
    for (const [name, value] of Object.entries(filters)) {
      if (Array.isArray(value)) {
        if (value.length) params[name] = value.join(",");
      } else if (value !== "") {
        params[name] = value;
      }
    }
    return params;
  }, [filters, format]);

  const download = async () => {
    if (invalidPriceRange) {
      feedback.error(
        "Revise el rango de precios",
        "El precio mínimo no puede ser mayor que el precio máximo.",
      );
      return;
    }
    if (invalidFairDateRange) {
      feedback.error(
        "Revise el rango de fechas",
        "La fecha final debe ser posterior a la fecha inicial.",
      );
      return;
    }
    setDownloading(true);
    try {
      const response = await api.get<Blob>(`/reports/${resource}`, {
        params: {
          format,
          ...Object.fromEntries(
            Object.entries(filters).filter(([, value]) => value !== ""),
          ),
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
      feedback.success(
        "Reporte generado",
        `${selectedLabel} en ${format === "pdf" ? "PDF" : "Excel"}.`,
      );
    } catch (error) {
      feedback.error("No se pudo generar el reporte", errorApi(error));
    } finally {
      setDownloading(false);
    }
  };

  if (optionsQuery.isLoading)
    return <EstadoCarga label="Preparando reportes..." />;
  if (optionsQuery.error)
    return <CajaError mensaje={errorApi(optionsQuery.error)} />;

  const statusOptions = STATUS_OPTIONS[resource];
  const organizationReport = ["solicitudes", "unidades_productivas"].includes(
    resource,
  );

  return (
    <section className="admin-page reports-page">
      <header className="page-heading reports-heading">
        <div>
          <span className="eyebrow">Información institucional</span>
          <h1>Reportes</h1>
          <p>
            Seleccione el contenido, aplique los filtros necesarios y elija el
            formato de descarga.
          </p>
        </div>
        <span className="heading-icon">
          <FileDown />
        </span>
      </header>

      <div className="reports-workspace">
        <section className="reports-config-section">
          <div className="reports-section-heading">
            <span>01</span>
            <div>
              <h2>Contenido del reporte</h2>
              <p>El reporte general incluye todos los apartados.</p>
            </div>
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
            <div>
              <h2>Filtros</h2>
              <p>
                {resource === "general"
                  ? "Se incluirán todos los registros disponibles."
                  : "Deje los filtros en Todos para obtener el reporte completo."}
              </p>
            </div>
            {activeFilterCount > 0 && (
              <button
                type="button"
                className="reports-clear-button"
                onClick={() => setFilters(defaultFilters())}
              >
                <RotateCcw size={16} /> Limpiar filtros
              </button>
            )}
          </div>

          <div
            className={`reports-dynamic-filters ${
              resource === "auditoria" ? "reports-dynamic-filters--auditoria" : ""
            }`}
            key={resource}
          >
            {resource === "general" ? (
              <div className="reports-general-message">
                <FileText aria-hidden="true" />
                <div>
                  <strong>Reporte consolidado</strong>
                  <span>
                    Solicitudes, unidades, sectores, productos, ferias,
                    administradores y auditoría.
                  </span>
                </div>
              </div>
            ) : (
              <>
                {statusOptions && (
                  <Campo label="Estado">
                    <SelectorBuscable
                      value={filters.status ?? ""}
                      options={statusOptions}
                      onChange={(value) => setFilter("status", value)}
                      searchable={false}
                      placeholder="Todos los estados"
                      ariaLabel="Filtrar por estado"
                    />
                  </Campo>
                )}

                {organizationReport && (
                  <>
                    <Campo label="Sector productivo">
                      <SelectorMultipleReportes
                        value={filters.sector_ids ?? ""}
                        options={options?.sectors ?? []}
                        onChange={(value) => setFilter("sector_ids", value)}
                        allLabel="Todos los sectores"
                        searchPlaceholder="Buscar sector..."
                        ariaLabel="Seleccionar sectores productivos"
                      />
                    </Campo>
                    <Campo label="Departamento">
                      <SelectorMultipleReportes
                        value={filters.departments ?? ""}
                        options={
                          options?.departments.map((item) => ({
                            value: item,
                            label: item,
                          })) ?? []
                        }
                        onChange={(value) => setFilter("departments", value)}
                        allLabel="Todos los departamentos"
                        searchPlaceholder="Buscar departamento..."
                        ariaLabel="Seleccionar departamentos"
                      />
                    </Campo>
                    <Campo label="NIT">
                      <SelectorBuscable
                        value={filters.has_nit ?? ""}
                        options={PRESENCE_OPTIONS}
                        onChange={(value) => setFilter("has_nit", value)}
                        searchable={false}
                        placeholder="Todos"
                        ariaLabel="Filtrar por NIT"
                      />
                    </Campo>
                    <Campo label="Registro SEPREC">
                      <SelectorBuscable
                        value={filters.has_seprec ?? ""}
                        options={PRESENCE_OPTIONS}
                        onChange={(value) => setFilter("has_seprec", value)}
                        searchable={false}
                        placeholder="Todos"
                        ariaLabel="Filtrar por SEPREC"
                      />
                    </Campo>
                    <Campo label="Registro PRO-BOLIVIA">
                      <SelectorBuscable
                        value={filters.has_pro_bolivia ?? ""}
                        options={PRESENCE_OPTIONS}
                        onChange={(value) =>
                          setFilter("has_pro_bolivia", value)
                        }
                        searchable={false}
                        placeholder="Todos"
                        ariaLabel="Filtrar por PRO-BOLIVIA"
                      />
                    </Campo>
                    <Campo label="Redes sociales">
                      <SelectorBuscable
                        value={filters.has_social ?? ""}
                        options={PRESENCE_OPTIONS}
                        onChange={(value) => setFilter("has_social", value)}
                        searchable={false}
                        placeholder="Todos"
                        ariaLabel="Filtrar por redes sociales"
                      />
                    </Campo>
                  </>
                )}

                {resource === "productos" && (
                  <>
                    <Campo label="Unidad productiva">
                      <SelectorMultipleReportes
                        value={filters.productive_unit_ids ?? ""}
                        options={options?.productive_units ?? []}
                        onChange={(value) =>
                          setFilter("productive_unit_ids", value)
                        }
                        allLabel="Todas las unidades productivas"
                        searchPlaceholder="Buscar unidad productiva..."
                        ariaLabel="Seleccionar unidades productivas"
                      />
                    </Campo>
                    <Campo label="Precio mínimo (Bs)">
                      <input
                        className="input"
                        type="number"
                        min="0"
                        step="0.01"
                        value={filters.price_min ?? ""}
                        aria-invalid={invalidPriceRange || undefined}
                        onChange={(event) =>
                          setFilter("price_min", event.target.value)
                        }
                      />
                    </Campo>
                    <Campo label="Precio máximo (Bs)">
                      <input
                        className="input"
                        type="number"
                        min={filters.price_min || "0"}
                        step="0.01"
                        value={filters.price_max ?? ""}
                        aria-invalid={invalidPriceRange || undefined}
                        aria-describedby={
                          invalidPriceRange ? "report-price-error" : undefined
                        }
                        onChange={(event) =>
                          setFilter("price_max", event.target.value)
                        }
                      />
                      {invalidPriceRange && (
                        <small
                          id="report-price-error"
                          className="field-error"
                          role="alert"
                        >
                          El precio máximo debe ser igual o mayor que el precio
                          mínimo.
                        </small>
                      )}
                    </Campo>
                  </>
                )}

                {resource === "ferias" && (
                  <>
                    <Campo label="Lugar">
                      <SelectorBuscable
                        value={filters.location ?? ""}
                        options={[
                          { value: "", label: "Todos los lugares" },
                          ...(options?.fair_locations ?? []),
                        ]}
                        onChange={(value) => setFilter("location", value)}
                        placeholder="Todos los lugares"
                        ariaLabel="Filtrar por lugar registrado"
                      />
                    </Campo>
                    <Campo label="Desde">
                      <input
                        className="input"
                        type="date"
                        max={filters.date_to || undefined}
                        value={filters.date_from ?? ""}
                        aria-invalid={invalidFairDateRange || undefined}
                        onChange={(event) =>
                          setFilter("date_from", event.target.value)
                        }
                      />
                    </Campo>
                    <Campo label="Hasta">
                      <input
                        className="input"
                        type="date"
                        min={filters.date_from || undefined}
                        value={filters.date_to ?? ""}
                        aria-invalid={invalidFairDateRange || undefined}
                        aria-describedby={
                          invalidFairDateRange ? "report-fair-date-error" : undefined
                        }
                        onChange={(event) =>
                          setFilter("date_to", event.target.value)
                        }
                      />
                      {invalidFairDateRange && (
                        <small
                          id="report-fair-date-error"
                          className="field-error"
                          role="alert"
                        >
                          La fecha final debe ser posterior a la fecha inicial.
                        </small>
                      )}
                    </Campo>
                  </>
                )}

                {resource === "auditoria" && (
                  <>
                    <Campo label="Acción">
                      <SelectorMultipleReportes
                        value={filters.actions ?? ""}
                        options={
                          options?.actions.map((item) => ({
                            value: item,
                            label: etiquetaAccionAuditoria(item),
                          })) ?? []
                        }
                        onChange={(value) => setFilter("actions", value)}
                        allLabel="Todas las acciones"
                        searchPlaceholder="Buscar acción..."
                        ariaLabel="Seleccionar acciones"
                      />
                    </Campo>
                    <Campo label="Desde">
                      <input
                        className="input"
                        type="date"
                        max={filters.date_to || undefined}
                        value={filters.date_from ?? ""}
                        onChange={(event) =>
                          setFilter("date_from", event.target.value)
                        }
                      />
                    </Campo>
                    <Campo label="Hasta">
                      <input
                        className="input"
                        type="date"
                        min={filters.date_from || undefined}
                        value={filters.date_to ?? ""}
                        onChange={(event) =>
                          setFilter("date_to", event.target.value)
                        }
                      />
                    </Campo>
                  </>
                )}
              </>
            )}
          </div>
        </section>

        <section className="reports-config-section reports-export-section">
          <div className="reports-section-heading">
            <span>03</span>
            <div>
              <h2>Formato de descarga</h2>
              <p>Ambos formatos incluyen la información filtrada.</p>
            </div>
          </div>
          <div
            className="reports-format-control"
            role="group"
            aria-label="Formato del reporte"
          >
            <button
              type="button"
              className={format === "pdf" ? "active" : ""}
              onClick={() => setFormat("pdf")}
            >
              <FileText /> PDF
            </button>
            <button
              type="button"
              className={format === "xlsx" ? "active" : ""}
              onClick={() => setFormat("xlsx")}
            >
              <FileSpreadsheet /> Excel
            </button>
          </div>
          <button
            type="button"
            className="reports-download-button"
            disabled={downloading || invalidPriceRange || invalidFairDateRange}
            onClick={() => void download()}
          >
            <FileDown />{" "}
            {downloading ? "Generando reporte..." : "Generar y descargar"}
          </button>
        </section>
      </div>
    </section>
  );
}
