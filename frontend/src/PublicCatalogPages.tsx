import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Factory, MapPin, MessageCircle, PackageSearch, Plus, Minus, Store } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, apiError, assetUrl, emptyPagination, type CanonicalFair, type CanonicalProduct, type Paged, type ProductiveSector, type ProductiveUnit } from "./api";
import { BOLIVIA_DEPARTMENTS } from "./boliviaLocations";
import { PublicHeader, InstitutionalSeal } from "./Layouts";
import { Empty, ErrorBox, Loading, Modal, PaginationBar, SearchField } from "./ui";

type ActiveFairsResponse = { active: boolean; fair: CanonicalFair | null; items: CanonicalFair[] };

const displayDate = (value: string) => new Intl.DateTimeFormat("es-BO", { dateStyle: "long" }).format(new Date(`${value}T12:00:00`));

function PublicFooter() {
  return <footer className="public-footer"><div className="container public-footer-content"><InstitutionalSeal className="footer-seal" /><div><strong>Catálogo Digital de Ferias</strong><p>Promoviendo la producción boliviana y el contacto directo con sus productores.</p></div></div></footer>;
}

function PublicShell({ children }: { children: React.ReactNode }) {
  return <><PublicHeader /><main className="container public-main">{children}</main><PublicFooter /></>;
}

function FairImage({ fair }: { fair: CanonicalFair }) {
  return fair.imagen_portada ? <img className="card-media" src={assetUrl(fair.imagen_portada)} alt={`Portada de ${fair.nombre}`} /> : <div className="card-media image-placeholder"><CalendarDays /><span>Feria productiva</span></div>;
}

export function PublicCatalogPage() {
  const [q, setQ] = useState("");
  const fairs = useQuery({ queryKey: ["public", "active-fairs"], queryFn: () => api.get<ActiveFairsResponse>("/public/fairs/active").then((response) => response.data) });
  const filtered = (fairs.data?.items ?? []).filter((fair) => `${fair.nombre} ${fair.ubicacion} ${fair.descripcion ?? ""}`.toLocaleLowerCase("es").includes(q.trim().toLocaleLowerCase("es")));

  return <PublicShell>
    <section className="catalog-welcome">
      <div><span className="eyebrow">Hecho en Bolivia</span><h1>Ferias productivas en curso</h1><p>Explore las ferias activas, conozca a sus Unidades Productivas expositoras y consulte sus productos directamente por WhatsApp.</p></div>
      <div className="catalog-welcome-mark"><Store /><span>Compra directa<br /><strong>Producción nacional</strong></span></div>
    </section>
    <div className="public-catalog-heading"><div><span className="eyebrow">Agenda vigente</span><h2>Seleccione una feria</h2><p>Cada feria muestra únicamente las unidades autorizadas por la administración.</p></div><SearchField value={q} onChange={setQ} placeholder="Buscar feria o ubicación…" /></div>
    {fairs.isLoading ? <Loading label="Buscando ferias activas…" /> : fairs.error ? <ErrorBox message={apiError(fairs.error)} /> : filtered.length ? <div className="fair-public-grid">{filtered.map((fair) => <article className="public-card fair-public-card" key={fair.id}><FairImage fair={fair} /><div className="card-body"><span className="live-pill"><i /> En curso</span><h2>{fair.nombre}</h2><p className="line-clamp">{fair.descripcion || "Encuentro de productores y emprendimientos bolivianos."}</p><div className="fair-card-meta"><span><CalendarDays />{displayDate(fair.fecha_inicio)} al {displayDate(fair.fecha_fin)}</span><span><MapPin />{fair.ubicacion}</span></div><Link className="btn" to={`/catalogo/ferias/${fair.id}`}>Entrar a la feria <span aria-hidden="true">→</span></Link></div></article>)}</div> : <Empty title="No hay ferias activas en este momento" description="Vuelva pronto para conocer las próximas ferias productivas." />}
  </PublicShell>;
}

