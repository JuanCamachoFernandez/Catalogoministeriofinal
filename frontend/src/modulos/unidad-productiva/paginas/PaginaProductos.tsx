import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageOff, Images, PackageOpen, Pencil, Plus, Trash2 } from "lucide-react";
import { errorApi, urlRecurso, paginacionVacia, type CanonicalProduct, type Paged } from "../../../compartido";
import {
  BotonConfirmacion,
  EstadoVacio,
  CajaError,
  Campo,
  EstadoCarga,
  Modal,
  BarraPaginacion,
  InsigniaEstado,
  useRetroalimentacion,
  useElementosPaginacionAdaptable,
} from "../../../compartido/componentes";
import { ModalImagenesProducto } from "../componentes/ModalImagenesProducto";
import { productoVacio, camposProducto } from "../constantes/formularioProducto";
import type { ErroresBorradorProducto } from "../tipos/formularioProducto";
import { validarBorradorProducto } from "../validaciones/formularioProducto";
import { servicioProductos } from "../servicios/servicioProductos";
import "../estilos/unidad-productiva.css";

const datosPagina = <T,>(value?: Paged<T>) =>
  value ?? { items: [], pagination: paginacionVacia };
const mensaje = (error: unknown) =>
  errorApi(error, "No se pudo completar la operación.");
