import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Factory,
  MapPin,
  MessageCircle,
  PackageSearch,
  Plus,
  Minus,
  ShoppingBag,
  Trash2,
} from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  api,
  apiError,
  assetUrl,
  emptyPagination,
  type CanonicalFair,
  type CanonicalProduct,
  type Paged,
  type ProductiveSector,
  type ProductiveUnit,
} from "./api";
import { BOLIVIA_DEPARTMENTS } from "./boliviaLocations";
import { PublicHeader, InstitutionalSeal } from "./Layouts";
import {
  Empty,
  ErrorBox,
  Loading,
  Modal,
  PaginationBar,
  SearchableSelect,
  SearchField,
} from "./ui";

type ActiveFairsResponse = {
  active: boolean;
  fair: CanonicalFair | null;
  items: CanonicalFair[];
};

const displayDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", { dateStyle: "long" }).format(
    new Date(`${value}T12:00:00`),
  );
function PublicFooter() {
  return (
    <footer className="public-footer">
      <div className="container public-footer-content">
        <InstitutionalSeal className="footer-seal" />
        <div>
          <strong>Ferias Productivas Bolivia</strong>
          <p>
            Promoviendo la producción boliviana y el contacto directo con sus
            productores.
          </p>
        </div>
      </div>
    </footer>
  );
}

function PublicShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    const root = document.documentElement;
    const previousBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, 0);
    root.scrollTop = 0;
    document.body.scrollTop = 0;
    root.style.scrollBehavior = previousBehavior;
  }, [pathname]);

  return (
    <>
      <PublicHeader />
      <main className="container public-main">{children}</main>
      <PublicFooter />
    </>
  );
}

function FairImage({ fair }: { fair: CanonicalFair }) {
  return fair.imagen_portada ? (
    <img
      className="card-media"
      src={assetUrl(fair.imagen_portada)}
      alt={`Portada de ${fair.nombre}`}
    />
  ) : (
    <div className="card-media image-placeholder">
      <CalendarDays />
      <span>Feria productiva</span>
    </div>
  );
}

function CatalogPlaceholder({
  kind,
  name,
  large = false,
}: {
  kind: "unit" | "product";
  name: string;
  large?: boolean;
}) {
  const initials =
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase() || (kind === "unit" ? "UP" : "PB");
  return (
    <div
      className={`${large ? "detail-image " : "card-media "}catalog-media-placeholder ${kind === "unit" ? "unit-placeholder" : "product-placeholder"}`}
      aria-label={`${name}, imagen no disponible`}
    >
      <span className="placeholder-orbit" aria-hidden="true" />
      <span className="placeholder-mark" aria-hidden="true">
        {kind === "unit" ? <Factory /> : <PackageSearch />}
      </span>
      <strong>{initials}</strong>
      <small>
        {kind === "unit" ? "Unidad Productiva" : "Producto boliviano"}
      </small>
    </div>
  );
}

