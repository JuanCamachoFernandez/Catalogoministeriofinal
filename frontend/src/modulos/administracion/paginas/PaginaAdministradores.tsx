import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Pencil, Plus, Trash2, UserRoundCheck, UserRoundX, X } from "lucide-react";
import { createPortal } from "react-dom";
import { useEffect, useRef, useState } from "react";
import { api, type AdminUser, type Paged, type UserStatus } from "../../../compartido";
import {
  BarraPaginacion,
  BotonConfirmacion,
  CajaError,
  Campo,
  CampoBusqueda,
  EstadoCarga,
  EstadoVacio,
  InsigniaEstado,
  Modal,
  SelectorBuscable,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { datosPagina, limpiar, mensaje } from "../utilidades/administracionCompartida";
import {
  EMAIL_PATTERN,
  REPRESENTATIVE_NAME_PATTERN,
  sanearNombreRepresentante,
} from "../../registro/componentes/formularioRegistro";

type DraftAdmin = {
  first_name: string;
  apellido_paterno: string;
  apellido_materno: string;
  email: string;
  phone: string;
  cargo: string;
  unidad: string;
  observaciones: string;
};

type CreateAdminResponse = {
  message: string;
  data: AdminUser;
  username: string;
  temporary_password: string;
};

type ResetPasswordResponse = {
  message: string;
  username: string;
  temporary_password: string;
};

type CreatedCredentials = {
  firstName: string;
  username: string;
  temporaryPassword: string;
};

const ADMIN_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "ACTIVE", label: "Activos" },
  { value: "INACTIVE", label: "Inactivos" },
  { value: "LOCKED", label: "Bloqueados" },
  { value: "BLOCKED", label: "Suspendidos" },
];

const EMPTY_DRAFT: DraftAdmin = {
  first_name: "",
  apellido_paterno: "",
  apellido_materno: "",
  email: "",
  phone: "",
  cargo: "",
  unidad: "",
  observaciones: "",
};

const ADMIN_FIELD_LABELS: Record<keyof DraftAdmin, string> = {
  first_name: "Nombres",
  apellido_paterno: "Apellido paterno",
  apellido_materno: "Apellido materno",
  email: "Correo Electrónico",
  phone: "Teléfono",
  cargo: "Cargo",
  unidad: "Unidad",
  observaciones: "Observaciones",
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", {
    dateStyle: "medium",
  }).format(new Date(value));

const statusActionLabel = (status: UserStatus) =>
  status === "ACTIVE" ? "Inhabilitar temporalmente" : "Reactivar cuenta";

const statusNextValue = (status: UserStatus): UserStatus =>
  status === "ACTIVE" ? "INACTIVE" : "ACTIVE";

const statusQuestion = (admin: AdminUser) =>
  admin.status === "ACTIVE"
    ? `La cuenta de ${admin.first_name} ${admin.apellido_paterno ?? ""} quedara inhabilitada temporalmente y luego podrá reactivarse.`
    : `La cuenta de ${admin.first_name} ${admin.apellido_paterno ?? ""} volvera a estar activa.`;

function draftFromAdmin(admin: AdminUser): DraftAdmin {
  return {
    first_name: admin.first_name ?? "",
    apellido_paterno: admin.apellido_paterno ?? "",
    apellido_materno: admin.apellido_materno ?? "",
    email: admin.email ?? "",
    phone: admin.phone ?? "",
    cargo: admin.cargo ?? "",
    unidad: admin.unidad ?? "",
    observaciones: admin.observaciones ?? "",
  };
}

function AdministradorNombreCompleto({ admin }: { admin: AdminUser }) {
  return (
    <>
      {[admin.first_name, admin.apellido_paterno, admin.apellido_materno]
        .filter(Boolean)
        .join(" ")}
    </>
  );
}