const limpiar = (value: string) => value.trim() || null;
export function PaginaProductos({ admin = false }: { admin?: boolean }) {
  const [page, setPage] = useState(1),
    [editing, setEditing] = useState<CanonicalProduct | null>(null),
    [creating, setCreating] = useState(false),
    [draft, setDraft] = useState(productoVacio),
    [validationErrors, setValidationErrors] = useState<ErroresBorradorProducto>({}),
    [imagesFor, setImagesFor] = useState<CanonicalProduct | null>(null),
    [deletedProductIds, setDeletedProductIds] = useState<Set<string>>(
      () => new Set(),
    );
  const qc = useQueryClient(),
    feedback = useRetroalimentacion();
  const list = useQuery({
      queryKey: ["canonical-products", admin, page],
      queryFn: () => servicioProductos.list(page, admin ? 20 : 6, admin),
    }),
    data = datosPagina(list.data);
  const displayedProducts = useElementosPaginacionAdaptable(
    data.items,
    data.pagination,
    admin ? "admin" : "unidad-productiva",
  );
  const visibleProducts = displayedProducts.filter(
    (product) => !deletedProductIds.has(product.id),
  );
  const productLimit = 15;
  const productCount = admin ? 0 : data.pagination.total;
  const reachedProductLimit = !admin && productCount >= productLimit;
  const open = (p?: CanonicalProduct) => {
    if (!p && reachedProductLimit) {
      feedback.notify({
        title: "Límite de productos alcanzado",
        mensaje: `La unidad puede registrar como máximo ${productLimit} productos.`,
        tone: "warning",
      });
      return;
    }
    setValidationErrors({});
    setEditing(p ?? null);
    setCreating(!p);
    setDraft(
      p
        ? {
            nombre_comercial: p.nombre_comercial,
            descripcion_tecnica: p.descripcion_tecnica,
            materia_prima: p.materia_prima,
            dimensiones: p.dimensiones ?? "",
            colores_disponibles: p.colores_disponibles ?? "",
            certificaciones: p.certificaciones ?? "",
            presentacion_empaque: p.presentacion_empaque,
            precio_referencia: String(p.precio_referencia),
            capacidad_produccion_stock:
              p.capacidad_produccion_stock.match(/\d+/g)?.join("") ?? "",
          }
        : productoVacio,
    );
  };
  const save = async () => {
    const errors = validarBorradorProducto(draft);
    if (Object.keys(errors).length) {
      setValidationErrors(errors);
      feedback.error(
        "Revise el formulario",
        Object.values(errors)[0] ?? "Hay datos inválidos.",
      );
      return;
    }
    try {
      const payload = {
        ...draft,
        nombre_comercial: draft.nombre_comercial.trim(),
        descripcion_tecnica: draft.descripcion_tecnica.trim(),
        materia_prima: draft.materia_prima.trim(),
        presentacion_empaque: draft.presentacion_empaque.trim(),
        capacidad_produccion_stock: draft.capacidad_produccion_stock.trim(),
        dimensiones: limpiar(draft.dimensiones),
        colores_disponibles: limpiar(draft.colores_disponibles),
        certificaciones: limpiar(draft.certificaciones),
        precio_referencia: draft.precio_referencia,
      };
      if (editing)
        await servicioProductos.update(editing.id, payload);
      else await servicioProductos.create(payload);
      await qc.invalidateQueries({ queryKey: ["canonical-products"] });
      setEditing(null);
      setCreating(false);
      feedback.success("Producto guardado", draft.nombre_comercial);
    } catch (e) {
      feedback.error("No se pudo guardar", mensaje(e));
    }
  };
  return (
    <section
      id={admin ? undefined : "unidad-productiva-productos"}
      className={admin ? undefined : "unit-products-page"}
    >
      {admin ? (
        <div className="page-heading">
          <div>
            <span className="eyebrow">Oferta productiva</span>
              <h1>Productos registrados</h1>
              <p>
                Cada producto requiere al menos una imagen para ser publicable
                y admite un máximo de tres.
              </p>
          </div>
        </div>
      ) : (
        <header className="unit-products-hero">
          <div className="unit-products-hero-copy">
            <span className="unit-products-hero-icon">
              <PackageOpen size={29} />
            </span>
            <div>
              <span className="unit-products-kicker">OFERTA PRODUCTIVA</span>
              <h1>Mis productos</h1>
              <p>
                Administre la información, imágenes y disponibilidad de los
                productos que ofrece su unidad.
              </p>
            </div>
          </div>
          <div className="unit-products-hero-actions">
            <div
              className="unit-products-quota"
              aria-label={`${productCount} de ${productLimit} productos registrados`}
            >
              <div className="unit-products-quota-copy">
                <span>Productos registrados</span>
                <strong>
                  {productCount}
                  <small>/{productLimit}</small>
                </strong>
              </div>
              <div
                className="unit-products-quota-track"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={productLimit}
                aria-valuenow={Math.min(productCount, productLimit)}
              >
                <span
                  style={{
                    width: `${Math.min((productCount / productLimit) * 100, 100)}%`,
                  }}
                />
              </div>
            </div>
            <button
              className="unit-products-create-button"
              onClick={() => open()}
              disabled={reachedProductLimit}
              title={
                reachedProductLimit
                  ? `Límite máximo de ${productLimit} productos alcanzado`
                  : undefined
              }
            >
              <Plus size={19} />
              {reachedProductLimit ? "Límite alcanzado" : "Nuevo producto"}
            </button>
          </div>
        </header>
      )}
      {list.isLoading && !visibleProducts.length ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : visibleProducts.length ? (
        <>
          <div className="card-grid">
            {visibleProducts.map((p) => (
              <article
                className={`catalog-card ${admin ? "" : "unit-product-card"}`}
                key={p.id}
              >
                {!admin ? (
                  <div className="unit-product-media">
                    {p.imagenes[0] ? (
                      <img
                        src={urlRecurso(
                          p.imagenes.find((i) => i.es_principal)?.url_imagen ??
                            p.imagenes[0].url_imagen,
                        )}
                        alt={`Imagen principal de ${p.nombre_comercial}`}
                      />
                    ) : (
                      <div className="unit-product-media-placeholder">
                        <ImageOff size={36} />
                        <strong>Sin imágenes</strong>
                        <span>
                          Agregue fotografías para publicar el producto.
                        </span>
                      </div>
                    )}
                    <span className="unit-product-image-count">
                      <Images size={15} /> {p.imagenes.length}/3 imágenes
                    </span>
                  </div>
                ) : p.imagenes[0] ? (
                  <img
                    src={urlRecurso(
                      p.imagenes.find((i) => i.es_principal)?.url_imagen ??
                        p.imagenes[0].url_imagen,
                    )}
                    alt=""
                  />
                ) : null}
                <div className="card-body">
                  {!admin ? (
                    <div className="unit-product-status-row">
                      <InsigniaEstado value={p.estado} />
                      <span
                        className={`unit-product-publication ${p.publicable ? "is-publicable" : ""}`}
                      >
                        {p.publicable
                          ? "Visible en catálogo"
                          : "Pendiente de publicación"}
                      </span>
                    </div>
                  ) : (
                    <InsigniaEstado value={p.estado} />
                  )}
                  <h2>{p.nombre_comercial}</h2>
                  <p>{p.descripcion_tecnica}</p>
                  {!admin ? (
                    <div className="unit-product-price-row">
                      <span>Precio</span>
                      <strong>
                        Bs {Number(p.precio_referencia).toFixed(2)}
                      </strong>
                    </div>
                  ) : (
                    <strong>Bs {Number(p.precio_referencia).toFixed(2)}</strong>
                  )}
                  {admin && (
                    <small>
                      {p.imagenes.length}/3 imágenes ·{" "}
                      {p.publicable ? "Publicable" : "No publicable"}
                    </small>
                  )}
                  <div className="card-actions">
                    {!admin && (
                      <>
                        <button className="btn-small" onClick={() => open(p)}>
                          <Pencil size={16} /> Editar
                        </button>
                        <button
                          className="btn-small"
                          onClick={() => setImagesFor(p)}
                        >
                          <Images size={16} /> Imágenes
                        </button>
                        <BotonConfirmacion
                          className="btn-small btn-danger unit-product-delete-button"
                          question={`¿Eliminar permanentemente “${p.nombre_comercial}”? Esta acción no se puede deshacer.`}
                          onConfirm={async () => {
                            try {
                              await servicioProductos.remove(p.id);
                              setDeletedProductIds((current) => {
                                const next = new Set(current);
                                next.add(p.id);
                                return next;
                              });
                              if (data.items.length === 1 && page > 1) {
                                setPage((current) => current - 1);
                              }
                              await qc.invalidateQueries({
                                queryKey: ["canonical-products"],
                              });
                              feedback.success(
                                "Producto eliminado permanentemente",
                                p.nombre_comercial,
                              );
                            } catch (error) {
                              feedback.error(
                                "No se pudo eliminar el producto",
                                mensaje(error),
                              );
                            }
                          }}
                        >
                          <Trash2 size={16} /> Eliminar producto
                        </BotonConfirmacion>
                      </>
                    )}
                    <label className="product-status-field">
                      <span>Estado del producto</span>
                      <select
                        aria-label={`Estado de ${p.nombre_comercial}`}
                        className={`input compact product-status-select product-status-${p.estado.toLowerCase().replaceAll("_", "-")}`}
                        value={p.estado}
                        onChange={async (e) => {
                          try {
                            const updatedProduct = await servicioProductos.updateStatus(
                              p.id,
                              e.target.value,
                              admin,
                            );
                            qc.setQueryData<Paged<CanonicalProduct>>(
                              ["canonical-products", admin, page],
                              (current) =>
                                current
                                  ? {
                                      ...current,
                                      items: current.items.map((item) =>
                                        item.id === p.id ? updatedProduct : item,
                                      ),
                                    }
                                  : current,
                            );
                          } catch (error) {
                            feedback.error(
                              "No se pudo cambiar el estado",
                              mensaje(error),
                            );
                          }
                        }}
                      >
                        <option value="DRAFT">En preparación</option>
                        <option value="AVAILABLE">Disponible</option>
                        <option value="OUT_OF_STOCK">Agotado</option>
                        <option value="RETIRED">Retirado</option>
                      </select>
                    </label>
                  </div>
                </div>
              </article>
            ))}
          </div>
          <BarraPaginacion
            pagination={data.pagination}
            onPageChange={setPage}
            mobileLabel="Ver más productos"
            scrollTargetId="unidad-productiva-productos"
          />
        </>
      ) : !admin ? (
        <div className="unit-products-empty">
          <span>
            <PackageOpen size={38} />
          </span>
          <h2>Todavía no tiene productos</h2>
          <p>
            Registre el primer producto de su unidad para comenzar a preparar su
            catálogo.
          </p>
          <button
            className="unit-products-create-button"
            onClick={() => open()}
          >
            <Plus size={18} /> Crear primer producto
          </button>
        </div>
      ) : (
        <EstadoVacio title="No hay productos" />
      )}
      {(editing || creating) && (
        <Modal
          title={editing ? "Editar producto" : "Nuevo producto"}
          wide
          hideHeader
          className="product-editor-modal"
          onClose={() => {
            setEditing(null);
            setCreating(false);
            setValidationErrors({});
          }}
        >
          <div className="product-form-intro">
            <span>INFORMACIÓN DEL PRODUCTO</span>
            <h3>
              {editing
                ? "Actualice los datos comerciales"
                : "Registre un nuevo producto"}
            </h3>
            <p>
              Complete la información que verán los visitantes en el catálogo
              público.
            </p>
          </div>
          <div className="product-form-section-heading">
            <span>01</span>
            <div>
              <h3>Datos comerciales</h3>
              <p>Identificación, presentación, precio y disponibilidad.</p>
            </div>
          </div>
          <div className="form-grid product-form product-form-panel">
            {camposProducto.map((field) => {
              const { key } = field;
              return (
                <Campo
                  key={key}
                  label={field.label}
                  hint={field.hint}
                  hintAsHelp
                  required={field.required}
                  optional={!field.required}
                >
                  <input
                    className={`input ${validationErrors[key] ? "input-error" : ""}`}
                    aria-label={field.label}
                    required={field.required}
                    type={field.type ?? "text"}
                    inputMode={field.inputMode}
                    min={field.min}
                    step={field.step}
                    maxLength={field.maxLength}
                    placeholder={field.placeholder}
                    aria-invalid={Boolean(validationErrors[key])}
                    value={draft[key]}
                    onChange={(event) => {
                      let value = event.target.value;
                      if (key === "capacidad_produccion_stock")
                        value = value.replace(/\D/g, "");
                      if (key === "colores_disponibles")
                        value = value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]/g, "");
                      setDraft((current) => ({ ...current, [key]: value }));
                      setValidationErrors((current) => ({
                        ...current,
                        [key]: undefined,
                      }));
                    }}
                  />
                  {validationErrors[key] && (
                    <small className="field-error" role="alert">
                      {validationErrors[key]}
                    </small>
                  )}
                </Campo>
              );
            })}
          </div>
          <div className="product-form-section-heading product-description-heading">
            <span>02</span>
            <div>
              <h3>Descripción para el catálogo</h3>
              <p>Cuente qué caracteriza y diferencia a este producto.</p>
            </div>
          </div>
          <div className="product-form product-description-field product-form-panel">
            <Campo
              label="Descripción técnica"
              hint="Explique las características, elaboración y usos del producto."
              hintAsHelp
              required
            >
              <textarea
                className={`input ${validationErrors.descripcion_tecnica ? "input-error" : ""}`}
                aria-label="Descripción técnica"
                required
                rows={4}
                maxLength={5000}
                placeholder="Describa sus características, elaboración y usos principales."
                aria-invalid={Boolean(validationErrors.descripcion_tecnica)}
                value={draft.descripcion_tecnica}
                onChange={(event) => {
                  setDraft((current) => ({
                    ...current,
                    descripcion_tecnica: event.target.value,
                  }));
                  setValidationErrors((current) => ({
                    ...current,
                    descripcion_tecnica: undefined,
                  }));
                }}
              />
              {validationErrors.descripcion_tecnica && (
                <small className="field-error" role="alert">
                  {validationErrors.descripcion_tecnica}
                </small>
              )}
            </Campo>
          </div>
          <div className="product-form-footer">
            <p className="product-required-note">
              Los campos marcados con <strong>*</strong> son obligatorios.
            </p>
            <button className="btn" onClick={() => void save()}>
              {editing ? "Guardar cambios" : "Crear producto"}
            </button>
          </div>
        </Modal>
      )}
      {imagesFor && (
        <ModalImagenesProducto
          product={imagesFor}
          onClose={() => setImagesFor(null)}
          onChanged={() =>
            qc.invalidateQueries({ queryKey: ["canonical-products"] })
          }
        />
      )}
    </section>
  );
}
