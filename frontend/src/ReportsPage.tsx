import { useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet, FileText, Filter, Plus } from "lucide-react";
import { useState } from "react";
import { api, apiError, type Category, type Exhibitor, type Paged } from "./api";
import { BOLIVIA_DEPARTMENTS, municipalitiesFor } from "./boliviaLocations";
import { Field, Modal, SearchableSelect, useFeedback } from "./ui";

type Resource = "general" | "administradores" | "expositores" | "ferias" | "productos" | "categorias" | "auditoria";
type Option = { value: Exclude<Resource, "general">; label: string; columns: { value: string; label: string }[] };
type Options = { resources: Option[]; actions: string[]; entities: string[] };
type Filters = Record<"q" | "status" | "role" | "unit" | "department" | "municipality" | "document_type" | "exhibitor_id" | "category_id" | "action" | "entity" | "date_from" | "date_to", string>;

const emptyFilters: Filters = { q: "", status: "", role: "", unit: "", department: "", municipality: "", document_type: "", exhibitor_id: "", category_id: "", action: "", entity: "", date_from: "", date_to: "" };
const resources: { value: Resource; label: string; description: string }[] = [
  { value: "general", label: "Reporte general", description: "Todas las áreas del sistema en un solo archivo." },
  { value: "administradores", label: "Administradores", description: "Cuentas, roles, unidades, cargos y estados." },
  { value: "expositores", label: "Expositores", description: "Empresas, responsables, ubicación y contacto." },
  { value: "ferias", label: "Ferias", description: "Programación, ubicación, fechas y publicación." },
  { value: "productos", label: "Productos", description: "Oferta, expositor, categoría y disponibilidad." },
  { value: "categorias", label: "Categorías", description: "Clasificación y estado de las categorías." },
  { value: "auditoria", label: "Auditoría", description: "Usuarios, acciones, entidades, fechas y descripciones." },
];

