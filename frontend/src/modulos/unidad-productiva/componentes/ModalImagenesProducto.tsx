import { useState } from "react";
import { ImagePlus, Star, Trash2 } from "lucide-react";
import { errorApi, urlRecurso, type CanonicalProduct } from "../../../compartido";
import { BotonConfirmacion, Modal, useRetroalimentacion } from "../../../compartido/componentes";
import { validarArchivoImagen } from "../../../compartido/validaciones/imagenes";
import { servicioProductos } from "../servicios/servicioProductos";

const mensaje = (error: unknown) =>
  errorApi(error, "No se pudo completar la operación.");
export function ModalImagenesProducto({
  product,
  onClose,
  onChanged,
}: {
  product: CanonicalProduct;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false),
    feedback = useRetroalimentacion();
  const refresh = async () => {
    onChanged();
  };
  return (
    <Modal
      title="Galería del producto"
      onClose={onClose}
      wide
      hideHeader
      className="product-images-modal"
    >
      <div className="product-images-intro">
        <div>
          <span>GESTIÓN DE IMÁGENES</span>
          <h3>{product.nombre_comercial}</h3>
          <p>
            Agregue al menos una imagen clara. Puede cargar hasta tres y elegir
            una como portada del producto.
          </p>
        </div>
        <div
          className="product-images-counter"
          aria-label={`${product.imagenes.length} de 3 imágenes cargadas`}
        >
          <strong>
            {product.imagenes.length}
            <small>/3</small>
          </strong>
          <span>imágenes</span>
        </div>
      </div>
      <div className="product-images-progress" aria-hidden="true">
        {[0, 1, 2].map((slot) => (
          <span
            key={slot}
            className={slot < product.imagenes.length ? "complete" : ""}
          />
        ))}
      </div>
      <div className="product-images-grid">
        {product.imagenes.map((img) => (
          <article
            key={img.id}
            className={`product-image-card ${img.es_principal ? "is-main" : ""}`}
          >
            <div className="product-image-frame">
              <img
                src={urlRecurso(img.url_imagen)}
                alt={img.texto_alternativo ?? "Imagen del producto"}
              />
              <span
                className={
                  img.es_principal
                    ? "product-image-main-badge"
                    : "product-image-number"
                }
              >
                {img.es_principal ? (
                  <>
                    <Star size={14} fill="currentColor" /> Portada
                  </>
                ) : (
                  `Imagen ${img.orden_visualizacion + 1}`
                )}
              </span>
            </div>
            <div className="product-image-card-copy">
              <strong>
                {img.es_principal
                  ? "Imagen principal"
                  : `Imagen ${img.orden_visualizacion + 1}`}
              </strong>
              <small>
                {img.es_principal
                  ? "Visible primero en el catálogo"
                  : "Imagen complementaria del producto"}
              </small>
            </div>
            <div className="product-image-actions">
              {!img.es_principal && (
                <button
                  className="image-main-button"
                  onClick={async () => {
                    await servicioProductos.setMainImage(product.id, img.id);
                    await refresh();
                    onClose();
                  }}
                >
                  <Star size={16} /> Usar como portada
                </button>
              )}
              <BotonConfirmacion
                className="image-delete-button"
                question="¿Eliminar esta imagen?"
                onConfirm={async () => {
                  await servicioProductos.removeImage(product.id, img.id);
                  await refresh();
                  onClose();
                }}
              >
                <Trash2 size={16} /> Eliminar
              </BotonConfirmacion>
            </div>
          </article>
        ))}
        {product.imagenes.length < 3 && (
          <label
            className={`product-image-upload-card ${busy ? "is-busy" : ""}`}
          >
            <span className="product-image-upload-icon">
              <ImagePlus size={28} />
            </span>
            <strong>{busy ? "Procesando y subiendo…" : "Agregar imagen"}</strong>
            <span>Seleccione una fotografía clara del producto.</span>
            <small>JPG, PNG o WebP · Máximo 10 MB</small>
            <span className="product-image-upload-button">
              {busy ? "Procesando localmente…" : "Seleccionar archivo"}
            </span>
            <input
              disabled={busy}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={async (event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                const validation = validarArchivoImagen(file, {
                  label: "la imagen del producto",
                });
                if (!validation.ok) {
                  feedback.error(validation.title, validation.message);
                  event.target.value = "";
                  return;
                }
                setBusy(true);
                try {
                  await servicioProductos.uploadImage(product.id, file, {
                    alt_text: `Imagen de ${product.nombre_comercial}`,
                  });
                  await refresh();
                  onClose();
                } catch (error) {
                  feedback.error("No se pudo cargar", mensaje(error));
                } finally {
                  setBusy(false);
                  event.target.value = "";
                }
              }}
            />
          </label>
        )}
      </div>
      <div className="product-images-tip">
        <strong>Consejo:</strong> use buena iluminación y evite texto pequeño o
        fondos que distraigan.
      </div>
    </Modal>
  );
}