export default function PaginaAdministradores() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<DraftAdmin>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<CreatedCredentials | null>(null);
  const [showCredentialsHelp, setShowCredentialsHelp] = useState(false);
  const credentialsHelpRef = useRef<HTMLButtonElement | null>(null);
  const [credentialsHelpPosition, setCredentialsHelpPosition] = useState({
    left: 16,
    top: 16,
    width: 320,
  });
  const formRef = useRef<HTMLFormElement | null>(null);
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
    queryKey: ["admin-users", q, status, page],
    queryFn: () =>
      api
        .get<Paged<AdminUser>>("/admin/users", {
          params: {
            role: "ADMIN",
            q: q || undefined,
            status: status || undefined,
            page,
            per_page: 10,
          },
        })
        .then((response) => response.data),
  });

  const data = datosPagina(list.data);

  const closeForm = () => {
    setCreating(false);
    setEditing(null);
    setSaving(false);
  };

  const updateDraft = <K extends keyof DraftAdmin>(field: K, value: DraftAdmin[K]) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };

  const focusInvalidControl = (
    control: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement,
    popupMessage: string,
  ) => {
    formRef.current
      ?.querySelectorAll<HTMLElement>('[aria-invalid="true"]')
      .forEach((item) => item.removeAttribute("aria-invalid"));
    control.setAttribute("aria-invalid", "true");
    control.scrollIntoView({ behavior: "smooth", block: "center" });
    control.focus({ preventScroll: true });
    feedback.notify({
      title: "Revise el campo marcado",
      mensaje: popupMessage,
      tone: "error",
      onClose: () => {
        control.scrollIntoView({ behavior: "smooth", block: "center" });
        control.focus({ preventScroll: true });
      },
    });
  };

  const fieldFromServerError = (error: unknown) => {
    const response = (
      error as {
        response?: {
          data?: { details?: Record<string, unknown>; error?: string };
        };
      }
    )?.response;
    const details = response?.data?.details;
    const detailedField = details ? Object.keys(details)[0] : "";
    if (detailedField) return detailedField;
    const errorMessage = (response?.data?.error ?? "").toLowerCase();
    if (errorMessage.includes("gmail") || errorMessage.includes("correo")) return "email";
    if (errorMessage.includes("apellido paterno")) return "apellido_paterno";
    if (errorMessage.includes("nombres")) return "first_name";
    return "";
  };

  const refreshList = async () => {
    await qc.invalidateQueries({ queryKey: ["admin-users"] });
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        first_name: draft.first_name.trim(),
        apellido_paterno: draft.apellido_paterno.trim(),
        apellido_materno: draft.apellido_materno.trim(),
        email: draft.email.trim().toLowerCase(),
        phone: limpiar(draft.phone),
        cargo: limpiar(draft.cargo),
        unidad: limpiar(draft.unidad),
        observaciones: limpiar(draft.observaciones),
        role: "ADMIN",
      };
      if (editing) {
        await api.patch(`/admin/users/${editing.id}`, payload);
        await refreshList();
        closeForm();
        feedback.success("Administrador actualizado", payload.email);
        return;
      }
      const response = await api.post<CreateAdminResponse>("/admin/users", payload);
      await refreshList();
      closeForm();
      setCreatedCredentials({
        firstName: response.data.data.first_name,
        username: response.data.username,
        temporaryPassword: response.data.temporary_password,
      });
      feedback.success("Administrador creado", response.data.data.email);
    } catch (error) {
      const fieldName = fieldFromServerError(error);
      const control = fieldName
        ? formRef.current?.querySelector<
            HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
          >(`[name="${fieldName}"]`)
        : null;
      if (control) {
        focusInvalidControl(control, mensaje(error));
        return;
      }
      feedback.error("No se pudo guardar", mensaje(error));
    } finally {
      setSaving(false);
    }
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const controls = Array.from(event.currentTarget.elements).filter(
      (
        element,
      ): element is
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement =>
        element instanceof HTMLInputElement ||
        element instanceof HTMLSelectElement ||
        element instanceof HTMLTextAreaElement,
    );
    const invalidControl = controls.find((control) => !control.validity.valid);
    if (invalidControl) {
      const label =
        ADMIN_FIELD_LABELS[invalidControl.name as keyof DraftAdmin] ?? "indicado";
      const popupMessage = invalidControl.validity.valueMissing
        ? `Complete el campo "${label}". Al cerrar este mensaje quedara marcado para que pueda corregirlo.`
        : `Revise el formato del campo "${label}". Al cerrar este mensaje quedara marcado para que pueda corregirlo.`;
      focusInvalidControl(invalidControl, popupMessage);
      return;
    }
    void save();
  };

  const changeStatus = async (admin: AdminUser) => {
    try {
      const nextStatus = statusNextValue(admin.status);
      await api.patch(`/admin/users/${admin.id}/status`, {
        status: nextStatus,
      });
      await refreshList();
      if (selected?.id === admin.id) {
        setSelected({
          ...admin,
          status: nextStatus,
        });
      }
      feedback.success(
        admin.status === "ACTIVE" ? "Cuenta inhabilitada temporalmente" : "Cuenta reactivada",
        admin.email,
      );
    } catch (error) {
      feedback.error("No se pudo cambiar el estado", mensaje(error));
    }
  };

  const removeAdmin = async (admin: AdminUser) => {
    try {
      await api.delete(`/admin/users/${admin.id}`);
      await refreshList();
      if (selected?.id === admin.id) setSelected(null);
      if (editing?.id === admin.id) closeForm();
      feedback.success("Administrador dado de baja", admin.email);
    } catch (error) {
      feedback.error("No se pudo eliminar", mensaje(error));
    }
  };

  const resendCredentials = async (admin: AdminUser) => {
    try {
      setCreatedCredentials(null);
      await api.post<ResetPasswordResponse>(
        `/admin/users/${admin.id}/reset-password`,
      );
      await refreshList();
      feedback.success(
        "Credenciales reenviadas",
        "Se generó una nueva contraseña temporal y fue enviada al correo registrado.",
      );
    } catch (error) {
      feedback.error("No se pudieron reenviar las credenciales", mensaje(error));
    }
  };

  if (creating || editing) {
    const currentAdmin = editing;

    return (
      <section className="admin-unit-registration-page admin-admins-form-page">
        <button
          type="button"
          className="back-navigation"
          onClick={closeForm}
        >
          {"← Volver al listado"}
        </button>

        <div className="registration-intro admin-admins-page-header">
          <div>
            <span className="eyebrow">Control de acceso</span>
            <h1>{currentAdmin ? "Editar administrador" : "Nuevo administrador"}</h1>
          </div>
        </div>

        <section className="admin-admins-form-panel">
          <form
            ref={formRef}
            className="registration-form admin-admins-form"
            noValidate
            onSubmit={submit}
            onInput={(event) =>
              (event.target as HTMLElement).removeAttribute("aria-invalid")
            }
          >
            <section className="registration-section">
              <div className="registration-section-heading">
                <span>1</span>
                <div>
                  <h2>Datos del administrador</h2>
                  <p>Completa la información base de la cuenta administrativa.</p>
                </div>
              </div>
              <div className="admin-admins-form-grid">
                <Campo label="Nombres" required>
                  <input
                    className="input"
                    name="first_name"
                    required
                    maxLength={100}
                    pattern={REPRESENTATIVE_NAME_PATTERN}
                    placeholder="Nombres del administrador"
                    value={draft.first_name}
                    onChange={(event) =>
                      updateDraft("first_name", sanearNombreRepresentante(event.target.value))
                    }
                  />
                </Campo>
                <Campo label="Apellido paterno" required>
                  <input
                    className="input"
                    name="apellido_paterno"
                    required
                    maxLength={100}
                    pattern={REPRESENTATIVE_NAME_PATTERN}
                    placeholder="Apellido paterno"
                    value={draft.apellido_paterno}
                    onChange={(event) =>
                      updateDraft("apellido_paterno", sanearNombreRepresentante(event.target.value))
                    }
                  />
                </Campo>
                <Campo label="Apellido materno" required>
                  <input
                    className="input"
                    name="apellido_materno"
                    required
                    maxLength={100}
                    pattern={REPRESENTATIVE_NAME_PATTERN}
                    placeholder="Apellido materno"
                    value={draft.apellido_materno}
                    onChange={(event) =>
                      updateDraft("apellido_materno", sanearNombreRepresentante(event.target.value))
                    }
                  />
                </Campo>
                <Campo label="Teléfono" optional>
                  <input
                    className="input"
                    name="phone"
                    type="tel"
                    inputMode="numeric"
                    maxLength={15}
                    pattern="[0-9]{7,15}"
                    placeholder="Ej. 70000000"
                    value={draft.phone}
                    onChange={(event) =>
                      updateDraft("phone", event.target.value.replace(/\D/g, "").slice(0, 15))
                    }
                  />
                </Campo>
                <Campo label="Correo Electrónico" required>
                  <input
                    className="input"
                    name="email"
                    type="email"
                    required
                    inputMode="email"
                    maxLength={255}
                    pattern={EMAIL_PATTERN}
                    placeholder="usuario@institucion.edu.bo"
                    value={draft.email}
                    onChange={(event) => updateDraft("email", event.target.value)}
                  />
                </Campo>
              </div>
            </section>

            <section className="registration-section">
              <div className="registration-section-heading">
                <span>2</span>
                <div>
                  <h2>Datos institucionales</h2>
                  <p>Registra el cargo, la unidad y cualquier observación de apoyo.</p>
                </div>
              </div>
              <div className="admin-admins-form-grid">
                <Campo label="Cargo" optional>
                  <input
                    className="input"
                    name="cargo"
                    maxLength={150}
                    placeholder="Cargo institucional"
                    value={draft.cargo}
                    onChange={(event) => updateDraft("cargo", event.target.value)}
                  />
                </Campo>
                <Campo label="Unidad" optional>
                  <input
                    className="input"
                    name="unidad"
                    maxLength={150}
                    placeholder="Unidad administrativa"
                    value={draft.unidad}
                    onChange={(event) => updateDraft("unidad", event.target.value)}
                  />
                </Campo>
                <Campo label="Observaciones" optional>
                  <textarea
                    className="input"
                    name="observaciones"
                    placeholder="Observaciones internas o contexto adicional"
                    value={draft.observaciones}
                    onChange={(event) => updateDraft("observaciones", event.target.value)}
                  />
                </Campo>
              </div>
            </section>

            <div className="registration-actions">
              <span>
                {currentAdmin
                  ? "Los cambios afectaran la cuenta administrativa inmediatamente."
                  : "Al crear la cuenta se generaran credenciales temporales para el primer ingreso."}
              </span>
              <div className="modal-actions admin-admins-modal-actions">
                <button
                  type="button"
                  className="admin-unit-action-button admin-unit-action-button-danger"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="admin-unit-action-button registration-submit"
                  disabled={
                    saving ||
                    !draft.first_name.trim() ||
                    !draft.apellido_paterno.trim() ||
                    !draft.apellido_materno.trim() ||
                    !draft.email.trim()
                  }
                >
                  {saving ? "Guardando..." : currentAdmin ? "Guardar cambios" : "Crear administrador"}
                </button>
              </div>
            </div>
          </form>
        </section>

        {createdCredentials && (
          <Modal
            title="Credenciales temporales"
            className="admin-sector-modal admin-admins-credentials-modal"
            onClose={() => setCreatedCredentials(null)}
          >
            <div className="admin-sector-modal-content admin-admins-credentials admin-admins-credentials-minimal">
              <p className="admin-sector-modal-intro">
                La cuenta de <strong>{createdCredentials.firstName}</strong> fue creada correctamente.
              </p>
              <div className="admin-admins-credentials-card">
                <p><strong>Usuario</strong><span>{createdCredentials.username}</span></p>
                <p><strong>Contraseña temporal</strong><span>{createdCredentials.temporaryPassword}</span></p>
              </div>
              <p className="admin-admins-credentials-hint">
                En el primer ingreso se pedira cambiar la contraseña.
              </p>
            </div>
          </Modal>
        )}
      </section>
    );
  }

  if (selected) {
    return (
      <article className="admin-unit-detail-page admin-admins-detail-page">
        <button
          type="button"
          className="back-navigation"
          onClick={() => {
            setCreatedCredentials(null);
            setSelected(null);
          }}
        >
          ← Volver al listado
        </button>

        <header className="admin-unit-detail-heading">
          <div className="admin-unit-detail-heading-main">
            <span className="eyebrow">Cuenta administrativa</span>
            <div className="admin-unit-detail-identity">
              <div className="admin-unit-detail-logo admin-unit-detail-logo-fallback">
                {selected.first_name.charAt(0)}
              </div>
              <div>
                <h1><AdministradorNombreCompleto admin={selected} /></h1>
                <p>@{selected.username}</p>
                <small>Registrado el {formatDate(selected.created_at)}</small>
              </div>
            </div>
          </div>
          <InsigniaEstado value={selected.status} />
        </header>

        <section className="admin-unit-detail-section">
          <h3>Datos de acceso</h3>
          <div className="admin-unit-detail-grid">
            <p>
              <span>Usuario</span>
              <strong>@{selected.username}</strong>
            </p>
            <p>
              <span>Correo Electrónico</span>
              <strong>{selected.email}</strong>
            </p>
          </div>
        </section>

        <section className="admin-unit-detail-section">
          <h3>Datos personales e institucionales</h3>
          <div className="admin-unit-detail-grid">
            <p>
              <span>Nombres</span>
              <strong>{selected.first_name}</strong>
            </p>
            <p>
              <span>Apellido paterno</span>
              <strong>{selected.apellido_paterno || "No registrado"}</strong>
            </p>
            <p>
              <span>Apellido materno</span>
              <strong>{selected.apellido_materno || "No registrado"}</strong>
            </p>
            <p>
              <span>Teléfono</span>
              <strong>{selected.phone || "No registrado"}</strong>
            </p>
            <p>
              <span>Unidad</span>
              <strong>{selected.unidad || "No registrada"}</strong>
            </p>
            <p>
              <span>Cargo</span>
              <strong>{selected.cargo || "No registrado"}</strong>
            </p>
          </div>
        </section>

        <section className="admin-unit-detail-section">
          <h3>Observaciones</h3>
          <div className="admin-unit-detail-grid">
            <div className="admin-unit-detail-card admin-unit-detail-wide">
              <span>Notas internas</span>
              <p>{selected.observaciones || "Sin observaciones registradas."}</p>
            </div>
          </div>
        </section>

        <section className="admin-request-review-section admin-request-decision-section">
          <div className="admin-request-decision-heading">
            <div className="admin-admins-credentials-heading">
              <h3>Credenciales de acceso</h3>
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
                          Puede regenerar una contraseña temporal y mostrar
                          nuevamente los datos de acceso cuando el usuario no
                          pueda ingresar al sistema.
                        </p>
                      </div>
                    </>,
                    document.body,
                  )
                ) : null}
              </div>
            </div>
          </div>
          <div className="admin-request-decision-confirmed">
            <p>La cuenta administrativa está registrada y disponible para gestionar su acceso.</p>
          <button
            type="button"
            className="admin-request-decision-button admin-request-resend-button"
            onClick={() => {
              void resendCredentials(selected);
            }}
            title="Restablece la contraseña temporal y muestra nuevamente las credenciales de acceso."
            >
              Reenviar credenciales
          </button>
          </div>
        </section>
      </article>
    );
  }

  return (
    <section className="admin-page admin-admins-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Control de acceso</span>
          <h1>Administradores</h1>
        </div>
        <button
          type="button"
          className="admin-units-create-button"
          onClick={() => {
            setCreatedCredentials(null);
            setSelected(null);
            setEditing(null);
            setDraft(EMPTY_DRAFT);
            setCreating(true);
          }}
        >
          <Plus aria-hidden="true" />
          Nuevo administrador
        </button>
      </div>

      <div className="toolbar admin-requests-toolbar admin-fairs-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar por nombre, usuario o correo..."
        />
        <SelectorBuscable
          value={status}
          options={ADMIN_STATUS_OPTIONS}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          placeholder="Todos los estados"
          searchPlaceholder="Buscar estado..."
          ariaLabel="Filtrar administradores por estado"
        />
      </div>

      {list.isLoading ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : data.items.length ? (
        <>
          <div className="table-wrap admin-requests-table admin-admins-table">
            <table>
              <thead>
                <tr>
                  <th>Administrador</th>
                  <th>Usuario</th>
                  <th>Correo</th>
                  <th>Estado</th>
                  <th>Registro</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((admin) => (
                  <tr key={admin.id}>
                    <td>
                      <div className="admin-admins-person-cell">
                        <strong>
                          {[admin.first_name, admin.apellido_paterno, admin.apellido_materno]
                            .filter(Boolean)
                            .join(" ")}
                        </strong>
                      </div>
                    </td>
                    <td>@{admin.username}</td>
                    <td>{admin.email}</td>
                    <td>
                      <InsigniaEstado value={admin.status} />
                    </td>
                    <td>{formatDate(admin.created_at)}</td>
                    <td>
                      <div className="admin-admins-actions">
                        <button
                          type="button"
                          className="btn-small"
                          onClick={() => {
                            setCreatedCredentials(null);
                            setSelected(admin);
                            setCreating(false);
                            setEditing(null);
                          }}
                          aria-label={`Ver ${admin.first_name}`}
                          title="Ver detalle"
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          type="button"
                          className="btn-small"
                          onClick={() => {
                            setSelected(null);
                            setCreating(false);
                            setDraft(draftFromAdmin(admin));
                            setEditing(admin);
                          }}
                          aria-label={`Editar ${admin.first_name}`}
                          title="Editar"
                        >
                          <Pencil size={16} />
                        </button>
                        <BotonConfirmacion
                          className={`btn-small ${
                            admin.status === "ACTIVE"
                              ? "admin-sector-action-disable"
                              : "admin-sector-action-enable"
                          }`}
                          question={statusQuestion(admin)}
                          confirmLabel={statusActionLabel(admin.status)}
                          onConfirm={() => {
                            void changeStatus(admin);
                          }}
                          title={statusActionLabel(admin.status)}
                        >
                          {admin.status === "ACTIVE" ? <UserRoundX size={16} /> : <UserRoundCheck size={16} />}
                        </BotonConfirmacion>
                        <BotonConfirmacion
                          className="btn-small admin-sector-action-disable"
                          question={`La cuenta de ${admin.first_name} ${admin.apellido_paterno ?? ""} se dara de baja y dejará de formar parte del sistema.`}
                          confirmLabel="Dar de baja"
                          onConfirm={() => {
                            void removeAdmin(admin);
                          }}
                          title="Dar de baja"
                        >
                          <Trash2 size={16} />
                        </BotonConfirmacion>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <BarraPaginacion pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <EstadoVacio
          title="No hay administradores registrados"
        />
      )}

      {createdCredentials && (
        <Modal
          title="Credenciales temporales"
          className="admin-sector-modal admin-admins-credentials-modal"
          onClose={() => setCreatedCredentials(null)}
        >
          <div className="admin-sector-modal-content admin-admins-credentials admin-admins-credentials-minimal">
            <p className="admin-sector-modal-intro">
              La cuenta de <strong>{createdCredentials.firstName}</strong> fue creada correctamente.
            </p>
            <div className="admin-admins-credentials-card">
              <p><strong>Usuario</strong><span>{createdCredentials.username}</span></p>
              <p><strong>Contraseña temporal</strong><span>{createdCredentials.temporaryPassword}</span></p>
            </div>
            <p className="admin-admins-credentials-hint">
              En el primer ingreso se pedira cambiar la contraseña.
            </p>
          </div>
        </Modal>
      )}
    </section>
  );
}
