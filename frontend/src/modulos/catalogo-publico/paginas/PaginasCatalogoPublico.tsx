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
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  errorApi,
  urlRecurso,
  paginacionVacia,
  type CanonicalProduct,
} from "../../../compartido";
import { BOLIVIA_DEPARTMENTS } from "../../../compartido/constantes/ubicacionesBolivia";
import { MarcadorCatalogo } from "../componentes/MarcadorCatalogo";
import { ImagenFeria } from "../componentes/ImagenFeria";
import { EstructuraPublica } from "../componentes/EstructuraPublica";
import { EnlacesSocialesUnidad } from "../componentes/EnlacesSocialesUnidad";
import { mostrarFecha } from "../utilidades/mostrarFecha";
import { servicioCatalogoPublico } from "../servicios/servicioCatalogoPublico";
import {
  EstadoVacio,
  CajaError,
  EstadoCarga,
  Modal,
  BarraPaginacion,
  SelectorBuscable,
  CampoBusqueda,
  usePaginacionMovil,
  useElementosPaginacionAdaptable,
} from "../../../compartido/componentes";

export function PaginaCatalogoPublico() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const fairs = useQuery({
    queryKey: ["public", "active-fairs", q, page],
    queryFn: () =>
      servicioCatalogoPublico.getActiveFairs({ page, perPage: 6, query: q }),
  });
  const data = fairs.data ?? {
    active: false,
    fair: null,
    items: [],
    pagination: paginacionVacia,
  };
  const displayedFairs = useElementosPaginacionAdaptable(
    data.items,
    data.pagination,
    q,
  );

  return (
    <EstructuraPublica>
      <div className="public-catalog-heading">
        <div>
          <h1>Ferias productivas en curso</h1>
          <p>
            Ingrese a una feria y descubra productos hechos en Bolivia por
            productores nacionales.
          </p>
        </div>
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar feria o ubicación…"
        />
      </div>
      {fairs.isLoading && !displayedFairs.length ? (
        <EstadoCarga label="Buscando ferias activas…" />
      ) : fairs.error ? (
        <CajaError mensaje={errorApi(fairs.error)} />
      ) : displayedFairs.length ? (
        <>
        <div className="fair-public-grid">
          {displayedFairs.map((fair) => (
            <article className="public-card fair-public-card" key={fair.id}>
              <ImagenFeria fair={fair} />
              <div className="card-body">
                <h2>{fair.nombre}</h2>
                <div className="fair-card-meta">
                  <span>
                    <CalendarDays />
                    {mostrarFecha(fair.fecha_inicio)} al{" "}
                    {mostrarFecha(fair.fecha_fin)}
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
        <BarraPaginacion
          pagination={data.pagination}
          onPageChange={setPage}
          mobileLabel="Ver más ferias"
        />
        </>
      ) : (
        <EstadoVacio
          title="No hay ferias activas en este momento"
          description="Vuelva pronto para conocer las próximas ferias productivas."
        />
      )}
    </EstructuraPublica>
  );
}

export function PaginaFeriaPublica() {
  const { fairId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const mobilePagination = usePaginacionMovil();
  const [mobilePage, setMobilePage] = useState(1);
  const pendingDesktopScroll = useRef(false);
  const q = searchParams.get("q") ?? "",
    sector = searchParams.get("sector") ?? "",
    department = searchParams.get("departamento") ?? "";
  const parsedPage = Number(searchParams.get("pagina") ?? 1),
    desktopPage =
      Number.isFinite(parsedPage) && parsedPage > 0
        ? Math.floor(parsedPage)
        : 1;
  const page = mobilePagination ? mobilePage : desktopPage;
  const updateFilters = (updates: Record<string, string>) => {
    if (Object.hasOwn(updates, "pagina") && !updates.pagina) setMobilePage(1);
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
  };
  const fairs = useQuery({
    queryKey: ["public", "active-fairs", "all"],
    queryFn: () => servicioCatalogoPublico.getActiveFairs(),
  });
  const fair = fairs.data?.items.find((item) => item.id === fairId);
  const sectors = useQuery({
    queryKey: ["productive-sectors", "public"],
    queryFn: servicioCatalogoPublico.getSectors,
  });
  const units = useQuery({
    queryKey: ["public", "fair-units", fairId, q, sector, department, page],
    enabled: Boolean(fair),
    queryFn: () =>
      servicioCatalogoPublico.getFairUnits({
        fairId,
        query: q,
        sectorId: sector,
        department,
        page,
      }),
  });
  const data = units.data ?? { items: [], pagination: paginacionVacia };
  const displayedUnits = useElementosPaginacionAdaptable(
    data.items,
    data.pagination,
    `${fairId}|${q}|${sector}|${department}`,
  );
  useEffect(() => {
    if (
      mobilePagination ||
      !pendingDesktopScroll.current ||
      units.data?.pagination.page !== page
    ) return;
    pendingDesktopScroll.current = false;
    window.requestAnimationFrame(() => {
      document.getElementById("unidades-productivas")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }, [mobilePagination, page, units.data?.pagination.page]);

  return (
    <EstructuraPublica>
      <Link className="back-link fair-back-button" to="/catalogo">
        <ArrowLeft size={18} /> Todas las ferias
      </Link>
      {fairs.isLoading ? (
        <EstadoCarga />
      ) : !fair ? (
        <EstadoVacio
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
                src={urlRecurso(fair.imagen_portada)}
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
                  {mostrarFecha(fair.fecha_inicio)} al{" "}
                  {mostrarFecha(fair.fecha_fin)}
                </span>
                <span>
                  <MapPin />
                  {fair.ubicacion}
                </span>
              </div>
            </div>
          </section>
          <div className="section-heading pagination-scroll-target" id="unidades-productivas">
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
            <CampoBusqueda
              value={q}
              onChange={(value) => updateFilters({ q: value, pagina: "" })}
              placeholder="Buscar Unidad Productiva…"
            />
            <SelectorBuscable
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
            <SelectorBuscable
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
                    onClick={() => {
                      setMobilePage(1);
                      setSearchParams({}, { replace: true });
                    }}
                  >
                    Limpiar filtros
                  </button>
                </>
              )}
            </div>
          </div>
          {units.isLoading && !displayedUnits.length ? (
            <EstadoCarga label="Cargando expositores…" />
          ) : units.error ? (
            <CajaError mensaje={errorApi(units.error)} />
          ) : displayedUnits.length ? (
            <>
              <div className="exhibitor-grid">
                {displayedUnits.map((unit) => (
                  <article className="public-card exhibitor-card" key={unit.id}>
                    {unit.logo_url ? (
                      <img
                        className="card-media unit-logo"
                        src={urlRecurso(unit.logo_url)}
                        alt={`Logo de ${unit.nombre_comercial}`}
                      />
                    ) : (
                      <MarcadorCatalogo
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
              <BarraPaginacion
                pagination={data.pagination}
                onPageChange={(next) => {
                  if (mobilePagination) setMobilePage(next);
                  else {
                    pendingDesktopScroll.current = true;
                    updateFilters({ pagina: next > 1 ? String(next) : "" });
                  }
                }}
                mobileLabel="Ver más unidades productivas"
                scrollOnDesktop={false}
              />
            </>
          ) : (
            <EstadoVacio
              title="No se encontraron expositores"
              description="Cambie los filtros para ver otras Unidades Productivas."
            />
          )}
        </>
      )}
    </EstructuraPublica>
  );
}

export function PaginaUnidadPublica() {
  const { fairId = "", unitId = "" } = useParams();
  const location = useLocation();
  const mobilePagination = usePaginacionMovil();
  const [productPage, setProductPage] = useState(1);
  const pendingProductScroll = useRef(false);
  const [cart, setCart] = useState<Record<string, number>>({});
  const [cartProducts, setCartProducts] = useState<
    Record<string, CanonicalProduct>
  >({});
  const [selected, setSelected] = useState<CanonicalProduct | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [showProductImage, setShowProductImage] = useState(false);
  const [showSelection, setShowSelection] = useState(false);
  const [showLogo, setShowLogo] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const unit = useQuery({
    queryKey: ["public", "fair-unit", fairId, unitId],
    queryFn: () => servicioCatalogoPublico.getFairUnit(fairId, unitId),
  });
  const products = useQuery({
    queryKey: ["public", "fair-unit-products", fairId, unitId, productPage],
    queryFn: () =>
      servicioCatalogoPublico.getFairUnitProducts(fairId, unitId, productPage),
  });
  const productData = products.data ?? {
    items: [],
    pagination: paginacionVacia,
  };
  const displayedProducts = useElementosPaginacionAdaptable(
    productData.items,
    productData.pagination,
    `${fairId}|${unitId}`,
  );
  useEffect(() => {
    if (
      mobilePagination ||
      !pendingProductScroll.current ||
      products.data?.pagination.page !== productPage
    ) return;
    pendingProductScroll.current = false;
    window.requestAnimationFrame(() => {
      document.getElementById("productos-unidad")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }, [mobilePagination, productPage, products.data?.pagination.page]);
  const selectedItems = useMemo(
    () => Object.entries(cart).filter(([, quantity]) => quantity > 0),
    [cart],
  );
  const selectedProducts = useMemo(
    () =>
      Object.entries(cart)
        .map(([id, quantity]) => ({ product: cartProducts[id], quantity }))
        .filter(
          (item): item is { product: CanonicalProduct; quantity: number } =>
            Boolean(item.product) && item.quantity > 0,
        ),
    [cart, cartProducts],
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
  const changeQuantity = (product: CanonicalProduct, value: number) => {
    const quantity = Math.max(0, Math.min(999, value));
    setCart((current) => ({ ...current, [product.id]: quantity }));
    setCartProducts((current) => {
      if (quantity > 0) return { ...current, [product.id]: product };
      const next = { ...current };
      delete next[product.id];
      return next;
    });
  };
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
      const url = await servicioCatalogoPublico.createWhatsAppUrl(
        fairId,
        selectedItems.map(([product_id, quantity]) => ({
          product_id,
          quantity,
        })),
      );
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (error) {
      setSendError(errorApi(error, "No se pudo abrir WhatsApp."));
    } finally {
      setSending(false);
    }
  };

  return (
    <EstructuraPublica>
      <Link
        className="back-link fair-back-button"
        to={`/catalogo/ferias/${fairId}${location.search}`}
      >
        <ArrowLeft size={18} /> Volver a los expositores
      </Link>
      {unit.isLoading ? (
        <EstadoCarga label="Cargando productos…" />
      ) : unit.error || !unit.data ? (
        <CajaError
          mensaje={errorApi(
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
                  src={urlRecurso(unit.data.logo_url)}
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
                  {unit.data.cantidad_productos_publicables ?? 0} productos disponibles
                </span>
              </div>
              <EnlacesSocialesUnidad unit={unit.data} />
            </div>
          </section>
          <div className="section-heading pagination-scroll-target" id="productos-unidad">
            <div>
              <span className="eyebrow">Catálogo del expositor</span>
              <h2>Productos disponibles</h2>
              <p>
                Seleccione cantidades y envíe una consulta directa por WhatsApp.
              </p>
            </div>
          </div>
          {products.isLoading && !displayedProducts.length ? (
            <EstadoCarga label="Cargando productos…" />
          ) : products.error ? (
            <CajaError mensaje={errorApi(products.error)} />
          ) : displayedProducts.length ? (
            <>
          <div className="product-grid">
            {displayedProducts.map((product) => {
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
                        src={urlRecurso(image.url_imagen)}
                        alt={
                          image.texto_alternativo || product.nombre_comercial
                        }
                      />
                    ) : (
                      <MarcadorCatalogo
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
                            changeQuantity(product, quantity - 1)
                          }
                          aria-label={`Quitar ${product.nombre_comercial}`}
                        >
                          <Minus />
                        </button>
                        <strong aria-live="polite">{quantity}</strong>
                        <button
                          onClick={() =>
                            changeQuantity(product, quantity + 1)
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
          <BarraPaginacion
            pagination={productData.pagination}
            onPageChange={(next) => {
              if (!mobilePagination) pendingProductScroll.current = true;
              setProductPage(next);
            }}
            mobileLabel="Ver más productos"
            scrollOnDesktop={false}
          />
            </>
          ) : (
            <EstadoVacio
              title="No hay productos disponibles"
              description="Esta Unidad Productiva todavía no tiene productos publicables."
            />
          )}
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
                src={urlRecurso(unit.data.logo_url)}
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
                          src={urlRecurso(image.url_imagen)}
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
                            changeQuantity(product, quantity - 1)
                          }
                          aria-label={`Quitar ${product.nombre_comercial}`}
                        >
                          <Minus />
                        </button>
                        <strong>{quantity}</strong>
                        <button
                          onClick={() =>
                            changeQuantity(product, quantity + 1)
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
                        onClick={() => changeQuantity(product, 0)}
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
                  setCartProducts({});
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
                            src={urlRecurso(
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
                              src={urlRecurso(image.url_imagen)}
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
                    <MarcadorCatalogo
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
                            selected,
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
                            selected,
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
                  src={urlRecurso(selectedImages[activeImageIndex]?.url_imagen)}
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
    </EstructuraPublica>
  );
}
