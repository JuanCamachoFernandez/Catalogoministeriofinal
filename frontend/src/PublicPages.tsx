import { useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  ImageOff,
  MapPin,
  MessageCircle,
  Minus,
  PackageSearch,
  Plus,
  Store,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  apiError,
  assetUrl,
  emptyPagination,
  type Fair,
  type Paged,
  type Product,
} from "./api";
import { buildWhatsappItems } from "./catalogUtils";
import { InstitutionalSeal, PublicHeader } from "./Layouts";
import {
  Empty,
  ErrorBox,
  Loading,
  Modal,
  PaginationBar,
  SearchField,
  StatusBadge,
} from "./ui";

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", {
    dateStyle: "long",
    timeZone: "America/La_Paz",
  }).format(new Date(`${value}T12:00:00`));
function Media({
  src,
  alt,
  className = "",
}: {
  src?: string | null;
  alt: string;
  className?: string;
}) {
  return src ? (
    <img className={className} src={assetUrl(src)} alt={alt} />
  ) : (
    <div className={`image-placeholder ${className}`}>
      <ImageOff />
      <span>Sin imagen</span>
    </div>
  );
}

export function CatalogPage() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const fairs = useQuery({
    queryKey: ["public", "fairs", query, page],
    queryFn: () =>
      api
        .get<Paged<Fair>>("/public/fairs", {
          params: { q: query || undefined, page, per_page: 9 },
        })
        .then((response) => response.data),
  });
  return (
    <>
      <PublicHeader />
      <main className="public-main container">
        <section className="public-catalog-heading">
          <div>
            <span className="eyebrow">Catálogo nacional</span>
            <h1>Ferias disponibles</h1>
            <p>Seleccione una feria para conocer sus datos, expositores y productos.</p>
          </div>
          <SearchField
            value={query}
            onChange={(value) => {
              setQuery(value);
              setPage(1);
            }}
            placeholder="Buscar feria…"
          />
        </section>
        {fairs.isLoading ? (
          <Loading label="Cargando ferias…" />
        ) : fairs.error ? (
          <ErrorBox message={apiError(fairs.error, "No se pudieron cargar las ferias.")} />
        ) : fairs.data?.items.length ? (
          <>
            <div className="fair-public-grid">
              {fairs.data.items.map((fair) => (
                <article className="public-card fair-public-card" key={fair.id}>
                  <Media
                    src={fair.imagen_portada}
                    alt={`Portada de ${fair.nombre}`}
                    className="card-media"
                  />
                  <div className="card-body">
                    <h2>{fair.nombre}</h2>
                    <div className="fair-card-meta">
                      <span><MapPin /> {fair.departamento}</span>
                      <span><CalendarDays /> {formatDate(fair.fecha_inicio)} – {formatDate(fair.fecha_fin)}</span>
                    </div>
                    {fair.descripcion && <p className="line-clamp">{fair.descripcion}</p>}
                    <Link className="btn w-full" to={`/catalogo/ferias/${fair.slug}`}>
                      Entrar a la feria
                    </Link>
                  </div>
                </article>
              ))}
            </div>
            <PaginationBar pagination={fairs.data.pagination} onPage={setPage} />
          </>
        ) : (
          <Empty
            title={query ? "No encontramos ferias" : "No hay ferias publicadas"}
            description={query ? "Pruebe con otro nombre." : "Las ferias aparecerán aquí durante sus fechas de publicación."}
          />
        )}
      </main>
      <PublicFooter />
    </>
  );
}

