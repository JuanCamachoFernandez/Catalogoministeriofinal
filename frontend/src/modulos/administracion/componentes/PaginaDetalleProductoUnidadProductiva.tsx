import { ChevronLeft, ChevronRight, Expand } from "lucide-react";
import { useMemo, useState } from "react";
import { urlRecurso, type CanonicalProduct } from "../../../compartido";
import { EstadoVacio, Modal, InsigniaEstado } from "../../../compartido/componentes";

export function PaginaDetalleProductoUnidadProductiva({
  product,
  onBack,
}: {
  product: CanonicalProduct;
  onBack: () => void;
}) {
  const images = useMemo(
    () =>
      [...(product.imagenes ?? [])].sort(
        (a, b) => a.orden_visualizacion - b.orden_visualizacion,
      ),
    [product.imagenes],
  );
  const initialIndex = Math.max(
    0,
    images.findIndex((image) => image.es_principal),
  );
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");

  const selectedIndex = selectedImageId
    ? images.findIndex((image) => image.id === selectedImageId)
    : -1;
  const currentIndex = selectedIndex >= 0 ? selectedIndex : initialIndex;

  const currentImage = images[currentIndex] ?? null;
  const canNavigate = images.length > 1;
  const currentImageUrl = currentImage ? urlRecurso(currentImage.url_imagen) : "";

  const goToImage = (index: number) => {
    if (!images.length) return;
    const boundedIndex = (index + images.length) % images.length;
    setSelectedImageId(images[boundedIndex].id);
  };

  return (
    <article className="admin-unit-product-detail-page">
      <button type="button" className="back-navigation" onClick={onBack}>
        ← Volver a la unidad productiva
      </button>

      <header className="admin-unit-detail-heading">
        <div className="admin-unit-detail-heading-main">
          <span className="eyebrow">Detalle de producto</span>
          <div className="admin-unit-detail-identity">
            {currentImage ? (
              <img
                className="admin-unit-detail-logo admin-unit-product-detail-cover"
                src={urlRecurso(currentImage.url_imagen)}
                alt={product.nombre_comercial}
              />
            ) : (
              <div className="admin-unit-detail-logo admin-unit-detail-logo-fallback admin-unit-product-detail-cover">
                {product.nombre_comercial.charAt(0)}
              </div>
            )}
            <div>
              <h1>{product.nombre_comercial}</h1>
              <p>Bs {Number(product.precio_referencia).toFixed(2)}</p>
            </div>
          </div>
        </div>
        <InsigniaEstado value={product.estado} />
      </header>

      <section className="admin-unit-detail-section">
        <h3>Información general</h3>
        <div className="admin-unit-detail-grid">
          <p className="admin-unit-detail-wide">
            <span>Descripción técnica</span>
            <strong>{product.descripcion_tecnica}</strong>
          </p>
          <p>
            <span>Materia prima</span>
            <strong>{product.materia_prima}</strong>
          </p>
          <p>
            <span>Presentación o empaque</span>
            <strong>{product.presentacion_empaque}</strong>
          </p>
          <p>
            <span>Capacidad de producción o stock</span>
            <strong>{product.capacidad_produccion_stock}</strong>
          </p>
          <p>
            <span>Dimensiones</span>
            <strong>{product.dimensiones || "No registrado"}</strong>
          </p>
          <p>
            <span>Colores disponibles</span>
            <strong>{product.colores_disponibles || "No registrado"}</strong>
          </p>
          <p className="admin-unit-detail-wide">
            <span>Certificaciones</span>
            <strong>{product.certificaciones || "No registrado"}</strong>
          </p>
        </div>
      </section>

      <section className="admin-unit-detail-section">
        <div className="admin-unit-detail-section-heading">
          <div>
            <h3>Imágenes</h3>
            <p>{images.length} registradas</p>
          </div>
        </div>
        {currentImage ? (
          <div className="admin-unit-product-gallery">
            {canNavigate && (
              <div className="admin-unit-product-gallery-meta">
                <div className="admin-unit-product-gallery-dots" aria-label="Posición actual en la galería">
                  {images.map((image, index) => (
                    <span
                      key={image.id}
                      className={index === currentIndex ? "is-active" : ""}
                      aria-hidden="true"
                    />
                  ))}
                </div>
                <strong>
                  {currentIndex + 1} / {images.length}
                </strong>
              </div>
            )}
            <div className="admin-unit-product-gallery-stage">
              {canNavigate && (
                <button
                  type="button"
                  className="admin-unit-product-gallery-nav admin-unit-product-gallery-nav-prev"
                  onClick={() => goToImage(currentIndex - 1)}
                  aria-label="Ver imagen anterior"
                >
                  <ChevronLeft size={18} />
                </button>
              )}
              <button
                type="button"
                className="admin-unit-product-gallery-primary"
                onClick={() => setPreviewUrl(currentImageUrl)}
                title="Haga clic para ampliar"
                aria-label={`Ampliar imagen ${currentIndex + 1} de ${images.length}`}
              >
                <img
                  key={currentImage.id}
                  src={currentImageUrl}
                  alt={
                    currentImage.texto_alternativo ||
                    `${product.nombre_comercial} ${currentIndex + 1}`
                  }
                />
                <span className="admin-unit-product-gallery-hint">
                  <Expand size={16} />
                  Ampliar imagen
                </span>
              </button>
              {canNavigate && (
                <button
                  type="button"
                  className="admin-unit-product-gallery-nav admin-unit-product-gallery-nav-next"
                  onClick={() => goToImage(currentIndex + 1)}
                  aria-label="Ver imagen siguiente"
                >
                  <ChevronRight size={18} />
                </button>
              )}
            </div>

            {canNavigate && (
              <div className="admin-unit-product-gallery-strip" role="list">
                {images.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    role="listitem"
                    className={`admin-unit-product-gallery-thumb ${index === currentIndex ? "is-active" : ""}`}
                    onClick={() => goToImage(index)}
                    title={`Ver imagen ${index + 1}`}
                    aria-label={`Ver imagen ${index + 1}`}
                    aria-pressed={index === currentIndex}
                  >
                    <img
                      src={urlRecurso(image.url_imagen)}
                      alt={
                        image.texto_alternativo ||
                        `${product.nombre_comercial} ${index + 1}`
                      }
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <EstadoVacio title="Sin imágenes" />
        )}
      </section>

      {previewUrl && (
        <Modal
          title=""
          onClose={() => setPreviewUrl("")}
          wide
          className="admin-image-preview-modal"
        >
          <div className="image-preview-dialog">
            <img src={previewUrl} alt={`Imagen ampliada de ${product.nombre_comercial}`} />
          </div>
        </Modal>
      )}
    </article>
  );
}