export function PublicFairPage() {
  const { fairId = "" } = useParams();
  const [q, setQ] = useState(""); const [sector, setSector] = useState(""); const [department, setDepartment] = useState(""); const [page, setPage] = useState(1);
  const fairs = useQuery({ queryKey: ["public", "active-fairs"], queryFn: () => api.get<ActiveFairsResponse>("/public/fairs/active").then((response) => response.data) });
  const fair = fairs.data?.items.find((item) => item.id === fairId);
  const sectors = useQuery({ queryKey: ["productive-sectors", "public"], queryFn: () => api.get<Paged<ProductiveSector>>("/productive-sectors", { params: { per_page: 100 } }).then((response) => response.data.items) });
  const units = useQuery({ queryKey: ["public", "fair-units", fairId, q, sector, department, page], enabled: Boolean(fair), queryFn: () => api.get<Paged<ProductiveUnit>>("/public/productive-units", { params: { fair_id: fairId, q: q || undefined, sector_id: sector || undefined, departamento: department || undefined, page, per_page: 12 } }).then((response) => response.data) });
  const data = units.data ?? { items: [], pagination: emptyPagination };

  return <PublicShell>
    <Link className="back-link" to="/catalogo"><ArrowLeft size={18} /> Todas las ferias</Link>
    {fairs.isLoading ? <Loading /> : !fair ? <Empty title="La feria no está disponible" description="Puede haber finalizado o dejado de estar visible." /> : <>
      <section className="fair-detail-banner"><FairImage fair={fair} /><div><span className="live-pill"><i /> Feria en curso</span><h1>{fair.nombre}</h1><p>{fair.descripcion}</p><div className="fair-card-meta"><span><CalendarDays />{displayDate(fair.fecha_inicio)} al {displayDate(fair.fecha_fin)}</span><span><MapPin />{fair.ubicacion}</span></div></div></section>
      <div className="section-heading"><div><span className="eyebrow">Expositores</span><h2>Unidades Productivas participantes</h2><p>Entre al perfil de una unidad para conocer y consultar sus productos.</p></div></div>
      <div className="catalog-toolbar panel"><SearchField value={q} onChange={(value) => { setQ(value); setPage(1); }} placeholder="Buscar Unidad Productiva…" /><select className="input" value={sector} onChange={(event) => { setSector(event.target.value); setPage(1); }}><option value="">Todos los sectores</option>{sectors.data?.map((item) => <option value={item.id} key={item.id}>{item.nombre}</option>)}</select><select className="input" value={department} onChange={(event) => { setDepartment(event.target.value); setPage(1); }}><option value="">Todos los departamentos</option>{BOLIVIA_DEPARTMENTS.map((item) => <option key={item}>{item}</option>)}</select></div>
      {units.isLoading ? <Loading label="Cargando expositores…" /> : units.error ? <ErrorBox message={apiError(units.error)} /> : data.items.length ? <><div className="exhibitor-grid">{data.items.map((unit) => <article className="public-card exhibitor-card" key={unit.id}>{unit.logo_url ? <img className="card-media unit-logo" src={assetUrl(unit.logo_url)} alt={`Logo de ${unit.nombre_comercial}`} /> : <div className="card-media image-placeholder"><Factory /><span>Unidad Productiva</span></div>}<div className="card-body"><span className="sector-label">{unit.sectores.map((item) => item.nombre).join(" · ") || "Producción nacional"}</span><h3>{unit.nombre_comercial}</h3><p className="line-clamp">{unit.resena_comercial}</p><small><MapPin size={15} /> {unit.departamento}</small><Link className="btn-outline" to={`/catalogo/ferias/${fairId}/unidades/${unit.id}`}>Ver productos <span aria-hidden="true">→</span></Link></div></article>)}</div><PaginationBar pagination={data.pagination} onPageChange={setPage} /></> : <Empty title="No se encontraron expositores" description="Cambie los filtros para ver otras Unidades Productivas." />}
    </>}
  </PublicShell>;
}