export function FairDetailPage() {
  const { slug = "" } = useParams();
  const [query, setQuery] = useState("");
  const fair = useQuery({
    queryKey: ["public", "fair", slug, query],
    queryFn: () => api.get<Fair>(`/public/fairs/${slug}`, {
      params: { q: query || undefined },
    }).then((response) => response.data),
  });
  return (
    <>
      <PublicHeader />
      <main className="public-main container">
        <Link className="back-link" to="/catalogo">← Volver a las ferias</Link>
        {fair.isLoading ? (
          <Loading label="Cargando feria…" />
        ) : fair.error ? (
          <ErrorBox message={apiError(fair.error, "La feria no está disponible.")} />
        ) : fair.data && (
          <>
            <section className="fair-hero fair-detail-hero">
              <Media src={fair.data.imagen_portada} alt={`Portada de ${fair.data.nombre}`} className="fair-cover" />
              <div className="fair-overlay">
                <h1>{fair.data.nombre}</h1>
                {fair.data.descripcion && <p>{fair.data.descripcion}</p>}
                <div className="hero-meta">
                  <span><MapPin /> {fair.data.lugar}, {fair.data.departamento}</span>
                  <span><CalendarDays /> {formatDate(fair.data.fecha_inicio)} – {formatDate(fair.data.fecha_fin)}</span>
                </div>
                {fair.data.direccion && <p className="fair-address">Dirección: {fair.data.direccion}</p>}
              </div>
            </section>
            <section className="section-heading">
              <div>
                <span className="eyebrow">Participantes</span>
                <h2>Expositores de esta feria</h2>
              </div>
              <SearchField value={query} onChange={setQuery} placeholder="Buscar expositor…" />
            </section>
            {fair.data.expositores?.length ? (
              <div className="exhibitor-grid">
                {fair.data.expositores.map((item) => (
                  <article className="public-card" key={item.id}>
                    <Media src={item.logo} alt={`Logo de ${item.nombre_comercial}`} className="card-media" />
                    <div className="card-body">
                      <Store className="card-icon" />
                      <h3>{item.nombre_comercial}</h3>
                      <p>{item.descripcion || "Expositor participante de esta feria."}</p>
                      {(item.numero_stand || item.sector) && (
                        <small>{item.sector}{item.numero_stand && ` · Stand ${item.numero_stand}`}</small>
                      )}
                      <Link className="btn w-full" to={`/catalogo/ferias/${fair.data.slug}/expositores/${item.id}`}>
                        Ver productos
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <Empty title="Sin expositores" description={query ? "No encontramos expositores con ese nombre." : "Todavía no hay expositores autorizados en esta feria."} />
            )}
          </>
        )}
      </main>
      <PublicFooter />
    </>
  );
}

function ProductDetail({
  product,
  onClose,
}: {
  product: Product;
  onClose: () => void;
}) {
  const [selectedImage, setSelectedImage] = useState(product.imagenes[0]?.url);
  return (
    <Modal title={product.nombre} onClose={onClose} wide>
      <div className="product-detail">
        <div>
          <Media
            src={selectedImage}
            alt={product.nombre}
            className="detail-image"
          />
          {product.imagenes.length > 1 && (
            <div className="thumbnail-row">
              {product.imagenes.map((image) => (
                <button
                  key={image.id}
                  onClick={() => setSelectedImage(image.url)}
                >
                  <Media
                    src={image.url}
                    alt={image.alt_text || product.nombre}
                  />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="detail-copy">
          <StatusBadge value={product.estado} />
          <p>{product.descripcion}</p>
          <dl>
            {product.categoria && (
              <>
                <dt>Categoría</dt>
                <dd>{product.categoria.nombre}</dd>
              </>
            )}
            {product.materiales_o_ingredientes && (
              <>
                <dt>Materiales o ingredientes</dt>
                <dd>{product.materiales_o_ingredientes}</dd>
              </>
            )}
            {product.lugar_origen && (
              <>
                <dt>Lugar de origen</dt>
                <dd>{product.lugar_origen}</dd>
              </>
            )}
            {product.presentacion && (
              <>
                <dt>Presentación</dt>
                <dd>{product.presentacion}</dd>
              </>
            )}
          </dl>
        </div>
      </div>
    </Modal>
  );
}

export function ExhibitorCatalogPage() {
  const { slug = "", exhibitorId = "" } = useParams();
  const [query, setQuery] = useState("");
  const [availability, setAvailability] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [page, setPage] = useState(1);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [detail, setDetail] = useState<Product | null>(null);
  const [whatsappError, setWhatsappError] = useState("");
  const result = useQuery({
    queryKey: [
      "public",
      "exhibitor",
      slug,
      exhibitorId,
      query,
      availability,
      categoryId,
      page,
    ],
    queryFn: () =>
      api
        .get<{
          id: string;
          nombre_comercial: string;
          descripcion: string | null;
          productos: Product[];
          pagination: Paged<Product>["pagination"];
        }>(`/public/fairs/${slug}/exhibitors/${exhibitorId}`, {
          params: {
            q: query || undefined,
            availability: availability || undefined,
            category_id: categoryId || undefined,
            page,
          },
        })
        .then((response) => response.data),
  });
  const categories = useMemo(() => {
    const map = new Map<string, string>();
    result.data?.productos.forEach(
      (product) =>
        product.categoria &&
        map.set(product.categoria.id, product.categoria.nombre),
    );
    return [...map.entries()];
  }, [result.data]);
  const selectedCount = Object.keys(quantities).length;
  const updateQuantity = (id: string, delta: number) =>
    setQuantities((current) => {
      const next = Math.max(0, (current[id] ?? 0) + delta);
      const copy = { ...current };
      if (next) copy[id] = next;
      else delete copy[id];
      return copy;
    });
  const consult = async () => {
    setWhatsappError("");
    try {
      const { data } = await api.post<{ url: string }>(
        "/public/whatsapp-query",
        { fair_slug: slug, items: buildWhatsappItems(quantities) },
      );
      window.open(data.url, "_blank", "noopener,noreferrer");
    } catch (reason) {
      setWhatsappError(apiError(reason, "No se pudo generar la consulta."));
    }
  };
  return (
    <>
      <PublicHeader />
      <main className="public-main container">
        <Link className="back-link" to={`/catalogo/ferias/${slug}`}>
          ← Volver a la feria
        </Link>
        {result.isLoading ? (
          <Loading label="Cargando productos…" />
        ) : result.error ? (
          <ErrorBox
            message={apiError(
              result.error,
              "El expositor no está disponible en esta feria.",
            )}
          />
        ) : (
          result.data && (
            <>
              <section className="store-heading">
                <span className="eyebrow">Tienda del expositor</span>
                <h1>{result.data.nombre_comercial}</h1>
                <p>{result.data.descripcion}</p>
              </section>
              <div className="catalog-toolbar">
                <SearchField
                  value={query}
                  onChange={(value) => {
                    setQuery(value);
                    setPage(1);
                  }}
                  placeholder="Buscar producto…"
                />
                <select
                  className="input"
                  value={categoryId}
                  onChange={(event) => {
                    setCategoryId(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">Todas las categorías</option>
                  {categories.map(([id, name]) => (
                    <option key={id} value={id}>
                      {name}
                    </option>
                  ))}
                </select>
                <select
                  className="input"
                  value={availability}
                  onChange={(event) => {
                    setAvailability(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">Toda disponibilidad</option>
                  <option value="AVAILABLE">Disponibles</option>
                  <option value="OUT_OF_STOCK">Agotados</option>
                </select>
              </div>
              {result.data.productos.length ? (
                <div className="product-grid">
                  {result.data.productos.map((product) => {
                    const available = product.estado === "AVAILABLE";
                    const quantity = quantities[product.id] ?? 0;
                    return (
                      <article className="product-card" key={product.id}>
                        <button
                          className="product-image-button"
                          onClick={() => setDetail(product)}
                        >
                          <Media
                            src={product.imagenes[0]?.url}
                            alt={product.nombre}
                            className="card-media"
                          />
                        </button>
                        <div className="card-body">
                          <div className="flex justify-between gap-2">
                            <StatusBadge value={product.estado} />
                            {product.categoria && (
                              <small>{product.categoria.nombre}</small>
                            )}
                          </div>
                          <button
                            className="product-title"
                            onClick={() => setDetail(product)}
                          >
                            {product.nombre}
                          </button>
                          <p className="line-clamp">{product.descripcion}</p>
                          {available ? (
                            quantity ? (
                              <div className="quantity">
                                <button
                                  onClick={() => updateQuantity(product.id, -1)}
                                  aria-label="Restar"
                                >
                                  <Minus />
                                </button>
                                <span>{quantity}</span>
                                <button
                                  onClick={() => updateQuantity(product.id, 1)}
                                  aria-label="Sumar"
                                >
                                  <Plus />
                                </button>
                              </div>
                            ) : (
                              <button
                                className="btn-outline w-full"
                                onClick={() => updateQuantity(product.id, 1)}
                              >
                                <Plus size={18} /> Agregar a consulta
                              </button>
                            )
                          ) : (
                            <button disabled className="btn-outline w-full">
                              No disponible
                            </button>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <Empty
                  title="No encontramos productos"
                  description="Pruebe con otros filtros de búsqueda."
                />
              )}
              <PaginationBar
                pagination={result.data.pagination ?? emptyPagination}
                onPage={setPage}
              />
            </>
          )
        )}
      </main>
      {selectedCount > 0 && (
        <aside className="selection-bar">
          <div>
            <strong>{selectedCount} producto(s)</strong>
            <span> en su consulta</span>
          </div>
          {whatsappError && (
            <span className="text-danger">{whatsappError}</span>
          )}
          <button className="btn-secondary" onClick={consult}>
            <MessageCircle /> Consultar por WhatsApp
          </button>
          <button
            onClick={() => setQuantities({})}
            aria-label="Vaciar selección"
          >
            <X />
          </button>
        </aside>
      )}
      {detail && (
        <ProductDetail product={detail} onClose={() => setDetail(null)} />
      )}
      <PublicFooter />
    </>
  );
}

export function NotFoundPage() {
  return (
    <>
      <PublicHeader />
      <main className="page-state min-h-[60vh]">
        <PackageSearch size={56} />
        <h1>Página no encontrada</h1>
        <Link className="btn" to="/catalogo">
          Volver al catálogo
        </Link>
      </main>
      <PublicFooter />
    </>
  );
}
function PublicFooter() {
  return (
    <footer className="public-footer">
      <div className="container public-footer-content">
        <InstitutionalSeal className="footer-seal" />
        <div>
          <strong>Ferias Productivas Bolivia</strong>
          <p>Promoviendo la producción y el emprendimiento boliviano.</p>
        </div>
      </div>
    </footer>
  );
}
