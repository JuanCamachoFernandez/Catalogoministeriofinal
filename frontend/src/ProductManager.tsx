import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, ImagePlus, PackagePlus, Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  api,
  apiError,
  assetUrl,
  emptyPagination,
  type Category,
  type Exhibitor,
  type Paged,
  type Product,
  type ProductImage,
  type ProductStatus,
} from "./api";
import {
  ConfirmButton,
  Empty,
  ErrorBox,
  Field,
  Loading,
  Modal,
  PaginationBar,
  SearchField,
  StatusBadge,
  UploadProgress,
  useFeedback,
  useResponsivePaginationItems,
} from "./ui";

type ProductDraft = {
  exhibitor_id: string;
  category_id: string;
  nombre: string;
  descripcion: string;
  estado: ProductStatus;
  materiales_o_ingredientes: string;
  lugar_origen: string;
  presentacion: string;
};

const blank: ProductDraft = {
  exhibitor_id: "",
  category_id: "",
  nombre: "",
  descripcion: "",
  estado: "AVAILABLE",
  materiales_o_ingredientes: "",
  lugar_origen: "",
  presentacion: "",
};
const fromProduct = (product: Product): ProductDraft => ({
  exhibitor_id: product.exhibitor_id,
  category_id: product.category_id,
  nombre: product.nombre,
  descripcion: product.descripcion,
  estado: product.estado,
  materiales_o_ingredientes: product.materiales_o_ingredientes ?? "",
  lugar_origen: product.lugar_origen ?? "",
  presentacion: product.presentacion ?? "",
});