function filename(header: string | undefined, fallback: string) {
  const match = header?.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  return match ? decodeURIComponent(match[1].replace(/"$/, "")) : fallback;
}

function ReportModal({ initial, close }: { initial: Resource; close: () => void }) {
  const feedback = useFeedback();
  const [resource, setResource] = useState<Resource>(initial);
  const [format, setFormat] = useState<"pdf" | "xlsx">("pdf");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [columns, setColumns] = useState<string[] | null>(null);
  const [pending, setPending] = useState(false);
  const options = useQuery({ queryKey: ["report-options"], queryFn: () => api.get<Options>("/reports/options").then((r) => r.data) });
  const units = useQuery({ queryKey: ["admin-units"], queryFn: () => api.get<{ items: { id: string; nombre: string }[] }>("/admin/units").then((r) => r.data.items) });
  const exhibitors = useQuery({ queryKey: ["exhibitors", "report-options"], queryFn: () => api.get<Paged<Exhibitor>>("/exhibitors", { params: { per_page: 100 } }).then((r) => r.data.items) });
  const categories = useQuery({ queryKey: ["categories", "report-options"], queryFn: () => api.get<Paged<Category>>("/admin/categories", { params: { per_page: 100 } }).then((r) => r.data.items) });
  const definition = options.data?.resources.find((item) => item.value === resource);
  const selectedColumns = columns ?? definition?.columns.map((item) => item.value) ?? [];
  const change = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  const statusOptions = resource === "ferias" ? [["DRAFT", "En preparación"], ["PUBLISHED", "Publicada"], ["FINISHED", "Finalizada"], ["DISABLED", "Cancelada"]] : resource === "productos" ? [["AVAILABLE", "Disponible"], ["OUT_OF_STOCK", "Agotado"], ["INACTIVE", "Inactivo"]] : resource === "categorias" ? [["active", "Activa"], ["inactive", "Inactiva"]] : [["ACTIVE", "Activo"], ["INACTIVE", "Inactivo"], ["LOCKED", "Bloqueado"]];

  const download = async () => {
    if (resource !== "general" && !selectedColumns.length) return feedback.error("Faltan columnas", "Seleccione al menos una columna.");
    if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) return feedback.error("Fechas incorrectas", "La fecha inicial no puede ser posterior a la final.");
    setPending(true);
    try {
      const params = Object.fromEntries(Object.entries({ format, ...filters, columns: resource === "general" ? "" : selectedColumns.join(",") }).filter(([, value]) => value));
      const response = await api.get<Blob>(`/reports/${resource}`, { params, responseType: "blob" });
      const now = new Date();
      const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
      const fallback = `reporte_${resource}_${stamp}.${format}`;
      const name = filename(response.headers["content-disposition"], fallback);
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url; link.download = name; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
      close();
      feedback.success("Reporte descargado", `${name} se guardó en el dispositivo.`);
    } catch (reason) { feedback.error("No se pudo generar el reporte", apiError(reason, "Inténtelo nuevamente.")); }
    finally { setPending(false); }
  };

  return <Modal title="Generar reporte" onClose={close} wide><div className="report-builder">
    <section className="report-section"><h3>1. Tipo y formato</h3><div className="form-grid">
      <Field label="Contenido"><select className="input" value={resource} onChange={(e) => { setResource(e.target.value as Resource); setFilters(emptyFilters); setColumns(null); }}>{resources.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field>
      <Field label="Formato"><div className="report-format-options"><button type="button" className={format === "pdf" ? "active" : ""} onClick={() => setFormat("pdf")}><FileText /> PDF</button><button type="button" className={format === "xlsx" ? "active" : ""} onClick={() => setFormat("xlsx")}><FileSpreadsheet /> Excel</button></div></Field>
    </div></section>
    {resource !== "general" && <section className="report-section"><h3><Filter size={19} /> 2. Filtros</h3><div className="form-grid">
      <Field label="Buscar texto"><input className="input" value={filters.q} onChange={(e) => change("q", e.target.value)} placeholder="Nombre, correo, documento…" /></Field>
      {resource !== "auditoria" && <Field label="Estado"><select className="input" value={filters.status} onChange={(e) => change("status", e.target.value)}><option value="">Todos</option>{statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>}
      {resource === "administradores" && <><Field label="Rol"><select className="input" value={filters.role} onChange={(e) => change("role", e.target.value)}><option value="">Todos</option><option value="SUPERADMIN">Superadministrador</option><option value="ADMIN_VICEMINISTERIO">Administrador</option></select></Field><Field label="Unidad"><select className="input" value={filters.unit} onChange={(e) => change("unit", e.target.value)}><option value="">Todas</option>{units.data?.map((item) => <option key={item.id}>{item.nombre}</option>)}</select></Field></>}
      {["expositores", "ferias"].includes(resource) && <><Field label="Departamento"><SearchableSelect value={filters.department} options={[{ value: "", label: "Todos" }, ...BOLIVIA_DEPARTMENTS.map((item) => ({ value: item, label: item }))]} onChange={(value) => { change("department", value); change("municipality", ""); }} ariaLabel="Departamento del reporte" /></Field><Field label="Municipio"><SearchableSelect disabled={!filters.department} value={filters.municipality} options={[{ value: "", label: "Todos" }, ...municipalitiesFor(filters.department).map((item) => ({ value: item, label: item }))]} onChange={(value) => change("municipality", value)} ariaLabel="Municipio del reporte" /></Field></>}
      {resource === "expositores" && <Field label="Tipo de documento"><select className="input" value={filters.document_type} onChange={(e) => change("document_type", e.target.value)}><option value="">Todos</option><option value="CI">CI</option><option value="NIT">NIT</option><option value="OTRO">Otro</option></select></Field>}
      {resource === "productos" && <><Field label="Expositor"><select className="input" value={filters.exhibitor_id} onChange={(e) => change("exhibitor_id", e.target.value)}><option value="">Todos</option>{exhibitors.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre_comercial}</option>)}</select></Field><Field label="Categoría"><select className="input" value={filters.category_id} onChange={(e) => change("category_id", e.target.value)}><option value="">Todas</option>{categories.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select></Field></>}
      {resource === "auditoria" && <><Field label="Acción"><select className="input" value={filters.action} onChange={(e) => change("action", e.target.value)}><option value="">Todas</option>{options.data?.actions.map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}</select></Field><Field label="Entidad"><select className="input" value={filters.entity} onChange={(e) => change("entity", e.target.value)}><option value="">Todas</option>{options.data?.entities.map((item) => <option key={item}>{item}</option>)}</select></Field></>}
      <Field label="Fecha inicial"><input className="input" type="date" value={filters.date_from} onChange={(e) => change("date_from", e.target.value)} /></Field><Field label="Fecha final"><input className="input" type="date" value={filters.date_to} onChange={(e) => change("date_to", e.target.value)} /></Field>
    </div></section>}
    {resource !== "general" && definition && <section className="report-section"><div className="report-section-heading"><h3>3. Columnas</h3><div><button type="button" className="text-button" onClick={() => setColumns(definition.columns.map((item) => item.value))}>Todas</button><button type="button" className="text-button" onClick={() => setColumns([])}>Limpiar</button></div></div><div className="report-columns">{definition.columns.map((item) => <label key={item.value}><input type="checkbox" checked={selectedColumns.includes(item.value)} onChange={(e) => setColumns(e.target.checked ? [...selectedColumns, item.value] : selectedColumns.filter((value) => value !== item.value))} />{item.label}</label>)}</div></section>}
    <div className="modal-actions"><button type="button" className="btn-outline" onClick={close}>Cancelar</button><button type="button" className="btn" disabled={pending || options.isLoading} onClick={download}><Download size={18} /> {pending ? "Generando…" : "Generar y descargar"}</button></div>
  </div></Modal>;
}

export function ReportsPage() {
  const [modal, setModal] = useState<Resource | null>(null);
  return <><div className="page-header"><div><span className="eyebrow">Información</span><h1>Reportes</h1><p>Descargue información filtrada en PDF o Excel.</p></div><button className="btn" onClick={() => setModal("general")}><Plus /> Generar reporte</button></div>
    <div className="report-resource-grid">{resources.map((item) => <article className="data-card report-resource-card" key={item.value}><div><span className="report-resource-icon">{item.value === "general" || item.value === "productos" ? <FileSpreadsheet /> : <FileText />}</span><h2>{item.label}</h2><p>{item.description}</p></div><button className="btn-outline" onClick={() => setModal(item.value)}><Download size={17} /> Configurar</button></article>)}</div>
    {modal && <ReportModal initial={modal} close={() => setModal(null)} />}</>;
}
