import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  api,
  urlRecurso,
  type CanonicalProduct,
  type ProductiveUnit,
  type ProductiveUnitFairParticipation,
} from "../../../compartido";
import {
  BotonConfirmacion,
  CajaError,
  EstadoCarga,
  InsigniaEstado,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { mensaje } from "../utilidades/administracionCompartida";
import { SeccionParticipacionesUnidadProductiva } from "./SeccionParticipacionesUnidadProductiva";
import { PaginaDetalleProductoUnidadProductiva } from "./PaginaDetalleProductoUnidadProductiva";
import { SeccionProductosUnidadProductiva } from "./SeccionProductosUnidadProductiva";

const formatDate = (value?: string | null) => {
  if (!value) return "No registrado";
  const parsed = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(parsed);
};

export function PaginaDetalleUnidadProductiva({
  unitId,
  onBack,
  onChanged,
}: {
  unitId: string;
  onBack: () => void;
  onChanged: () => Promise<void> | void;
}) {
  const [selectedProduct, setSelectedProduct] = useState<CanonicalProduct | null>(
    null,
  );
  const qc = useQueryClient();
  const feedback = useRetroalimentacion();
  const unit = useQuery({
    queryKey: ["productive-unit-detail", unitId],
    queryFn: () =>
      api
        .get<ProductiveUnit>(`/admin/productive-units/${unitId}`)
        .then((response) => response.data),
  });
  const participations = useQuery({
    queryKey: ["productive-unit-participations", unitId],
    queryFn: () =>
      api
        .get<{ items: ProductiveUnitFairParticipation[] }>(
          `/admin/productive-units/${unitId}/participations`,
        )
        .then((response) => response.data.items),
  });

  const act = async (
    path: string,
    method: "post" | "delete" = "post",
    successMessage = "La operación se completó correctamente.",
  ) => {
    try {
      if (method === "delete") {
        await api.delete(path);
      } else {
        await api.post(path);
      }
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["productive-units"] }),
        qc.invalidateQueries({ queryKey: ["productive-unit-detail", unitId] }),
      ]);
      feedback.success("Operación completada", successMessage);
      await onChanged();
    } catch (error) {
      feedback.error("No se pudo actualizar", mensaje(error));
    }
  };

  if (unit.isLoading) return <EstadoCarga />;
  if (unit.error || !unit.data) {
    return <CajaError mensaje={mensaje(unit.error ?? "Unidad no encontrada")} />;
  }

  if (selectedProduct) {
    return (
      <PaginaDetalleProductoUnidadProductiva
        product={selectedProduct}
        onBack={() => setSelectedProduct(null)}
      />
    );
  }

  const products = unit.data.productos ?? [];
  const isDeleted = Boolean(unit.data.deleted_at);

  return (
    <article className="admin-unit-detail-page">
      <button type="button" className="back-navigation" onClick={onBack}>
        ← Volver al listado
      </button>

      <header className="admin-unit-detail-heading">
        <div className="admin-unit-detail-heading-main">
          <span className="eyebrow">Detalle de Unidad Productiva</span>
          <div className="admin-unit-detail-identity">
            {unit.data.logo_url ? (
              <img
                className="admin-unit-detail-logo"
                src={urlRecurso(unit.data.logo_url)}
                alt={`Logo de ${unit.data.nombre_comercial}`}
              />
            ) : (
              <div className="admin-unit-detail-logo admin-unit-detail-logo-fallback">
                {unit.data.nombre_comercial.charAt(0)}
              </div>
            )}
            <div>
              <h1>{unit.data.nombre_comercial}</h1>
              <p>{unit.data.razon_social}</p>
              <small>Se unió el {formatDate(unit.data.fecha_creacion)}</small>
            </div>
          </div>
        </div>
        <InsigniaEstado
          value={isDeleted ? "LOGICALLY_DELETED" : unit.data.estado}
        />
      </header>

      <section className="admin-unit-detail-section">
        <h3>Datos de la unidad</h3>
        <div className="admin-unit-detail-grid">
          <p>
            <span>NIT</span>
            <strong>{unit.data.nit || "No registrado"}</strong>
          </p>
          <p>
            <span>Registro SEPREC</span>
            <strong>{unit.data.registro_seprec || "No registrado"}</strong>
          </p>
          <p>
            <span>Registro PRO-BOLIVIA</span>
            <strong>{unit.data.registro_pro_bolivia || "No registrado"}</strong>
          </p>
        </div>
      </section>

      <section className="admin-unit-detail-section">
        <h3>Contacto y ubicación</h3>
        <div className="admin-unit-detail-grid">
          <p>
            <span>Nombres del representante</span>
            <strong>{unit.data.nombres_representante}</strong>
          </p>
          <p>
            <span>Apellido paterno</span>
            <strong>{unit.data.apellido_paterno_representante}</strong>
          </p>
          <p>
            <span>Apellido materno</span>
            <strong>{unit.data.apellido_materno_representante}</strong>
          </p>
          <p>
            <span>Departamento</span>
            <strong>{unit.data.departamento}</strong>
          </p>
          <p>
            <span>Teléfono o WhatsApp</span>
            <strong>{unit.data.telefono_whatsapp}</strong>
          </p>
          <p>
            <span>Correo electrónico</span>
            <strong>{unit.data.correo_electronico}</strong>
          </p>
          <p className="admin-unit-detail-wide">
            <span>Dirección física de la Planta de Producción o Taller</span>
            <strong>{unit.data.direccion_fisica}</strong>
          </p>
        </div>
      </section>

      <section className="admin-unit-detail-section">
        <h3>Presencia digital</h3>
        <div className="admin-unit-detail-grid">
          <p>
            <span>Facebook</span>
            {unit.data.facebook_url ? (
              <a
                href={unit.data.facebook_url}
                target="_blank"
                rel="noreferrer"
              >
                {unit.data.facebook_url}
              </a>
            ) : (
              <strong>No registrado</strong>
            )}
          </p>
          <p>
            <span>Instagram</span>
            {unit.data.instagram_url ? (
              <a
                href={unit.data.instagram_url}
                target="_blank"
                rel="noreferrer"
              >
                {unit.data.instagram_url}
              </a>
            ) : (
              <strong>No registrado</strong>
            )}
          </p>
          <p>
            <span>TikTok</span>
            {unit.data.tiktok_url ? (
              <a
                href={unit.data.tiktok_url}
                target="_blank"
                rel="noreferrer"
              >
                {unit.data.tiktok_url}
              </a>
            ) : (
              <strong>No registrado</strong>
            )}
          </p>
        </div>
      </section>

      <section className="admin-unit-detail-section">
        <h3>Actividad productiva</h3>
        <div className="admin-unit-detail-grid">
          <div className="admin-unit-detail-card admin-unit-detail-wide">
            <span>Sectores productivos</span>
            {unit.data.sectores.length ? (
              <ul className="admin-unit-detail-sector-list">
                {unit.data.sectores.map((sector) => (
                  <li key={sector.id}>
                    <strong>{sector.nombre}</strong>
                    {sector.detalle_otro && <small>{sector.detalle_otro}</small>}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No registrados</p>
            )}
          </div>
          <div className="admin-unit-detail-card admin-unit-detail-wide">
            <span>Reseña comercial</span>
            <p>{unit.data.resena_comercial}</p>
          </div>
        </div>
      </section>

      <SeccionProductosUnidadProductiva
        products={products}
        onSelectProduct={setSelectedProduct}
      />

      {participations.isLoading ? (
        <EstadoCarga label="Cargando participaciones..." />
      ) : participations.error ? (
        <CajaError mensaje={mensaje(participations.error)} />
      ) : (
        <SeccionParticipacionesUnidadProductiva
          participations={participations.data ?? []}
        />
      )}

      <section className="admin-unit-detail-section admin-unit-detail-actions">
        <BotonConfirmacion
          question="La unidad productiva y su cuenta quedarán inhabilitadas hasta que las restaures."
          onConfirm={() =>
            act(
              `/admin/productive-units/${unitId}`,
              "delete",
              "La unidad productiva fue inhabilitada correctamente.",
            )
          }
          className="admin-unit-action-button admin-unit-action-button-danger"
          title="Inhabilita la unidad productiva y su cuenta asociada sin borrarlas definitivamente."
          disabled={isDeleted}
        >
          Inhabilitar
        </BotonConfirmacion>
        <button
          type="button"
          className="admin-unit-action-button"
          disabled={!isDeleted}
          title={
            isDeleted
              ? "Restaura una unidad inhabilitada, reactiva su cuenta asociada y la deja operativa nuevamente."
              : "Restaurar solo aplica a unidades inhabilitadas."
          }
          onClick={() =>
            act(
              `/admin/productive-units/${unitId}/restore`,
              "post",
              "La unidad productiva fue restaurada correctamente.",
            )
          }
        >
          Restaurar
        </button>
      </section>
    </article>
  );
}