export function PublicUnitPage() {
  const { fairId = "", unitId = "" } = useParams();
  const [cart, setCart] = useState<Record<string, number>>({}); const [selected, setSelected] = useState<CanonicalProduct | null>(null); const [sending, setSending] = useState(false); const [sendError, setSendError] = useState("");
  const unit = useQuery({ queryKey: ["public", "fair-unit", fairId, unitId], queryFn: () => api.get<ProductiveUnit>(`/public/productive-units/${unitId}`, { params: { fair_id: fairId } }).then((response) => response.data) });
  const selectedItems = useMemo(() => Object.entries(cart).filter(([, quantity]) => quantity > 0), [cart]);
  const changeQuantity = (id: string, value: number) => setCart((current) => ({ ...current, [id]: Math.max(0, Math.min(999, value)) }));
  const sendWhatsApp = async () => { setSending(true); setSendError(""); try { const response = await api.post<{ url: string }>("/public/whatsapp", { fair_id: fairId, items: selectedItems.map(([product_id, quantity]) => ({ product_id, quantity })) }); window.open(response.data.url, "_blank", "noopener,noreferrer"); } catch (error) { setSendError(apiError(error, "No se pudo abrir WhatsApp.")); } finally { setSending(false); } };

  return <PublicShell>
    <Link className="back-link" to={`/catalogo/ferias/${fairId}`}><ArrowLeft size={18} /> Volver a los expositores</Link>
    {unit.isLoading ? <Loading label="Cargando productos…" /> : unit.error || !unit.data ? <ErrorBox message={apiError(unit.error, "La Unidad Productiva no está disponible en esta feria.")} /> : <>
      <section className="unit-public-header"><div className="unit-public-logo">{unit.data.logo_url ? <img src={assetUrl(unit.data.logo_url)} alt={`Logo de ${unit.data.nombre_comercial}`} /> : <Factory />}</div><div><span className="eyebrow">Unidad Productiva expositora</span><h1>{unit.data.nombre_comercial}</h1><p>{unit.data.resena_comercial}</p><div className="unit-public-meta"><span><MapPin />{unit.data.departamento}</span><span><PackageSearch />{unit.data.productos?.length ?? 0} productos disponibles</span></div></div></section>
      <div className="section-heading"><div><span className="eyebrow">Catálogo del expositor</span><h2>Productos disponibles</h2><p>Seleccione cantidades y envíe una consulta directa por WhatsApp.</p></div></div>
      <div className="product-grid">{unit.data.productos?.map((product) => { const image = product.imagenes.find((item) => item.es_principal) ?? product.imagenes[0]; const quantity = cart[product.id] ?? 0; return <article className="product-card" key={product.id}><button className="product-image-button" onClick={() => setSelected(product)}>{image ? <img className="card-media" src={assetUrl(image.url_imagen)} alt={image.texto_alternativo || product.nombre_comercial} /> : <div className="card-media image-placeholder"><PackageSearch /><span>Producto</span></div>}</button><div className="card-body"><button className="product-title" onClick={() => setSelected(product)}>{product.nombre_comercial}</button><p className="line-clamp">{product.descripcion_tecnica}</p><strong className="price">Bs {Number(product.precio_referencia).toFixed(2)}</strong><div className="quantity"><button onClick={() => changeQuantity(product.id, quantity - 1)} aria-label={`Quitar ${product.nombre_comercial}`}><Minus /></button><strong>{quantity}</strong><button onClick={() => changeQuantity(product.id, quantity + 1)} aria-label={`Agregar ${product.nombre_comercial}`}><Plus /></button></div></div></article>; })}</div>
      {sendError && <div className="selection-error">{sendError}</div>}
      {selectedItems.length > 0 && <div className="selection-bar"><span><strong>{selectedItems.length}</strong> producto(s) seleccionado(s)</span><button className="btn-secondary" disabled={sending} onClick={() => void sendWhatsApp()}><MessageCircle />{sending ? "Preparando…" : "Consultar por WhatsApp"}</button><button onClick={() => setCart({})} aria-label="Vaciar selección">×</button></div>}
      {selected && <Modal title={selected.nombre_comercial} onClose={() => setSelected(null)} wide><div className="product-detail"><div>{selected.imagenes.length ? <><img className="detail-image" src={assetUrl((selected.imagenes.find((item) => item.es_principal) ?? selected.imagenes[0]).url_imagen)} alt={selected.nombre_comercial} /><div className="thumbnail-row">{selected.imagenes.map((image) => <span key={image.id}><img src={assetUrl(image.url_imagen)} alt={image.texto_alternativo || selected.nombre_comercial} /></span>)}</div></> : <div className="detail-image image-placeholder"><PackageSearch /></div>}</div><div className="detail-copy"><span className="eyebrow">Producto boliviano</span><h2>{selected.nombre_comercial}</h2><p>{selected.descripcion_tecnica}</p><strong className="price">Bs {Number(selected.precio_referencia).toFixed(2)}</strong><dl><dt>Materia prima</dt><dd>{selected.materia_prima}</dd><dt>Presentación</dt><dd>{selected.presentacion_empaque}</dd><dt>Capacidad/stock</dt><dd>{selected.capacidad_produccion_stock}</dd>{selected.dimensiones && <><dt>Dimensiones</dt><dd>{selected.dimensiones}</dd></>}</dl><button className="btn-secondary" onClick={() => { changeQuantity(selected.id, Math.max(1, cart[selected.id] ?? 0)); setSelected(null); }}><Plus /> Agregar a la consulta</button></div></div></Modal>}
    </>}
  </PublicShell>;
}