export function PublicCatalogPage() {
  const [q, setQ] = useState("");
  const fairs = useQuery({
    queryKey: ["public", "active-fairs"],
    queryFn: () =>
      api
        .get<ActiveFairsResponse>("/public/fairs/active")
        .then((response) => response.data),
  });
  const filtered = (fairs.data?.items ?? []).filter((fair) =>
    `${fair.nombre} ${fair.ubicacion} ${fair.descripcion ?? ""}`
      .toLocaleLowerCase("es")
      .includes(q.trim().toLocaleLowerCase("es")),
  );

  return (
    <PublicShell>
      <div className="public-catalog-heading">
        <div>
          <h1>Ferias productivas en curso</h1>
          <p>
            Ingrese a una feria y descubra productos hechos en Bolivia por
            productores nacionales.
          </p>
        </div>
        <SearchField
          value={q}
          onChange={setQ}
          placeholder="Buscar feria o ubicación…"
        />
      </div>
      {fairs.isLoading ? (
        <Loading label="Buscando ferias activas…" />
      ) : fairs.error ? (
        <ErrorBox message={apiError(fairs.error)} />
      ) : filtered.length ? (
        <div className="fair-public-grid">
          {filtered.map((fair) => (
            <article className="public-card fair-public-card" key={fair.id}>
              <FairImage fair={fair} />
              <div className="card-body">
                <h2>{fair.nombre}</h2>
                <div className="fair-card-meta">
                  <span>
                    <CalendarDays />
                    {displayDate(fair.fecha_inicio)} al{" "}
                    {displayDate(fair.fecha_fin)}
                  </span>
                  <span>
                    <MapPin />
                    {fair.ubicacion}
                  </span>
                </div>
                <Link
                  className="btn fair-entry-button"
                  to={`/catalogo/ferias/${fair.id}`}
                >
                  Entrar a la feria <span aria-hidden="true">→</span>
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="No hay ferias activas en este momento"
          description="Vuelva pronto para conocer las próximas ferias productivas."
        />
      )}
    </PublicShell>
  );
}

export function PublicFairPage() {
  const { fairId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "",
    sector = searchParams.get("sector") ?? "",
    department = searchParams.get("departamento") ?? "";
  const parsedPage = Number(searchParams.get("pagina") ?? 1),
    page =
      Number.isFinite(parsedPage) && parsedPage > 0
        ? Math.floor(parsedPage)
        : 1;
  const updateFilters = (updates: Record<string, string>) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        Object.entries(updates).forEach(([key, value]) => {
          if (value) next.set(key, value);
          else next.delete(key);
        });
        return next;
      },
      { replace: true },
    );
  const fairs = useQuery({
    queryKey: ["public", "active-fairs"],
    queryFn: () =>
      api
        .get<ActiveFairsResponse>("/public/fairs/active")
        .then((response) => response.data),
  });
  const fair = fairs.data?.items.find((item) => item.id === fairId);
  const sectors = useQuery({
    queryKey: ["productive-sectors", "public"],
    queryFn: () =>
      api
        .get<Paged<ProductiveSector>>("/productive-sectors", {
          params: { per_page: 100 },
        })
        .then((response) => response.data.items),
  });
  const units = useQuery({
    queryKey: ["public", "fair-units", fairId, q, sector, department, page],
    enabled: Boolean(fair),
    queryFn: () =>
      api
        .get<Paged<ProductiveUnit>>("/public/productive-units", {
          params: {
            fair_id: fairId,
            q: q || undefined,
            sector_id: sector || undefined,
            departamento: department || undefined,
            page,
            per_page: 12,
          },
        })
        .then((response) => response.data),
  });
  const data = units.data ?? { items: [], pagination: emptyPagination };

  return (
    <PublicShell>
      <Link className="back-link fair-back-button" to="/catalogo">
        <ArrowLeft size={18} /> Todas las ferias
      </Link>
      {fairs.isLoading ? (
        <Loading />
      ) : !fair ? (
        <Empty
          title="La feria no está disponible"
          description="Puede haber finalizado o dejado de estar visible."
        />
      ) : (
        <>
          <section
            className={`fair-detail-banner${fair.imagen_portada ? " has-cover" : ""}`}
          >
            {fair.imagen_portada && (
              <img
                className="fair-detail-cover"
                src={assetUrl(fair.imagen_portada)}
                alt=""
              />
            )}
            <div className="fair-detail-shade" aria-hidden="true" />
            <div className="fair-detail-content">
              <span className="live-pill">
                <i /> Feria en curso
              </span>
              <h1>{fair.nombre}</h1>
              {fair.descripcion && <p>{fair.descripcion}</p>}
              <div className="fair-card-meta">
                <span>
                  <CalendarDays />
                  {displayDate(fair.fecha_inicio)} al{" "}
                  {displayDate(fair.fecha_fin)}
                </span>
                <span>
                  <MapPin />
                  {fair.ubicacion}
                </span>
              </div>
            </div>
          </section>
          <div className="section-heading">
            <div>
              <span className="eyebrow">Expositores</span>
              <h2>Unidades Productivas participantes</h2>
              <p>
                Entre al perfil de una unidad para conocer y consultar sus
                productos.
              </p>
            </div>
          </div>
          <div className="catalog-toolbar panel">
            <SearchField
              value={q}
              onChange={(value) => updateFilters({ q: value, pagina: "" })}
              placeholder="Buscar Unidad Productiva…"
            />
            <SearchableSelect
              value={sector}
              options={[
                { value: "", label: "Todos los sectores" },
                ...(sectors.data ?? []).map((item) => ({
                  value: item.id,
                  label: item.nombre,
                })),
              ]}
              onChange={(value) => updateFilters({ sector: value, pagina: "" })}
              placeholder="Todos los sectores"
              searchPlaceholder="Buscar sector…"
              ariaLabel="Filtrar por sector"
            />
            <SearchableSelect
              value={department}
              options={[
                { value: "", label: "Todos los departamentos" },
                ...BOLIVIA_DEPARTMENTS.map((item) => ({
                  value: item,
                  label: item,
                })),
              ]}
              onChange={(value) =>
                updateFilters({ departamento: value, pagina: "" })
              }
              placeholder="Todos los departamentos"
              searchPlaceholder="Buscar departamento…"
              ariaLabel="Filtrar por departamento"
            />
            <div className="catalog-filter-status">
              <span>
                <strong>{units.isLoading ? "…" : data.pagination.total}</strong>{" "}
                {data.pagination.total === 1
                  ? "expositor encontrado"
                  : "expositores encontrados"}
              </span>
              {(q || sector || department) && (
                <>
                  <div className="active-filter-chips">
                    {q && (
                      <button
                        onClick={() => updateFilters({ q: "", pagina: "" })}
                      >
                        Búsqueda: {q}
                        <span>×</span>
                      </button>
                    )}
                    {sector && (
                      <button
                        onClick={() =>
                          updateFilters({ sector: "", pagina: "" })
                        }
                      >
                        {sectors.data?.find((item) => item.id === sector)
                          ?.nombre ?? "Sector"}
                        <span>×</span>
                      </button>
                    )}
                    {department && (
                      <button
                        onClick={() =>
                          updateFilters({ departamento: "", pagina: "" })
                        }
                      >
                        {department}
                        <span>×</span>
                      </button>
                    )}
                  </div>
                  <button
                    className="clear-filters"
                    onClick={() => setSearchParams({}, { replace: true })}
                  >
                    Limpiar filtros
                  </button>
                </>
              )}
            </div>
          </div>
          {units.isLoading ? (
            <Loading label="Cargando expositores…" />
          ) : units.error ? (
            <ErrorBox message={apiError(units.error)} />
          ) : data.items.length ? (
            <>
              <div className="exhibitor-grid">
                {data.items.map((unit) => (
                  <article className="public-card exhibitor-card" key={unit.id}>
                    {unit.logo_url ? (
                      <img
                        className="card-media unit-logo"
                        src={assetUrl(unit.logo_url)}
                        alt={`Logo de ${unit.nombre_comercial}`}
                      />
                    ) : (
                      <CatalogPlaceholder
                        kind="unit"
                        name={unit.nombre_comercial}
                      />
                    )}
                    <div className="card-body">
                      <span className="sector-label">
                        {unit.sectores.map((item) => item.nombre).join(" · ") ||
                          "Producción nacional"}
                      </span>
                      <h3>{unit.nombre_comercial}</h3>
                      <p className="line-clamp">{unit.resena_comercial}</p>
                      <small>
                        <MapPin size={15} /> {unit.departamento}
                      </small>
                      <Link
                        className="btn-outline exhibitor-products-button"
                        to={`/catalogo/ferias/${fairId}/unidades/${unit.id}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`}
                      >
                        Ver productos <span aria-hidden="true">→</span>
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
              <PaginationBar
                pagination={data.pagination}
                onPageChange={(next) =>
                  updateFilters({ pagina: next > 1 ? String(next) : "" })
                }
              />
            </>
          ) : (
            <Empty
              title="No se encontraron expositores"
              description="Cambie los filtros para ver otras Unidades Productivas."
            />
          )}
        </>
      )}
    </PublicShell>
  );
}

export function PublicUnitPage() {
  const { fairId = "", unitId = "" } = useParams();
  const location = useLocation();
  const [cart, setCart] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<CanonicalProduct | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [showProductImage, setShowProductImage] = useState(false);
  const [showSelection, setShowSelection] = useState(false);
  const [showLogo, setShowLogo] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const unit = useQuery({
    queryKey: ["public", "fair-unit", fairId, unitId],
    queryFn: () =>
      api
        .get<ProductiveUnit>(`/public/productive-units/${unitId}`, {
          params: { fair_id: fairId },
        })
        .then((response) => response.data),
  });
  const selectedItems = useMemo(
    () => Object.entries(cart).filter(([, quantity]) => quantity > 0),
    [cart],
  );
  const selectedProducts = useMemo(
    () =>
      (unit.data?.productos ?? [])
        .map((product) => ({ product, quantity: cart[product.id] ?? 0 }))
        .filter((item) => item.quantity > 0),
    [cart, unit.data],
  );
  const selectedQuantity = useMemo(
    () => selectedProducts.reduce((total, item) => total + item.quantity, 0),
    [selectedProducts],
  );
  const selectedTotal = useMemo(
    () =>
      selectedProducts.reduce(
        (total, item) =>
          total + Number(item.product.precio_referencia) * item.quantity,
        0,
      ),
    [selectedProducts],
  );
  const selectedImages = useMemo(() => selected?.imagenes ?? [], [selected]);
  const changeQuantity = (id: string, value: number) =>
    setCart((current) => ({
      ...current,
      [id]: Math.max(0, Math.min(999, value)),
    }));
  const openProduct = (product: CanonicalProduct) => {
    const coverIndex = product.imagenes.findIndex(
      (image) => image.es_principal,
    );
    setSelected(product);
    setActiveImageIndex(coverIndex >= 0 ? coverIndex : 0);
    setShowProductImage(false);
  };
  const moveProductImage = (direction: number) =>
    setActiveImageIndex((current) =>
      selectedImages.length
        ? (current + direction + selectedImages.length) % selectedImages.length
        : 0,
    );
  useEffect(() => {
    if (!showProductImage || selectedImages.length < 2) return;
    const handle = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft")
        setActiveImageIndex(
          (current) =>
            (current - 1 + selectedImages.length) % selectedImages.length,
        );
      if (event.key === "ArrowRight")
        setActiveImageIndex((current) => (current + 1) % selectedImages.length);
    };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [showProductImage, selectedImages.length]);
  const sendWhatsApp = async () => {
    setSending(true);
    setSendError("");
    try {
      const response = await api.post<{ url: string }>("/public/whatsapp", {
        fair_id: fairId,
        items: selectedItems.map(([product_id, quantity]) => ({
          product_id,
          quantity,
        })),
      });
      window.open(response.data.url, "_blank", "noopener,noreferrer");
    } catch (error) {
      setSendError(apiError(error, "No se pudo abrir WhatsApp."));
    } finally {
      setSending(false);
    }
  };

  return (
    <PublicShell>
      <Link
        className="back-link fair-back-button"
        to={`/catalogo/ferias/${fairId}${location.search}`}
      >
        <ArrowLeft size={18} /> Volver a los expositores
      </Link>
      {unit.isLoading ? (
        <Loading label="Cargando productos…" />
      ) : unit.error || !unit.data ? (
        <ErrorBox
          message={apiError(
            unit.error,
            "La Unidad Productiva no está disponible en esta feria.",
          )}
        />
      ) : (
        <>
          <section className="unit-public-header">
            {unit.data.logo_url ? (
              <button
                type="button"
                className="unit-public-logo unit-public-logo-button"
                onClick={() => setShowLogo(true)}
                aria-label={`Ampliar imagen de ${unit.data.nombre_comercial}`}
              >
                <img
                  src={assetUrl(unit.data.logo_url)}
                  alt={`Logo de ${unit.data.nombre_comercial}`}
                />
              </button>
            ) : (
              <div className="unit-public-logo">
                <Factory />
              </div>
            )}
            <div>
              <span className="eyebrow">Unidad Productiva expositora</span>
              <h1>{unit.data.nombre_comercial}</h1>
              <p>{unit.data.resena_comercial}</p>
              <div className="unit-public-meta">
                <span>
                  <MapPin />
                  {unit.data.departamento}
                </span>
                <span>
                  <PackageSearch />
                  {unit.data.productos?.length ?? 0} productos disponibles
                </span>
              </div>
            </div>
          </section>
          <div className="section-heading">
            <div>
              <span className="eyebrow">Catálogo del expositor</span>
              <h2>Productos disponibles</h2>
              <p>
                Seleccione cantidades y envíe una consulta directa por WhatsApp.
              </p>
            </div>
          </div>
          <div className="product-grid">
            {unit.data.productos?.map((product) => {
              const image =
                product.imagenes.find((item) => item.es_principal) ??
                product.imagenes[0];
              const quantity = cart[product.id] ?? 0;
              return (
                <article
                  className={`product-card catalog-product-card${quantity > 0 ? " is-selected" : ""}`}
                  key={product.id}
                >
                  <button
                    className="product-image-button"
                    onClick={() => openProduct(product)}
                  >
                    {image ? (
                      <img
                        className="card-media"
                        src={assetUrl(image.url_imagen)}
                        alt={
                          image.texto_alternativo || product.nombre_comercial
                        }
                      />
                    ) : (
                      <CatalogPlaceholder
                        kind="product"
                        name={product.nombre_comercial}
                      />
                    )}
                  </button>
                  <div className="card-body">
                    <button
                      className="product-title"
                      onClick={() => openProduct(product)}
                    >
                      {product.nombre_comercial}
                    </button>
                    <p className="line-clamp">{product.descripcion_tecnica}</p>
                    <div className="product-card-purchase">
                      <strong className="price">
                        Bs {Number(product.precio_referencia).toFixed(2)}
                      </strong>
                      <div className="quantity-heading">
                        <span>Cantidad</span>
                        {quantity > 0 && <small>Seleccionado</small>}
                      </div>
                      <div className="quantity product-quantity">
                        <button
                          disabled={quantity === 0}
                          onClick={() =>
                            changeQuantity(product.id, quantity - 1)
                          }
                          aria-label={`Quitar ${product.nombre_comercial}`}
                        >
                          <Minus />
                        </button>
                        <strong aria-live="polite">{quantity}</strong>
                        <button
                          onClick={() =>
                            changeQuantity(product.id, quantity + 1)
                          }
                          aria-label={`Agregar ${product.nombre_comercial}`}
                        >
                          <Plus />
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          {sendError && <div className="selection-error">{sendError}</div>}
          {selectedItems.length > 0 && (
            <div className="selection-bar">
              <button
                type="button"
                className="selection-summary-trigger"
                onClick={() => setShowSelection(true)}
              >
                <ShoppingBag />
                <span>
                  <strong>
                    {selectedQuantity}{" "}
                    {selectedQuantity === 1 ? "unidad" : "unidades"}
                  </strong>
                  <small>
                    {selectedProducts.length}{" "}
                    {selectedProducts.length === 1 ? "producto" : "productos"} ·
                    Bs {selectedTotal.toFixed(2)}
                  </small>
                </span>
              </button>
              <button
                className="btn-secondary"
                disabled={sending}
                onClick={() => void sendWhatsApp()}
              >
                <MessageCircle />
                {sending ? "Preparando…" : "Consultar por WhatsApp"}
              </button>
              <button
                className="selection-clear"
                onClick={() => {
                  setCart({});
                  setShowSelection(false);
                }}
                aria-label="Vaciar selección"
              >
                ×
              </button>
            </div>
          )}
          {showLogo && unit.data.logo_url && (
            <Modal
              title={unit.data.nombre_comercial}
              onClose={() => setShowLogo(false)}
              wide
              className="unit-logo-preview-dialog"
            >
              <img
                src={assetUrl(unit.data.logo_url)}
                alt={`Imagen completa de ${unit.data.nombre_comercial}`}
              />
            </Modal>
          )}
          {showSelection && selectedProducts.length > 0 && (
            <Modal
              title="Resumen de la consulta"
              onClose={() => setShowSelection(false)}
              wide
              className="selection-summary-dialog"
            >
              <p className="selection-summary-intro">
                Revise productos y cantidades antes de continuar a WhatsApp.
              </p>
              <div className="selection-summary-list">
                {selectedProducts.map(({ product, quantity }) => {
                  const image =
                    product.imagenes.find((item) => item.es_principal) ??
                    product.imagenes[0];
                  return (
                    <article key={product.id}>
                      {image ? (
                        <img
                          src={assetUrl(image.url_imagen)}
                          alt={product.nombre_comercial}
                        />
                      ) : (
                        <div className="summary-image-placeholder">
                          <PackageSearch />
                        </div>
                      )}
                      <div className="selection-summary-copy">
                        <strong>{product.nombre_comercial}</strong>
                        <small>
                          Bs {Number(product.precio_referencia).toFixed(2)} por
                          unidad
                        </small>
                      </div>
                      <div className="quantity product-quantity summary-quantity">
                        <button
                          onClick={() =>
                            changeQuantity(product.id, quantity - 1)
                          }
                          aria-label={`Quitar ${product.nombre_comercial}`}
                        >
                          <Minus />
                        </button>
                        <strong>{quantity}</strong>
                        <button
                          onClick={() =>
                            changeQuantity(product.id, quantity + 1)
                          }
                          aria-label={`Agregar ${product.nombre_comercial}`}
                        >
                          <Plus />
                        </button>
                      </div>
                      <strong className="selection-line-total">
                        Bs{" "}
                        {(Number(product.precio_referencia) * quantity).toFixed(
                          2,
                        )}
                      </strong>
                      <button
                        className="selection-remove"
                        onClick={() => changeQuantity(product.id, 0)}
                        aria-label={`Eliminar ${product.nombre_comercial}`}
                      >
                        <Trash2 />
                      </button>
                    </article>
                  );
                })}
              </div>
              <div className="selection-summary-total">
                <span>
                  <small>Total referencial</small>
                  <strong>Bs {selectedTotal.toFixed(2)}</strong>
                </span>
                <div>
                  <button
                    className="btn-outline"
                    onClick={() => {
                      setCart({});
                      setShowSelection(false);
                    }}
                  >
                    Vaciar selección
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={sending}
                    onClick={() => void sendWhatsApp()}
                  >
                    <MessageCircle />
                    {sending ? "Preparando…" : "Continuar a WhatsApp"}
                  </button>
                </div>
              </div>
            </Modal>
          )}
          {selected && (
            <Modal
              title={selected.nombre_comercial}
              onClose={() => {
                setSelected(null);
                setShowProductImage(false);
              }}
              wide
              className="product-detail-dialog"
            >
              <div className="product-detail">
                <div className="detail-gallery">
                  {selectedImages.length ? (
                    <>
                      <div className="detail-image-stage">
                        <button
                          type="button"
                          className="detail-image-button"
                          onClick={() => setShowProductImage(true)}
                          aria-label="Ampliar imagen del producto"
                        >
                          <img
                            className="detail-image"
                            src={assetUrl(
                              selectedImages[activeImageIndex]?.url_imagen,
                            )}
                            alt={
                              selectedImages[activeImageIndex]
                                ?.texto_alternativo || selected.nombre_comercial
                            }
                          />
                        </button>
                        {selectedImages.length > 1 && (
                          <>
                            <button
                              type="button"
                              className="gallery-nav gallery-prev"
                              onClick={() => moveProductImage(-1)}
                              aria-label="Imagen anterior"
                            >
                              <ChevronLeft />
                            </button>
                            <button
                              type="button"
                              className="gallery-nav gallery-next"
                              onClick={() => moveProductImage(1)}
                              aria-label="Imagen siguiente"
                            >
                              <ChevronRight />
                            </button>
                          </>
                        )}
                        <span className="gallery-counter">
                          {activeImageIndex + 1} de {selectedImages.length}
                        </span>
                      </div>
                      <div className="thumbnail-row">
                        {selectedImages.map((image, index) => (
                          <button
                            type="button"
                            className={
                              index === activeImageIndex ? "active" : ""
                            }
                            key={image.id}
                            onClick={() => setActiveImageIndex(index)}
                            aria-label={`Ver imagen ${index + 1}`}
                          >
                            <img
                              src={assetUrl(image.url_imagen)}
                              alt={
                                image.texto_alternativo ||
                                `${selected.nombre_comercial}, imagen ${index + 1}`
                              }
                            />
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <CatalogPlaceholder
                      kind="product"
                      name={selected.nombre_comercial}
                      large
                    />
                  )}
                </div>
                <div className="detail-copy">
                  <span className="eyebrow">Producto boliviano</span>
                  <h2>{selected.nombre_comercial}</h2>
                  <p>{selected.descripcion_tecnica}</p>
                  <strong className="price detail-price">
                    Bs {Number(selected.precio_referencia).toFixed(2)}
                  </strong>
                  <dl>
                    <dt>Materia prima</dt>
                    <dd>{selected.materia_prima}</dd>
                    <dt>Presentación</dt>
                    <dd>{selected.presentacion_empaque}</dd>
                    <dt>Capacidad/stock</dt>
                    <dd>{selected.capacidad_produccion_stock}</dd>
                    {selected.dimensiones && (
                      <>
                        <dt>Dimensiones</dt>
                        <dd>{selected.dimensiones}</dd>
                      </>
                    )}
                  </dl>
                  <div
                    className={`modal-purchase-panel${
                      (cart[selected.id] ?? 0) > 0 ? " has-selection" : ""
                    }`}
                  >
                    <div className="modal-purchase-heading">
                      <div>
                        <span>Cantidad</span>
                        <small>
                          {(cart[selected.id] ?? 0) > 0
                            ? `${cart[selected.id]} ${(cart[selected.id] ?? 0) === 1 ? "unidad seleccionada" : "unidades seleccionadas"}`
                            : "Seleccione cuántas unidades desea consultar"}
                        </small>
                      </div>
                      {(cart[selected.id] ?? 0) > 0 && (
                        <strong>
                          Bs{" "}
                          {(
                            Number(selected.precio_referencia) *
                            (cart[selected.id] ?? 0)
                          ).toFixed(2)}
                        </strong>
                      )}
                    </div>
                    <div className="quantity modal-product-quantity">
                      <button
                        disabled={(cart[selected.id] ?? 0) === 0}
                        onClick={() =>
                          changeQuantity(
                            selected.id,
                            (cart[selected.id] ?? 0) - 1,
                          )
                        }
                        aria-label={`Quitar ${selected.nombre_comercial}`}
                      >
                        <Minus />
                      </button>
                      <strong aria-live="polite">
                        {cart[selected.id] ?? 0}
                      </strong>
                      <button
                        onClick={() =>
                          changeQuantity(
                            selected.id,
                            (cart[selected.id] ?? 0) + 1,
                          )
                        }
                        aria-label={`Agregar ${selected.nombre_comercial}`}
                      >
                        <Plus />
                      </button>
                    </div>
                    <button
                      className="btn-secondary modal-selection-done"
                      disabled={(cart[selected.id] ?? 0) === 0}
                      onClick={() => setSelected(null)}
                    >
                      <ShoppingBag />
                      {(cart[selected.id] ?? 0) > 0
                        ? "Guardar selección"
                        : "Seleccione una cantidad"}
                    </button>
                  </div>
                </div>
              </div>
            </Modal>
          )}
          {showProductImage && selected && selectedImages.length > 0 && (
            <Modal
              title={selected.nombre_comercial}
              onClose={() => setShowProductImage(false)}
              wide
              className="product-lightbox-dialog"
            >
              <div className="product-lightbox">
                <img
                  src={assetUrl(selectedImages[activeImageIndex]?.url_imagen)}
                  alt={
                    selectedImages[activeImageIndex]?.texto_alternativo ||
                    selected.nombre_comercial
                  }
                />
                {selectedImages.length > 1 && (
                  <>
                    <button
                      type="button"
                      className="lightbox-nav lightbox-prev"
                      onClick={() => moveProductImage(-1)}
                      aria-label="Imagen anterior"
                    >
                      <ChevronLeft />
                    </button>
                    <button
                      type="button"
                      className="lightbox-nav lightbox-next"
                      onClick={() => moveProductImage(1)}
                      aria-label="Imagen siguiente"
                    >
                      <ChevronRight />
                    </button>
                  </>
                )}
                <span>
                  {activeImageIndex + 1} de {selectedImages.length}
                </span>
              </div>
            </Modal>
          )}
        </>
      )}
    </PublicShell>
  );
}
