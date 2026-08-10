import { useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { createPortal } from "react-dom";
import { useEffect, useRef, useState } from "react";
import {
  api,
  urlRecurso,
  type Paged,
  type RegistrationRequest,
} from "../../../compartido";
import {
  EstadoVacio,
  CajaError,
  Campo,
  EstadoCarga,
  Modal,
  BarraPaginacion,
  CampoBusqueda,
  SelectorBuscable,
  InsigniaEstado,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { mensaje, datosPagina } from "../utilidades/administracionCompartida";

const REQUEST_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "PENDING", label: "Pendientes" },
  { value: "APPROVED", label: "Aprobadas" },
  { value: "REJECTED", label: "Rechazadas" },
];

export default function PaginaSolicitudesRegistro() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState<RegistrationRequest | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [logoPreview, setLogoPreview] = useState("");
  const [productPreview, setProductPreview] = useState<{
    url: string;
    name: string;
  } | null>(null);
  const [resenaPreview, setResenaPreview] = useState("");
  const [showCredentialsHelp, setShowCredentialsHelp] = useState(false);
  const credentialsHelpRef = useRef<HTMLButtonElement | null>(null);
  const [credentialsHelpPosition, setCredentialsHelpPosition] = useState({
    left: 16,
    top: 16,
    width: 320,
  });
  const qc = useQueryClient();
  const feedback = useRetroalimentacion();

  const updateCredentialsHelpPosition = () => {
    const triggerRect = credentialsHelpRef.current?.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 32);
    setCredentialsHelpPosition({
      width,
      left: triggerRect
        ? Math.min(Math.max(16, triggerRect.right - width), window.innerWidth - width - 16)
        : 16,
      top: triggerRect ? Math.min(Math.max(16, triggerRect.top), window.innerHeight - 180) : 16,
    });
  };

  useEffect(() => {
    if (!showCredentialsHelp) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowCredentialsHelp(false);
      }
    };
    window.addEventListener("resize", updateCredentialsHelpPosition);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("resize", updateCredentialsHelpPosition);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [showCredentialsHelp]);
  const list = useQuery({
    queryKey: ["registration-requests", q, estado, dateFrom, dateTo, page],
    queryFn: () =>
      api
        .get<Paged<RegistrationRequest>>("/admin/registration-requests", {
          params: {
            q: q || undefined,
            estado: estado || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            page,
            per_page: 10,
          },
        })
        .then((r) => r.data),
  });
  const act = async (path: string, payload?: object) => {
    try {
      await api.post(path, payload);
      await qc.invalidateQueries({ queryKey: ["registration-requests"] });
      setSelected(null);
      feedback.success("Operación completada", "La solicitud fue actualizada.");
    } catch (error) {
      feedback.error("No se pudo actualizar", mensaje(error));
    }
  };
  const data = datosPagina(list.data);
  return (
    <section className="admin-page admin-requests-page">
      {" "}
      <div className="page-heading">
        <div>
          <span className="eyebrow">Incorporación</span>
          <h1>Solicitudes de registro</h1>
        </div>
      </div>{" "}
      <div className="toolbar admin-requests-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar nombre, correo o NIT…"
        />
        <SelectorBuscable
          value={estado}
          options={REQUEST_STATUS_OPTIONS}
          onChange={(value) => {
            setEstado(value);
            setPage(1);
          }}
          placeholder="Todos los estados"
          searchPlaceholder="Buscar estado…"
          ariaLabel="Filtrar por estado"
        />
        <Campo label="Desde">
          <input
            className="input"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
          />
        </Campo>
        <Campo label="Hasta">
          <input
            className="input"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
          />
        </Campo>
      </div>{" "}
      {list.isLoading ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : data.items.length ? (
        <>
          <div className="table-wrap admin-requests-table">
            <table>
              <thead>
                <tr>
                  <th>Unidad Productiva</th>
                  <th>Contacto</th>
                  <th>Departamento</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.nombre_comercial}</strong>
                      <small>{item.razon_social}</small>
                    </td>
                    <td>{item.correo_electronico}</td>
                    <td>{item.departamento}</td>
                    <td>
                      <InsigniaEstado value={item.estado} />
                    </td>
                    <td>
                      <button
                        className="btn-small"
                        onClick={() => setSelected(item)}
                      >
                        Revisar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <BarraPaginacion pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <EstadoVacio title="No hay solicitudes" />
      )}{" "}
      {selected && (
        <article className="admin-request-review-page">
          {" "}
          <button
            type="button"
            className="back-navigation"
            onClick={() => setSelected(null)}
          >
            ← Volver a solicitudes
          </button>{" "}
          <header className="admin-request-review-heading">
            <div>
              <span className="eyebrow">Revisión de solicitud</span>
            </div>
            <InsigniaEstado value={selected.estado} />
          </header>{" "}
          <section className="admin-request-review-section">
            <h3>Datos de la unidad productiva</h3>
            <div className="admin-request-field-grid">
              <p>
                <span>Nombre comercial</span>
                <strong>{selected.nombre_comercial}</strong>
              </p>
              <p>
                <span>Razón social</span>
                <strong>{selected.razon_social}</strong>
              </p>
              <p>
                <span>NIT</span>
                <strong>{selected.nit || "No registrado"}</strong>
              </p>
              <p>
                <span>Registro SEPREC</span>
                <strong>{selected.registro_seprec || "No registrado"}</strong>
              </p>
              <p>
                <span>Registro PRO-BOLIVIA</span>
                <strong>
                  {selected.registro_pro_bolivia || "No registrado"}
                </strong>
              </p>
            </div>
          </section>{" "}
          <section className="admin-request-review-section">
            <h3>Representante y contacto</h3>
            <div className="admin-request-field-grid">
              <p>
                <span>Representante</span>
                <strong>{selected.nombre_representante}</strong>
              </p>
              <p>
                <span>Teléfono o WhatsApp</span>
                <strong>{selected.telefono_whatsapp}</strong>
              </p>
              <p>
                <span>Correo electrónico</span>
                <strong>{selected.correo_electronico}</strong>
              </p>
              <p>
                <span>Departamento</span>
                <strong>{selected.departamento}</strong>
              </p>
              <p>
                <span>Dirección física</span>
                <strong>{selected.direccion_fisica}</strong>
              </p>
            </div>
          </section>{" "}
          <section className="admin-request-review-section">
            <h3>Presencia digital</h3>
            <div className="admin-request-digital-layout">
              <div className="admin-request-logo-field">
                <span>Logotipo</span>
                {selected.logo_url ? (
                  <button
                    type="button"
                    className="admin-request-logo-button"
                    onClick={() => setLogoPreview(urlRecurso(selected.logo_url!))}
                    aria-label="Ver logotipo ampliado"
                  >
                    <img
                      className="detail-logo"
                      src={urlRecurso(selected.logo_url)}
                      alt={`Logo de ${selected.nombre_comercial}`}
                    />
                  </button>
                ) : (
                  <strong>No registrado</strong>
                )}
              </div>
              <div className="admin-request-social-grid">
                <p>
                  <span>Facebook</span>
                  {selected.facebook_url ? (
                    <a
                      href={selected.facebook_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {selected.facebook_url}
                    </a>
                  ) : (
                    <strong>No registrado</strong>
                  )}
                </p>
                <p>
                  <span>Instagram</span>
                  {selected.instagram_url ? (
                    <a
                      href={selected.instagram_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {selected.instagram_url}
                    </a>
                  ) : (
                    <strong>No registrado</strong>
                  )}
                </p>
                <p>
                  <span>TikTok</span>
                  {selected.tiktok_url ? (
                    <a
                      href={selected.tiktok_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {selected.tiktok_url}
                    </a>
                  ) : (
                    <strong>No registrado</strong>
                  )}
                </p>
              </div>
            </div>
          </section>{" "}
          <section className="admin-request-review-section">
            <h3>Actividad productiva</h3>
            <div className="admin-request-activity-grid">
              <div className="admin-request-info-card">
                <span>Sectores productivos</span>
                {selected.sectores.length ? (
                  <ul className="admin-request-sector-list">
                    {selected.sectores.map((sector) => (
                      <li key={sector.id}>
                        {sector.nombre}
                        {sector.detalle_otro && (
                          <small>{sector.detalle_otro}</small>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <strong>No registrado</strong>
                )}
              </div>
              <div className="admin-request-info-card admin-request-review-summary">
                <span>Reseña comercial</span>
                <p>{selected.resena_comercial}</p>
                {selected.resena_comercial.length > 220 && (
                  <button
                    type="button"
                    className="admin-request-expand-button"
                    onClick={() => setResenaPreview(selected.resena_comercial)}
                  >
                    Ver reseña completa
                  </button>
                )}
              </div>
            </div>
          </section>{" "}
          <section className="admin-request-review-section">
            <div className="admin-request-products-heading">
              <div>
                <h3>Productos registrados</h3>
                <p>Productos enviados para revisión de la solicitud.</p>
              </div>
              <strong>{selected.productos.length} de 3</strong>
            </div>
            <div className="admin-request-products">
              {selected.productos.map((product) => (
                <article key={product.id} className="admin-request-product">
                  <div className="admin-request-product-image">
                    <button
                      type="button"
                      className="admin-request-product-image-button"
                      onClick={() =>
                        setProductPreview({
                          url: urlRecurso(product.imagen_url),
                          name: product.nombre_comercial,
                        })
                      }
                      aria-label={`Ver imagen ampliada de ${product.nombre_comercial}`}
                    >
                      <img
                        src={urlRecurso(product.imagen_url)}
                        alt={product.nombre_comercial}
                      />
                    </button>
                  </div>
                  <div className="admin-request-product-fields">
                    <p>
                      <span>Nombre del producto</span>
                      <strong>{product.nombre_comercial}</strong>
                    </p>
                    <p>
                      <span>Precio de referencia</span>
                      <strong>
                        Bs {Number(product.precio_referencia).toFixed(2)}
                      </strong>
                    </p>
                    <p className="admin-request-field-wide">
                      <span>Reseña o descripción</span>
                      <strong>{product.descripcion_tecnica}</strong>
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </section>{" "}
          {selected.estado === "PENDING" && (
            <section className="admin-request-review-section admin-request-decision-section">
              <div className="admin-request-decision-heading">
                <div>
                  <h3>Decisión de la solicitud</h3>
                  <p>Apruebe la unidad o registre un motivo de rechazo.</p>
                </div>
              </div>
              <div className="admin-request-decision-grid">
                <article className="admin-request-decision-card admin-request-approve-card">
                  <h4>Aprobar solicitud</h4>
                  <p>
                    Al aprobar, se enviarán al correo de la Unidad Productiva
                    sus credenciales de acceso: usuario y contraseña.
                  </p>
                  <button
                    type="button"
                    className="admin-request-decision-button admin-request-approve-button"
                    onClick={() =>
                      void act(
                        `/admin/registration-requests/${selected.id}/approve`,
                        { observaciones: null },
                      )
                    }
                  >
                    Aprobar
                  </button>
                </article>
                <article className="admin-request-decision-card admin-request-reject-card">
                  <h4>Rechazar solicitud</h4>
                  <Campo label="Motivo de Rechazo">
                    <textarea
                      className="input"
                      rows={3}
                      value={rejectReason}
                      onChange={(event) => setRejectReason(event.target.value)}
                      placeholder="Motivo del rechazo"
                    />
                  </Campo>
                  <button
                    type="button"
                    className="admin-request-decision-button admin-request-reject-button"
                    disabled={!rejectReason.trim()}
                    onClick={() =>
                      void act(
                        `/admin/registration-requests/${selected.id}/reject`,
                        { motivo: rejectReason },
                      )
                    }
                  >
                    Rechazar
                  </button>
                </article>
              </div>
            </section>
          )}
          {selected.estado === "APPROVED" && (
            <section className="admin-request-review-section admin-request-decision-section">
              <div className="admin-request-decision-heading">
                <div className="admin-admins-credentials-heading">
                  <h3>Decisión de la solicitud</h3>
                  <div className="admin-admins-credentials-help">
                    <button
                      ref={credentialsHelpRef}
                      type="button"
                      className="admin-inline-help-button admin-admins-help-button"
                      aria-label="Mostrar ayuda sobre credenciales"
                      aria-expanded={showCredentialsHelp}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        updateCredentialsHelpPosition();
                        setShowCredentialsHelp((current) => !current);
                      }}
                    >
                      ?
                    </button>
                    {showCredentialsHelp ? (
                      createPortal(
                        <>
                          <button
                            type="button"
                            className="admin-inline-help-backdrop"
                            aria-label="Cerrar ayuda"
                            onClick={() => setShowCredentialsHelp(false)}
                          />
                          <div
                            className="admin-inline-help-card admin-admins-help-popover"
                            role="dialog"
                            aria-modal="true"
                            aria-label="Ayuda sobre credenciales"
                            style={credentialsHelpPosition}
                          >
                            <div className="admin-inline-help-card-header">
                              <button
                                type="button"
                                aria-label="Cerrar ayuda"
                                onClick={() => setShowCredentialsHelp(false)}
                              >
                                <X size={16} />
                              </button>
                            </div>
                            <p>
                              La solicitud ya fue aprobada. Aquí puede
                              regenerar una contraseña temporal y reenviar las
                              credenciales si la Unidad Productiva lo necesita.
                            </p>
                          </div>
                        </>,
                        document.body,
                      )
                    ) : null}
                  </div>
                </div>
                <InsigniaEstado value={selected.estado} />
              </div>
              <div className="admin-request-decision-confirmed">
                <p>Solicitud aprobada y lista para operar en el sistema.</p>
                <button
                  type="button"
                  className="admin-request-decision-button admin-request-resend-button"
                  title="Regenera una contraseña temporal y reenvía el usuario actual por correo."
                  onClick={() =>
                    void act(
                      `/admin/registration-requests/${selected.id}/resend-credentials`,
                    )
                  }
                >
                  Reenviar credenciales
                </button>
              </div>
            </section>
          )}{" "}
        </article>
      )}{" "}
      {logoPreview && (
        <Modal
          title=""
          onClose={() => setLogoPreview("")}
          wide
          className="admin-image-preview-modal"
        >
          <div className="image-preview-dialog">
            <img
              src={logoPreview}
              alt={`Logotipo ampliado de ${selected?.nombre_comercial ?? "la unidad productiva"}`}
            />
          </div>
        </Modal>
      )}{" "}
      {productPreview && (
        <Modal
          title=""
          onClose={() => setProductPreview(null)}
          wide
          className="admin-image-preview-modal"
        >
          <div className="image-preview-dialog">
            <img
              src={productPreview.url}
              alt={`Imagen ampliada de ${productPreview.name}`}
            />
          </div>
        </Modal>
      )}{" "}
      {resenaPreview && (
        <Modal
          title=""
          onClose={() => setResenaPreview("")}
          wide
          className="admin-text-preview-modal"
        >
          <div className="admin-text-preview-content">
            <span>Reseña comercial</span>
            <p>{resenaPreview}</p>
          </div>
        </Modal>
      )}{" "}
    </section>
  );
}