function ProductForm({
  mode,
  product,
  categories,
  exhibitors,
  onClose,
}: {
  mode: "admin" | "exhibitor";
  product: Product | null;
  categories: Category[];
  exhibitors: Exhibitor[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [draft, setDraft] = useState<ProductDraft>(
    product ? fromProduct(product) : blank,
  );
  const [pending, setPending] = useState(false);
  const change = <K extends keyof ProductDraft>(
    key: K,
    value: ProductDraft[K],
  ) => setDraft((current) => ({ ...current, [key]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.category_id || !draft.nombre.trim() || !draft.descripcion.trim()) {
      feedback.error(
        "Faltan datos del producto",
        "Complete la categoría, el nombre y la descripción antes de guardar.",
      );
      return;
    }
    setPending(true);
    const base = mode === "admin" ? "/products" : "/exhibitor/products";
    const payload = {
      ...draft,
      precio: null,
      informacion_adicional: null,
      destacado: false,
      exhibitor_id: mode === "admin" ? draft.exhibitor_id : undefined,
    };
    try {
      if (product) await api.patch(`${base}/${product.id}`, payload);
      else await api.post(base, payload);
      await queryClient.invalidateQueries({ queryKey: ["products", mode] });
      onClose();
      feedback.success(
        product ? "Producto actualizado" : "Producto creado",
        product ? "Los cambios se guardaron correctamente." : "El producto fue guardado correctamente.",
      );
    } catch (reason) {
      feedback.error("No se pudo guardar el producto", apiError(reason, "Revise los datos e inténtelo nuevamente."));
    } finally {
      setPending(false);
    }
  };
  return (
    <Modal
      title={product ? "Editar producto" : "Nuevo producto"}
      onClose={onClose}
      wide
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        {mode === "admin" && !product && (
          <Field label="Expositor">
            <select
              className="input"
              required
              value={draft.exhibitor_id}
              onChange={(event) => change("exhibitor_id", event.target.value)}
            >
              <option value="">Seleccione…</option>
              {exhibitors.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre_comercial}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Categoría">
          <select
            className="input"
            required
            value={draft.category_id}
            onChange={(event) => change("category_id", event.target.value)}
          >
            <option value="">Seleccione…</option>
            {categories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nombre}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Nombre">
          <input
            className="input"
            required
            maxLength={200}
            value={draft.nombre}
            onChange={(event) => change("nombre", event.target.value)}
          />
        </Field>
        <Field label="Disponibilidad">
          <select
            className="input"
            value={draft.estado}
            onChange={(event) =>
              change("estado", event.target.value as ProductStatus)
            }
          >
            <option value="AVAILABLE">Disponible</option>
            <option value="OUT_OF_STOCK">Agotado</option>
            <option value="INACTIVE">Inactivo</option>
          </select>
        </Field>
        <Field label="Descripción">
          <textarea
            className="input"
            required
            rows={4}
            value={draft.descripcion}
            onChange={(event) => change("descripcion", event.target.value)}
          />
        </Field>
        <Field label="Materiales o ingredientes">
          <textarea
            className="input"
            rows={4}
            value={draft.materiales_o_ingredientes}
            onChange={(event) =>
              change("materiales_o_ingredientes", event.target.value)
            }
          />
        </Field>
        <Field label="Lugar de origen">
          <input
            className="input"
            maxLength={150}
            value={draft.lugar_origen}
            onChange={(event) => change("lugar_origen", event.target.value)}
          />
          <small>Indique dónde fue realizado o elaborado. Ejemplo: Achacachi, La Paz.</small>
        </Field>
        <Field label="Presentación">
          <input
            className="input"
            maxLength={150}
            value={draft.presentacion}
            onChange={(event) => change("presentacion", event.target.value)}
          />
          <small>Ejemplos: unidad, paquete de 500 g, tallas S/M/L o disponible en varios colores.</small>
        </Field>
        <div className="modal-actions full">
          <button type="button" className="btn-outline" onClick={onClose}>
            Cancelar
          </button>
          <button disabled={pending} className="btn">
            {pending ? "Guardando…" : "Guardar producto"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ImageManager({
  mode,
  product,
  onClose,
}: {
  mode: "admin" | "exhibitor";
  product: Product;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [current, setCurrent] = useState(product);
  const [file, setFile] = useState<File | null>(null);
  const [altText, setAltText] = useState("");
  const [filePreview, setFilePreview] = useState("");
  const [zoomedImage, setZoomedImage] = useState("");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState(0);
  useEffect(() => () => {
    if (filePreview.startsWith("blob:")) URL.revokeObjectURL(filePreview);
  }, [filePreview]);
  const refresh = async () => {
    const base = mode === "admin" ? "/products" : "/exhibitor/products";
    const { data } = await api.get<Product>(`${base}/${product.id}`);
    setCurrent(data);
    await queryClient.invalidateQueries({ queryKey: ["products", mode] });
    return data;
  };
  const upload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file || !altText.trim()) {
      feedback.error(
        "Faltan datos de la imagen",
        "Seleccione una imagen y complete el texto alternativo.",
      );
      return;
    }
    setPending(true);
    const form = new FormData();
    form.append("file", file);
    form.append("alt_text", altText);
    form.append("is_cover", String(current.imagenes.length === 0));
    const base =
      mode === "admin"
        ? `/products/${product.id}/images`
        : `/exhibitor/products/${product.id}/images`;
    try {
      await api.post(base, form, {
        onUploadProgress: (event) => {
          if (event.total)
            setProgress(Math.round((event.loaded * 100) / event.total));
        },
      });
      setFile(null);
      setAltText("");
      await refresh();
      setFilePreview("");
      feedback.success("Imagen subida correctamente", "Puede seleccionar otra imagen para agregarla al producto.");
    } catch (reason) {
      feedback.error("No se pudo cargar la imagen", apiError(reason, "Revise el archivo e inténtelo nuevamente."));
    } finally {
      setPending(false);
      setProgress(0);
    }
  };
  const update = async (image: ProductImage, patch: Partial<ProductImage>) => {
    try {
      await api.patch(`/product-images/${image.id}`, patch);
      await refresh();
      feedback.success("Imagen actualizada", patch.is_cover ? "La imagen ahora es la portada del producto." : "Los datos de la imagen se guardaron correctamente.");
    } catch (reason) {
      feedback.error("No se pudo actualizar la imagen", apiError(reason));
    }
  };
  const remove = async (image: ProductImage) => {
    try {
      await api.delete(`/product-images/${image.id}`);
      await refresh();
      feedback.success("Imagen eliminada", "La imagen fue retirada del producto.");
    } catch (reason) {
      feedback.error("No se pudo eliminar la imagen", apiError(reason));
    }
  };
  return (
    <Modal title={`Imágenes de ${product.nombre}`} onClose={onClose} wide>
      <form className="product-image-stage" onSubmit={upload} noValidate>
        <Field
          label="Nueva imagen"
          hint="Formatos de imagen admitidos por el servidor."
        >
          <input
            required
            type="file"
            accept="image/*"
            key={file?.name ?? "empty"}
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              if (!selected) return;
              if (!selected.type.startsWith("image/")) {
                event.target.value = "";
                feedback.error("Archivo no válido", "Seleccione únicamente una imagen.");
                return;
              }
              setFile(selected);
              setAltText("");
              setFilePreview(URL.createObjectURL(selected));
            }}
          />
        </Field>
        {file && filePreview && <>
        <button type="button" className="product-image-preview" onClick={() => setZoomedImage(filePreview)}>
          <img src={filePreview} alt="Vista previa de la nueva imagen" />
          <small>Haga clic para ampliar</small>
        </button>
        <Field label="Texto alternativo">
          <input
            className="input"
            required
            maxLength={255}
            value={altText}
            onChange={(event) => setAltText(event.target.value)}
            placeholder={`Ejemplo: ${product.nombre} vista frontal`}
          />
          <small>Describa brevemente la imagen para mejorar la accesibilidad.</small>
        </Field>
        <div className="image-auto-order" aria-live="polite">
          <strong>Imagen {current.imagenes.length + 1}</strong>
          <small>El orden se asignará automáticamente.</small>
        </div>
        <button className="btn" disabled={pending || !altText.trim()}>
          <ImagePlus /> {pending ? "Cargando…" : "Subir imagen"}
        </button>
        </>}
      </form>
      <UploadProgress value={progress} />
      <div className="image-admin-grid">
        {current.imagenes.map((image) => (
          <article key={image.id}>
            <button type="button" className="image-admin-preview" onClick={() => setZoomedImage(assetUrl(image.url))}>
              <img src={assetUrl(image.url)} alt={image.alt_text || product.nombre} />
              <small>Haga clic para ampliar</small>
            </button>
            <div className="image-admin-fields">
              <input
                className="input"
                defaultValue={image.alt_text ?? ""}
                onBlur={(event) =>
                  event.target.value !== (image.alt_text ?? "") &&
                  update(image, { alt_text: event.target.value })
                }
              />
              <div className="image-order-label">
                <strong>Imagen {image.display_order + 1}</strong>
                <small>Orden automático</small>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn-outline"
                  disabled={image.is_cover}
                  onClick={() => update(image, { is_cover: true })}
                >
                  <Star size={17} />{" "}
                  {image.is_cover ? "Portada" : "Hacer portada"}
                </button>
                <ConfirmButton
                  question="¿Eliminar esta imagen?"
                  onConfirm={() => remove(image)}
                >
                  <Trash2 size={17} />
                </ConfirmButton>
              </div>
            </div>
          </article>
        ))}
      </div>
      {!current.imagenes.length && (
        <Empty title="Este producto todavía no tiene imágenes" />
      )}
      {zoomedImage && (
        <Modal title="Vista ampliada de la imagen" onClose={() => setZoomedImage("")} wide>
          <div className="image-preview-dialog">
            <img src={zoomedImage} alt={product.nombre} />
            <div className="modal-actions"><button type="button" className="btn" onClick={() => setZoomedImage("")} autoFocus>OK</button></div>
          </div>
        </Modal>
      )}
    </Modal>
  );
}

export function ProductManager({ mode }: { mode: "admin" | "exhibitor" }) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [query, setQuery] = useState("");
  const [exhibitorId, setExhibitorId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [images, setImages] = useState<Product | null>(null);
  const endpoint = mode === "admin" ? "/products" : "/exhibitor/products";
  const products = useQuery({
    queryKey: ["products", mode, query, exhibitorId, categoryId, status, dateFrom, dateTo, page],
    queryFn: () =>
      api
        .get<Paged<Product>>(endpoint, {
          params: {
            q: query || undefined,
            exhibitor_id:
              mode === "admin" ? exhibitorId || undefined : undefined,
            category_id: mode === "admin" ? categoryId || undefined : undefined,
            estado: mode === "admin" ? status || undefined : undefined,
            date_from: mode === "admin" ? dateFrom || undefined : undefined,
            date_to: mode === "admin" ? dateTo || undefined : undefined,
            page,
          },
        })
        .then((response) => response.data),
  });
  const displayedProducts = useResponsivePaginationItems(
    products.data?.items ?? [],
    products.data?.pagination ?? emptyPagination,
    `${mode}|${query}|${exhibitorId}|${categoryId}|${status}|${dateFrom}|${dateTo}`,
  );
  const categories = useQuery({
    queryKey: ["categories", "active"],
    queryFn: () =>
      api
        .get<Paged<Category>>("/categories", { params: { per_page: 100 } })
        .then((response) => response.data.items),
  });
  const exhibitors = useQuery({
    queryKey: ["exhibitors", "options"],
    enabled: mode === "admin",
    queryFn: () =>
      api
        .get<Paged<Exhibitor>>("/exhibitors", { params: { per_page: 100 } })
        .then((response) => response.data.items),
  });
  const remove = async (product: Product) => {
    try {
      await api.delete(`${endpoint}/${product.id}`);
      await queryClient.invalidateQueries({ queryKey: ["products", mode] });
      feedback.success("Producto eliminado", `${product.nombre} fue retirado del catálogo.`);
    } catch (reason) {
      feedback.error("No se pudo eliminar el producto", apiError(reason));
    }
  };
  const quickStatus = async (product: Product, estado: ProductStatus) => {
    try {
      await api.patch(`${endpoint}/${product.id}`, { estado });
      await queryClient.invalidateQueries({ queryKey: ["products", mode] });
      const labels: Record<string, string> = { AVAILABLE: "disponible", OUT_OF_STOCK: "agotado", INACTIVE: "inactivo" };
      feedback.success("Disponibilidad actualizada", `${product.nombre} ahora figura como ${labels[estado] ?? estado}.`);
    } catch (reason) {
      feedback.error("No se pudo cambiar la disponibilidad", apiError(reason));
    }
  };
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">
            {mode === "admin" ? "Supervisión" : "Mi catálogo"}
          </span>
          <h1>{mode === "admin" ? "Productos" : "Mis productos"}</h1>
          <p>
            {mode === "admin"
              ? "Consulte la oferta publicada por todos los expositores."
              : "Mantenga actualizada la información que verán sus clientes."}
          </p>
        </div>
        {mode === "exhibitor" && (
          <button className="btn" onClick={() => setEditing("new")}>
            <PackagePlus /> Nuevo producto
          </button>
        )}
      </div>
      <div className="toolbar">
        <SearchField
          value={query}
          onChange={(value) => {
            setQuery(value);
            setPage(1);
          }}
          placeholder="Buscar producto…"
        />
        {mode === "admin" && (
          <>
          <select
            className="input"
            value={exhibitorId}
            onChange={(event) => {
              setExhibitorId(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos los expositores</option>
            {exhibitors.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nombre_comercial}
              </option>
            ))}
          </select>
          <select className="input" value={categoryId} onChange={(event) => { setCategoryId(event.target.value); setPage(1); }}><option value="">Todas las categorías</option>{categories.data?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select>
          <select className="input" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="AVAILABLE">Disponibles</option><option value="OUT_OF_STOCK">Agotados</option><option value="INACTIVE">Inactivos</option></select>
          <input className="input" type="date" aria-label="Productos desde" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} />
          <input className="input" type="date" aria-label="Productos hasta" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} />
          </>
        )}
      </div>
      {products.isLoading && !displayedProducts.length ? (
        <Loading />
      ) : products.error ? (
        <ErrorBox
          message={apiError(
            products.error,
            "No se pudieron cargar los productos.",
          )}
        />
      ) : displayedProducts.length ? (
        <>
          <div className="data-cards">
            {displayedProducts.map((product) => (
              <article className="data-card" key={product.id}>
                <div className="data-card-main">
                  {product.imagenes[0] ? (
                    <img
                      className="data-thumb"
                      src={assetUrl(product.imagenes[0].url)}
                      alt=""
                    />
                  ) : (
                    <div className="data-thumb placeholder">
                      <PackagePlus />
                    </div>
                  )}
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2>{product.nombre}</h2>
                      <StatusBadge value={product.estado} />
                    </div>
                    <p>
                      {mode === "admin" && (
                        <>
                          <strong>
                            {product.nombre_comercial ?? "Expositor desconocido"}
                          </strong>{" "}
                          ·{" "}
                        </>
                      )}
                      {product.categoria?.nombre ?? "Sin categoría"}
                    </p>
                  </div>
                </div>
                {mode === "exhibitor" && <div className="data-card-actions">
                  <select
                    className="input compact"
                    value={product.estado}
                    onChange={(event) =>
                      quickStatus(product, event.target.value as ProductStatus)
                    }
                  >
                    <option value="AVAILABLE">Disponible</option>
                    <option value="OUT_OF_STOCK">Agotado</option>
                    <option value="INACTIVE">Inactivo</option>
                  </select>
                  <button
                    className="btn-outline"
                    onClick={() => setImages(product)}
                  >
                    <ImagePlus size={17} /> Imágenes
                  </button>
                  <button
                    className="btn-outline"
                    onClick={() => setEditing(product)}
                  >
                    <Edit3 size={17} /> Editar
                  </button>
                  <ConfirmButton
                    question={`¿Eliminar ${product.nombre}? Esta acción lo retirará del catálogo.`}
                    onConfirm={() => remove(product)}
                  >
                    <Trash2 size={17} />
                  </ConfirmButton>
                </div>}
              </article>
            ))}
          </div>
          <PaginationBar
            pagination={products.data?.pagination ?? emptyPagination}
            onPage={setPage}
            mobileLabel="Ver más productos"
          />
        </>
      ) : (
        <Empty
          title="No hay productos"
          description="Cree el primer producto o cambie los filtros."
        />
      )}
      {mode === "exhibitor" && editing && (
        <ProductForm
          mode={mode}
          product={editing === "new" ? null : editing}
          categories={categories.data ?? []}
          exhibitors={exhibitors.data ?? []}
          onClose={() => setEditing(null)}
        />
      )}{" "}
      {mode === "exhibitor" && images && (
        <ImageManager
          mode={mode}
          product={images}
          onClose={() => setImages(null)}
        />
      )}
    </>
  );
}
