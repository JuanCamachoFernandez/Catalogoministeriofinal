import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CalendarDays,
  Edit3,
  ImagePlus,
  KeyRound,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Store,
  Trash2,
  UserCheck,
  UserX,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  apiError,
  assetUrl,
  emptyPagination,
  uploadFile,
  type AdminUser,
  type Assignment,
  type AssignmentStatus,
  type AuditItem,
  type Category,
  type Exhibitor,
  type Fair,
  type FairStatus,
  type Paged,
  type UserRole,
} from "./api";
import { useAuth } from "./AuthContext";
import { ProductManager } from "./ProductManager";
import {
  gmailAddress,
  gmailLocalPart,
  responsibleDisplayName,
} from "./adminUserUtils";
import {
  BOLIVIA_DEPARTMENTS,
  municipalitiesFor,
} from "./boliviaLocations";
import {
  ConfirmButton,
  Empty,
  ErrorBox,
  Field,
  Loading,
  Modal,
  PaginationBar,
  SearchField,
  SearchableSelect,
  StatusBadge,
  UploadProgress,
  useFeedback,
} from "./ui";

function Header({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function LocationFields({
  department,
  municipality,
  onDepartment,
  onMunicipality,
}: {
  department: string;
  municipality: string;
  onDepartment: (value: string) => void;
  onMunicipality: (value: string) => void;
}) {
  const municipalities = municipalitiesFor(department);
  return (
    <>
      <Field label="Departamento">
        <SearchableSelect
          value={department}
          options={BOLIVIA_DEPARTMENTS.map((item) => ({
            value: item,
            label: item,
          }))}
          placeholder="Seleccione un departamento"
          searchPlaceholder="Buscar departamento…"
          ariaLabel="Departamento"
          onChange={(value) => {
            onDepartment(value);
            if (!municipalitiesFor(value).includes(municipality))
              onMunicipality("");
          }}
        />
      </Field>
      <Field label="Municipio">
        <SearchableSelect
          disabled={!BOLIVIA_DEPARTMENTS.includes(department)}
          value={municipality}
          options={municipalities.map((item) => ({ value: item, label: item }))}
          placeholder="Seleccione un municipio"
          searchPlaceholder="Buscar municipio…"
          ariaLabel="Municipio"
          onChange={onMunicipality}
        />
      </Field>
    </>
  );
}

type CreatedCredentials = {
  username: string;
  password: string;
};

type CredentialsDialog = {
  title: string;
  credentials: CreatedCredentials;
};

function CredentialsModal({
  title,
  credentials,
  onClose,
}: {
  title: string;
  credentials: CreatedCredentials;
  onClose: () => void;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="credentials-modal-content">
        <div className="credentials-success-icon" aria-hidden="true">
          <UserCheck />
        </div>
        <p>Guarde estas credenciales para iniciar sesión.</p>
        <dl className="credentials-box">
          <div>
            <dt>Usuario</dt>
            <dd>{credentials.username}</dd>
          </div>
          <div>
            <dt>Contraseña</dt>
            <dd>{credentials.password}</dd>
          </div>
        </dl>
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose} autoFocus>
            Entendido
          </button>
        </div>
      </div>
    </Modal>
  );
}

export function AdminDashboard() {
  const dashboard = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () =>
      api.get("/admin/dashboard").then((response) => response.data),
  });
  if (dashboard.isLoading) return <Loading />;
  if (dashboard.error)
    return (
      <ErrorBox
        message={apiError(dashboard.error, "No se pudo cargar el resumen.")}
      />
    );
  const stats = dashboard.data.stats;
  const cards = [
    ["Ferias publicadas", stats.ferias_publicadas, CalendarDays],
    ["Ferias", stats.ferias, CalendarDays],
    ["Expositores activos", stats.expositores_activos, Store],
    ["Productos", stats.productos, Store],
    ["Disponibles", stats.productos_disponibles, UserCheck],
    ["Agotados", stats.productos_sin_stock, UserX],
    ["Asignaciones pendientes", stats.asignaciones_pendientes, Users],
  ];
  return (
    <>
      <Header
        eyebrow="Administración"
        title="Resumen general"
        description="Estado actual de la plataforma y actividad reciente."
      />
      <div className="stats-grid">
        {cards.map(([label, value, Icon]) => (
          <article className="stat-card" key={String(label)}>
            <Icon />
            <div>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          </article>
        ))}
      </div>
      <section className="panel">
        <h2>
          <Activity /> Actividad reciente
        </h2>
        {dashboard.data.recent_audits.length ? (
          <div className="activity-list">
            {dashboard.data.recent_audits.map((item: AuditItem) => (
              <article key={item.id}>
                <span className="activity-dot" />
                <div>
                  <strong>
                    {item.accion} · {item.entidad}
                  </strong>
                  <p>{item.descripcion || "Sin descripción"}</p>
                  <time>
                    {new Date(item.created_at).toLocaleString("es-BO")}
                  </time>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty title="Todavía no se registró actividad" />
        )}
      </section>
    </>
  );
}

type AdminDraft = {
  first_name: string;
  apellido_paterno: string;
  apellido_materno: string;
  numero_documento: string;
  gmail_user: string;
  phone: string;
  cargo: string;
  unidad: string;
  observaciones: string;
  role: UserRole;
};
const blankAdmin: AdminDraft = {
  first_name: "",
  apellido_paterno: "",
  apellido_materno: "",
  numero_documento: "",
  gmail_user: "",
  phone: "",
  cargo: "",
  unidad: "",
  observaciones: "",
  role: "ADMIN_VICEMINISTERIO",
};

function AdminForm({
  user,
  onClose,
  onCreated,
}: {
  user: AdminUser | null;
  onClose: () => void;
  onCreated: (credentials: CreatedCredentials) => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const units = useQuery({
    queryKey: ["admin-units"],
    queryFn: () =>
      api
        .get<{ items: { id: string; nombre: string }[] }>("/admin/units")
        .then((response) => response.data.items),
  });
  const [draft, setDraft] = useState<AdminDraft>(
    user
      ? {
          first_name: user.first_name,
          apellido_paterno: user.apellido_paterno ?? user.last_name,
          apellido_materno: user.apellido_materno ?? "",
          numero_documento: user.numero_documento ?? "",
          gmail_user: gmailLocalPart(user.email),
          phone: user.phone ?? "",
          cargo: user.cargo ?? "",
          unidad: user.unidad ?? "",
          observaciones: "",
          role: user.role,
        }
      : blankAdmin,
  );
  const [pending, setPending] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    try {
      const { gmail_user, role, ...fields } = draft;
      const basePayload = { ...fields, email: gmailAddress(gmail_user) };
      if (user) {
        await api.patch(`/admin/users/${user.id}`, basePayload);
        feedback.success(
          "Administrador actualizado",
          "Los cambios se guardaron correctamente.",
        );
      }
      else {
        const payload = { ...basePayload, role };
        const { data } = await api.post<{
          username: string;
          temporary_password: string;
        }>("/admin/users", payload);
        onCreated({
          username: data.username,
          password: data.temporary_password,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ["admins"] });
      onClose();
    } catch (reason) {
      feedback.error(
        "No se pudo guardar el administrador",
        apiError(reason, "Revise los datos e inténtelo nuevamente."),
      );
    } finally {
      setPending(false);
    }
  };
  const change = (key: keyof AdminDraft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  return (
    <Modal
      title={user ? "Editar administrador" : "Nuevo administrador"}
      onClose={onClose}
    >
      <form className="form-grid" onSubmit={submit}>
        <Field label="Nombres">
          <input
            className="input"
            required
            value={draft.first_name}
            onChange={(e) => change("first_name", e.target.value)}
          />
        </Field>
        <Field label="Apellido paterno">
          <input
            className="input"
            required
            value={draft.apellido_paterno}
            onChange={(e) => change("apellido_paterno", e.target.value)}
          />
        </Field>
        <Field label="Apellido materno">
          <input
            className="input"
            required
            value={draft.apellido_materno}
            onChange={(e) => change("apellido_materno", e.target.value)}
          />
        </Field>
        <Field label="Número de CI">
          <input
            className="input"
            required
            value={draft.numero_documento}
            onChange={(e) => change("numero_documento", e.target.value)}
          />
        </Field>
        <Field label="Correo Gmail (solo para recuperar contraseña)">
          <div className="gmail-input">
            <input
              className="input"
              required
              aria-label="Usuario de Gmail"
              pattern="[^@\s]+"
              title="Escriba solo la parte anterior a @gmail.com"
              value={draft.gmail_user}
              onChange={(e) =>
                change("gmail_user", e.target.value.replace(/@.*$/, ""))
              }
            />
            <span>@gmail.com</span>
          </div>
        </Field>
        <Field label="Celular">
          <input
            className="input"
            value={draft.phone}
            onChange={(e) => change("phone", e.target.value)}
          />
        </Field>
        <Field label="Cargo">
          <input
            className="input"
            value={draft.cargo}
            onChange={(e) => change("cargo", e.target.value)}
          />
        </Field>
        <Field label="Unidad">
          <SearchableSelect
            value={draft.unidad}
            options={(units.data ?? []).map((unit) => ({
              value: unit.nombre,
              label: unit.nombre,
            }))}
            placeholder="Buscar o escribir una unidad nueva…"
            searchPlaceholder="Buscar unidad…"
            ariaLabel="Unidad"
            allowCustom
            onChange={(value) => change("unidad", value)}
            onDelete={async (option) => {
              const unit = units.data?.find(
                (item) => item.nombre === option.value,
              );
              if (!unit) return;
              const confirmed = await feedback.confirm({
                title: "Eliminar unidad",
                message: `¿Eliminar ${option.label} de las opciones disponibles?`,
                confirmLabel: "Sí, eliminar",
                danger: true,
              });
              if (!confirmed) return;
              await api.delete(`/admin/units/${unit.id}`);
              await queryClient.invalidateQueries({
                queryKey: ["admin-units"],
              });
              feedback.success(
                "Unidad eliminada",
                `${option.label} ya no aparece entre las opciones.`,
              );
            }}
          />
        </Field>
        {!user && (
          <Field label="Rol">
            <select
              className="input"
              value={draft.role}
              onChange={(e) => change("role", e.target.value)}
            >
              <option value="ADMIN_VICEMINISTERIO">Administrador</option>
              <option value="SUPERADMIN">Superadministrador</option>
            </select>
          </Field>
        )}
        <Field label="Observaciones">
          <textarea
            className="input"
            rows={3}
            value={draft.observaciones}
            onChange={(e) => change("observaciones", e.target.value)}
          />
        </Field>
        <div className="modal-actions full">
          <button type="button" className="btn-outline" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn" disabled={pending}>
            Guardar
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function AdministratorsPage() {
  const { user: current } = useAuth();
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [unit, setUnit] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<AdminUser | "new" | null>(null);
  const [credentialsDialog, setCredentialsDialog] =
    useState<CredentialsDialog | null>(null);
  const list = useQuery({
    queryKey: ["admins", query, status, role, unit, page],
    queryFn: () =>
      api
        .get<Paged<AdminUser>>("/admin/users", {
          params: { q: query || undefined, status: status || undefined, role: role || undefined, unit: unit || undefined, page },
        })
        .then((response) => response.data),
  });
  const units = useQuery({
    queryKey: ["admin-units"],
    queryFn: () => api.get<{ items: { id: string; nombre: string }[] }>("/admin/units").then((response) => response.data.items),
  });
  const action = async (
    operation: () => Promise<unknown>,
    successMessage?: string,
  ) => {
    try {
      await operation();
      await queryClient.invalidateQueries({ queryKey: ["admins"] });
      if (successMessage)
        feedback.success("Operación realizada", successMessage);
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo completar la operación", message);
    }
  };
  return (
    <>
      <Header
        eyebrow="Seguridad"
        title="Administradores"
        description="Cuentas con acceso a la gestión institucional."
        action={
          <button className="btn" onClick={() => setEditing("new")}>
            <Plus /> Nuevo administrador
          </button>
        }
      />
      <div className="toolbar">
        <SearchField
          value={query}
          onChange={(value) => {
            setQuery(value);
            setPage(1);
          }}
          placeholder="Buscar administrador…"
        />
        <select className="input" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="ACTIVE">Activos</option><option value="INACTIVE">Inactivos</option><option value="LOCKED">Bloqueados</option></select>
        <select className="input" value={role} onChange={(event) => { setRole(event.target.value); setPage(1); }}><option value="">Todos los roles</option><option value="SUPERADMIN">Superadministradores</option><option value="ADMIN_VICEMINISTERIO">Administradores</option></select>
        <select className="input" value={unit} onChange={(event) => { setUnit(event.target.value); setPage(1); }}><option value="">Todas las unidades</option>{units.data?.map((item) => <option key={item.id} value={item.nombre}>{item.nombre}</option>)}</select>
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.data?.items.length ? (
        <>
          <div className="data-cards">
            {list.data.items.map((item) => (
              <article className="data-card" key={item.id}>
                <div className="data-card-main">
                  <div className="avatar">
                    <ShieldCheck />
                  </div>
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <h2>
                        {item.first_name}{" "}
                        {item.apellido_paterno ?? item.last_name}{" "}
                        {item.apellido_materno ?? ""}
                      </h2>
                      <StatusBadge value={item.status} />
                    </div>
                    <p>
                      {item.email} ·{" "}
                      {item.role === "SUPERADMIN"
                        ? "Superadministrador"
                        : "Administrador"}
                    </p>
                    <small>
                      {item.cargo || "Sin cargo"}
                      {item.unidad && ` · ${item.unidad}`}
                    </small>
                  </div>
                </div>
                <div className="data-card-actions">
                  <button
                    className="btn-outline"
                    onClick={() => setEditing(item)}
                  >
                    <Edit3 size={17} /> Editar
                  </button>
                  <ConfirmButton
                    className="btn-outline"
                    question="¿Restablecer la contraseña de esta cuenta?"
                    onConfirm={() =>
                      action(async () => {
                        const { data } = await api.post(
                          `/admin/users/${item.id}/reset-password`,
                        );
                        setCredentialsDialog({
                          title: "Contraseña restablecida correctamente",
                          credentials: {
                            username: item.username,
                            password: data.temporary_password,
                          },
                        });
                      })
                    }
                  >
                    <KeyRound size={17} /> Restablecer
                  </ConfirmButton>
                  <ConfirmButton
                    className="btn-outline"
                    disabled={item.id === current?.id}
                    question={`¿${item.status === "ACTIVE" ? "Inhabilitar" : "Activar"} la cuenta de ${item.first_name}?`}
                    onConfirm={() =>
                      action(
                        () => api.patch(`/admin/users/${item.id}/status`, {
                          status:
                            item.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
                        }),
                        item.status === "ACTIVE"
                          ? "El administrador fue inhabilitado correctamente."
                          : "El administrador fue activado correctamente.",
                      )
                    }
                  >
                    {item.status === "ACTIVE" ? (
                      <UserX size={17} />
                    ) : (
                      <UserCheck size={17} />
                    )}{" "}
                    {item.status === "ACTIVE" ? "Inhabilitar" : "Activar"}
                  </ConfirmButton>
                  <ConfirmButton
                    disabled={item.id === current?.id}
                    question={`¿Eliminar la cuenta de ${item.first_name}?`}
                    onConfirm={() =>
                      action(
                        () => api.delete(`/admin/users/${item.id}`),
                        "El administrador fue eliminado correctamente.",
                      )
                    }
                  >
                    <Trash2 size={17} />
                  </ConfirmButton>
                </div>
              </article>
            ))}
          </div>
          <PaginationBar pagination={list.data.pagination} onPage={setPage} />
        </>
      ) : (
        <Empty title="No hay administradores" />
      )}
      {editing && (
        <AdminForm
          user={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onCreated={(credentials) =>
            setCredentialsDialog({
              title: "Administrador creado correctamente",
              credentials,
            })
          }
        />
      )}
      {credentialsDialog && (
        <CredentialsModal
          title={credentialsDialog.title}
          credentials={credentialsDialog.credentials}
          onClose={() => setCredentialsDialog(null)}
        />
      )}
    </>
  );
}

type ExhibitorDraft = {
  nombre_comercial: string;
  tipo_documento: "CI" | "NIT" | "OTRO";
  numero_documento: string;
  nombre_responsable: string;
  apellido_paterno_responsable: string;
  apellido_materno_responsable: string;
  gmail_user: string;
  telefono_whatsapp: string;
  departamento: string;
  municipio: string;
  direccion: string;
  descripcion: string;
  descripcion_productos: string;
  nombre_tipo_expositor: string;
  logo: string;
  type_ids: string[];
};
const blankExhibitor: ExhibitorDraft = {
  nombre_comercial: "",
  tipo_documento: "CI",
  numero_documento: "",
  nombre_responsable: "",
  apellido_paterno_responsable: "",
  apellido_materno_responsable: "",
  gmail_user: "",
  telefono_whatsapp: "591",
  departamento: "La Paz",
  municipio: "",
  direccion: "",
  descripcion: "",
  descripcion_productos: "",
  nombre_tipo_expositor: "",
  logo: "",
  type_ids: [],
};

function ExhibitorForm({
  exhibitor,
  types,
  onClose,
  onCreated,
}: {
  exhibitor: Exhibitor | null;
  types: { id: string; nombre: string }[];
  onClose: () => void;
  onCreated: (credentials: CreatedCredentials) => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const source: ExhibitorDraft = exhibitor
    ? {
        nombre_comercial: exhibitor.nombre_comercial,
        tipo_documento: exhibitor.tipo_documento ?? "CI",
        numero_documento: exhibitor.numero_documento ?? "",
        nombre_responsable: exhibitor.nombre_responsable ?? "",
        apellido_paterno_responsable:
          exhibitor.apellido_paterno_responsable ??
          exhibitor.apellido_responsable ??
          "",
        apellido_materno_responsable:
          exhibitor.apellido_materno_responsable ?? "",
        gmail_user: gmailLocalPart(exhibitor.correo ?? ""),
        telefono_whatsapp: exhibitor.telefono_whatsapp ?? "591",
        departamento: exhibitor.departamento ?? "La Paz",
        municipio: exhibitor.municipio ?? "",
        direccion: exhibitor.direccion ?? "",
        descripcion: exhibitor.descripcion ?? "",
        descripcion_productos: exhibitor.descripcion_productos ?? "",
        nombre_tipo_expositor: exhibitor.nombre_tipo_expositor ?? "",
        logo: exhibitor.logo ?? "",
        type_ids: exhibitor.type_ids ?? [],
      }
    : blankExhibitor;
  const [draft, setDraft] = useState(source);
  const [useResponsibleName, setUseResponsibleName] = useState(false);
  const [logo, setLogo] = useState<File | null>(null);
  const [logoMode, setLogoMode] = useState<"UPLOAD" | "URL">(
    /^https?:\/\//i.test(source.logo) ? "URL" : "UPLOAD",
  );
  const [pending, setPending] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const change = (key: keyof ExhibitorDraft, value: string | string[]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const responsibleFullName = responsibleDisplayName(
    draft.nombre_responsable,
    draft.apellido_paterno_responsable,
    draft.apellido_materno_responsable,
  );
  const selectedType = types.find((item) => item.id === draft.type_ids[0]);
  const typeNameLabels: Record<string, string> = {
    "Asociación": "Nombre de la asociación",
    Cooperativa: "Nombre de la cooperativa",
    Emprendimiento: "Nombre del emprendimiento",
    Microempresa: "Nombre de la microempresa",
  };
  const typeNameLabel = selectedType ? typeNameLabels[selectedType.nombre] : undefined;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    try {
      const logoUrl =
        logoMode === "URL"
          ? draft.logo.trim() || null
          : logo
            ? await uploadFile(logo, "logos", setUploadProgress)
            : /^https?:\/\//i.test(draft.logo)
              ? null
              : draft.logo || null;
      const { gmail_user, type_ids, ...fields } = draft;
      const basePayload = {
        ...fields,
        nombre_comercial: useResponsibleName
          ? responsibleFullName
          : draft.nombre_comercial.trim(),
        correo: gmailAddress(gmail_user),
        logo: logoUrl,
      };
      if (exhibitor) {
        await api.patch(`/exhibitors/${exhibitor.id}`, { ...basePayload, type_ids });
        feedback.success(
          "Expositor actualizado",
          "Los cambios se guardaron correctamente.",
        );
      } else {
        const payload = { ...basePayload, type_ids };
        const { data } = await api.post<{
          username: string;
          temporary_password: string;
        }>("/exhibitors", payload);
        onCreated({
          username: data.username,
          password: data.temporary_password,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ["exhibitors"] });
      onClose();
    } catch (reason) {
      feedback.error(
        "No se pudo guardar el expositor",
        apiError(reason, "Revise los datos e inténtelo nuevamente."),
      );
    } finally {
      setPending(false);
      setUploadProgress(0);
    }
  };
  return (
    <Modal
      title={exhibitor ? "Editar expositor" : "Nuevo expositor"}
      onClose={onClose}
      wide
    >
      <form className="form-grid" onSubmit={submit}>
        <Field label="Nombre comercial">
          <input
            className="input"
            required
            disabled={useResponsibleName}
            placeholder={
              useResponsibleName
                ? "Se usará el nombre completo del responsable"
                : undefined
            }
            value={
              useResponsibleName ? responsibleFullName : draft.nombre_comercial
            }
            onChange={(e) => change("nombre_comercial", e.target.value)}
          />
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={useResponsibleName}
              onChange={(event) => setUseResponsibleName(event.target.checked)}
            />
            No tiene nombre comercial; usar el nombre del responsable
          </label>
        </Field>
        <Field label="Tipo de documento">
          <select
            className="input"
            value={draft.tipo_documento}
            onChange={(e) => change("tipo_documento", e.target.value)}
          >
            <option value="CI">CI</option>
            <option value="NIT">NIT</option>
            <option value="OTRO">Otro</option>
          </select>
        </Field>
        <Field
          label={
            draft.tipo_documento === "CI"
              ? "CI"
              : draft.tipo_documento === "NIT"
                ? "NIT"
                : "Número de documento"
          }
        >
          <input
            className="input"
            required
            value={draft.numero_documento}
            onChange={(e) => change("numero_documento", e.target.value)}
          />
        </Field>
        <Field label="Nombres del responsable">
          <input
            className="input"
            required
            value={draft.nombre_responsable}
            onChange={(e) => change("nombre_responsable", e.target.value)}
          />
        </Field>
        <Field label="Apellido paterno del responsable">
          <input
            className="input"
            required
            value={draft.apellido_paterno_responsable}
            onChange={(e) =>
              change("apellido_paterno_responsable", e.target.value)
            }
          />
        </Field>
        <Field label="Apellido materno del responsable">
          <input
            className="input"
            required
            value={draft.apellido_materno_responsable}
            onChange={(e) =>
              change("apellido_materno_responsable", e.target.value)
            }
          />
        </Field>
        <Field label="Correo Gmail (solo para recuperar contraseña)">
          <div className="gmail-input">
            <input
              className="input"
              required
              aria-label="Usuario de Gmail del expositor"
              pattern="[^@\s]+"
              title="Escriba solo la parte anterior a @gmail.com"
              value={draft.gmail_user}
              onChange={(e) =>
                change("gmail_user", e.target.value.replace(/@.*$/, ""))
              }
            />
            <span>@gmail.com</span>
          </div>
        </Field>
        <Field label="WhatsApp">
          <div className="phone-input">
            <span>+591</span>
            <input
              className="input"
              required
              inputMode="numeric"
              maxLength={8}
              pattern="[67][0-9]{7}"
              title="Ingrese los 8 dígitos del celular boliviano"
              value={draft.telefono_whatsapp.replace(/^591/, "")}
              onChange={(event) =>
                change(
                  "telefono_whatsapp",
                  `591${event.target.value.replace(/\D/g, "").slice(0, 8)}`,
                )
              }
            />
          </div>
        </Field>
        <LocationFields
          department={draft.departamento}
          municipality={draft.municipio}
          onDepartment={(value) => change("departamento", value)}
          onMunicipality={(value) => change("municipio", value)}
        />
        <Field label="Dirección">
          <input
            className="input"
            value={draft.direccion}
            onChange={(e) => change("direccion", e.target.value)}
          />
        </Field>
        <Field label="Tipo de expositor">
          <div className="check-list exhibitor-type-list">
            {types.map((type) => (
              <label key={type.id}>
                <input
                  type="radio"
                  name="tipo_expositor"
                  checked={draft.type_ids[0] === type.id}
                  onChange={() => {
                    change("type_ids", [type.id]);
                    change("nombre_tipo_expositor", "");
                  }}
                />
                {type.nombre}
              </label>
            ))}
          </div>
        </Field>
        {typeNameLabel && (
          <Field label={typeNameLabel}>
            <input
              className="input"
              required
              value={draft.nombre_tipo_expositor}
              onChange={(event) => change("nombre_tipo_expositor", event.target.value)}
            />
          </Field>
        )}
        <Field label="Origen del logo">
          <select
            className="input"
            value={logoMode}
            onChange={(e) => {
              setLogoMode(e.target.value as "UPLOAD" | "URL");
              setLogo(null);
            }}
          >
            <option value="UPLOAD">Cargar desde el dispositivo</option>
            <option value="URL">Usar URL de imagen</option>
          </select>
        </Field>
        <Field
          label={logoMode === "URL" ? "URL del logo" : "Archivo del logo"}
        >
          {logoMode === "URL" ? (
            <input
              className="input"
              type="url"
              placeholder="https://ejemplo.com/logo.jpg"
              value={draft.logo}
              onChange={(e) => change("logo", e.target.value)}
            />
          ) : (
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setLogo(e.target.files?.[0] ?? null)}
            />
          )}
        </Field>
        <UploadProgress value={uploadProgress} />
        <Field label="Descripción">
          <textarea
            className="input"
            rows={4}
            value={draft.descripcion}
            onChange={(e) => change("descripcion", e.target.value)}
          />
        </Field>
        <Field label="Descripción de productos">
          <textarea
            className="input"
            rows={4}
            value={draft.descripcion_productos}
            onChange={(e) => change("descripcion_productos", e.target.value)}
          />
        </Field>
        <div className="modal-actions full">
          <button type="button" className="btn-outline" onClick={onClose}>
            Cancelar
          </button>
          <button
            className="btn"
            disabled={pending || draft.type_ids.length !== 1 || Boolean(typeNameLabel && !draft.nombre_tipo_expositor.trim())}
          >
            Guardar expositor
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function ExhibitorsPage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [department, setDepartment] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Exhibitor | "new" | null>(null);
  const [credentialsDialog, setCredentialsDialog] =
    useState<CredentialsDialog | null>(null);
  const list = useQuery({
    queryKey: ["exhibitors", query, status, department, municipality, documentType, page],
    queryFn: () =>
      api
        .get<Paged<Exhibitor>>("/exhibitors", {
          params: {
            q: query || undefined,
            estado: status || undefined,
            departamento: department || undefined,
            municipio: municipality || undefined,
            tipo_documento: documentType || undefined,
            page,
          },
        })
        .then((r) => r.data),
  });
  const types = useQuery({
    queryKey: ["exhibitor-types"],
    queryFn: () =>
      api
        .get<{ items: { id: string; nombre: string }[] }>("/exhibitor-types")
        .then((r) => r.data.items),
  });
  const action = async (
    operation: () => Promise<unknown>,
    successMessage?: string,
  ) => {
    try {
      await operation();
      await queryClient.invalidateQueries({ queryKey: ["exhibitors"] });
      if (successMessage)
        feedback.success("Operación realizada", successMessage);
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo completar la operación", message);
    }
  };
  return (
    <>
      <Header
        eyebrow="Empresas"
        title="Expositores"
        description="Cuentas y emprendimientos registrados en la plataforma."
        action={
          <button className="btn" onClick={() => setEditing("new")}>
            <Plus /> Nuevo expositor
          </button>
        }
      />
      <div className="toolbar">
        <SearchField
          value={query}
          onChange={(v) => {
            setQuery(v);
            setPage(1);
          }}
          placeholder="Buscar por nombre comercial o responsable…"
        />
        <select
          className="input"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Todos los estados</option>
          <option value="ACTIVE">Activos</option>
          <option value="INACTIVE">Inactivos</option>
          <option value="LOCKED">Bloqueados</option>
        </select>
        <SearchableSelect
          value={department}
          options={[
            { value: "", label: "Todos los departamentos" },
            ...BOLIVIA_DEPARTMENTS.map((item) => ({ value: item, label: item })),
          ]}
          placeholder="Todos los departamentos"
          searchPlaceholder="Buscar departamento…"
          ariaLabel="Filtrar por departamento"
          onChange={(value) => {
            setDepartment(value);
            setMunicipality("");
            setPage(1);
          }}
        />
        <SearchableSelect
          disabled={!department}
          value={municipality}
          options={[{ value: "", label: "Todos los municipios" }, ...municipalitiesFor(department).map((item) => ({ value: item, label: item }))]}
          placeholder="Todos los municipios"
          searchPlaceholder="Buscar municipio…"
          ariaLabel="Filtrar por municipio"
          onChange={(value) => { setMunicipality(value); setPage(1); }}
        />
        <select className="input" value={documentType} onChange={(event) => { setDocumentType(event.target.value); setPage(1); }}><option value="">Todos los documentos</option><option value="CI">CI</option><option value="NIT">NIT</option><option value="OTRO">Otro</option></select>
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.data?.items.length ? (
        <>
          <div className="data-cards">
            {list.data.items.map((item) => (
              <article className="data-card" key={item.id}>
                <div className="data-card-main">
                  {item.logo ? (
                    <img
                      className="data-thumb"
                      src={assetUrl(item.logo)}
                      alt=""
                    />
                  ) : (
                    <div className="avatar">
                      <Store />
                    </div>
                  )}
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <h2>{item.nombre_comercial}</h2>
                      <StatusBadge value={item.estado ?? "INACTIVE"} />
                    </div>
                    <p>
                      {item.nombre_responsable}{" "}
                      {item.apellido_paterno_responsable ??
                        item.apellido_responsable}{" "}
                      {item.apellido_materno_responsable ?? ""} ·{" "}
                      {item.correo}
                    </p>
                    <small>
                      {item.municipio}, {item.departamento} · WhatsApp{" "}
                      {item.telefono_whatsapp}
                    </small>
                  </div>
                </div>
                <div className="data-card-actions">
                  <button
                    className="btn-outline"
                    onClick={() => setEditing(item)}
                  >
                    <Edit3 size={17} /> Editar
                  </button>
                  <ConfirmButton
                    className="btn-outline"
                    question={`¿Restablecer la contraseña de ${item.nombre_comercial}?`}
                    onConfirm={() =>
                      action(async () => {
                        const { data } = await api.post<{
                          username: string;
                          temporary_password: string;
                        }>(`/admin/users/${item.user_id}/reset-password`);
                        setCredentialsDialog({
                          title: "Contraseña restablecida correctamente",
                          credentials: {
                            username: data.username,
                            password: data.temporary_password,
                          },
                        });
                      })
                    }
                  >
                    <KeyRound size={17} /> Restablecer contraseña
                  </ConfirmButton>
                  <ConfirmButton
                    className="btn-outline"
                    question={`¿${item.estado === "ACTIVE" ? "Inhabilitar" : "Activar"} al expositor ${item.nombre_comercial}?`}
                    onConfirm={() =>
                      action(
                        () => api.patch(`/exhibitors/${item.id}/status`, {
                          status:
                            item.estado === "ACTIVE" ? "INACTIVE" : "ACTIVE",
                        }),
                        item.estado === "ACTIVE"
                          ? "El expositor fue inhabilitado correctamente."
                          : "El expositor fue activado correctamente.",
                      )
                    }
                  >
                    {item.estado === "ACTIVE" ? (
                      <UserX size={17} />
                    ) : (
                      <UserCheck size={17} />
                    )}{" "}
                    {item.estado === "ACTIVE" ? "Inhabilitar" : "Activar"}
                  </ConfirmButton>
                  <ConfirmButton
                    question={`¿Eliminar ${item.nombre_comercial} y desactivar su cuenta?`}
                    onConfirm={() =>
                      action(
                        () => api.delete(`/exhibitors/${item.id}`),
                        "El expositor y su cuenta fueron eliminados correctamente.",
                      )
                    }
                  >
                    <Trash2 size={17} />
                  </ConfirmButton>
                </div>
              </article>
            ))}
          </div>
          <PaginationBar pagination={list.data.pagination} onPage={setPage} />
        </>
      ) : (
        <Empty title="No se encontraron expositores" />
      )}
      {editing && (
        <ExhibitorForm
          exhibitor={editing === "new" ? null : editing}
          types={types.data ?? []}
          onClose={() => setEditing(null)}
          onCreated={(credentials) =>
            setCredentialsDialog({
              title: "Expositor creado correctamente",
              credentials,
            })
          }
        />
      )}
      {credentialsDialog && (
        <CredentialsModal
          title={credentialsDialog.title}
          credentials={credentialsDialog.credentials}
          onClose={() => setCredentialsDialog(null)}
        />
      )}
    </>
  );
}

function CategoryForm({
  category,
  onClose,
}: {
  category: Category | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [nombre, setNombre] = useState(category?.nombre ?? "");
  const [descripcion, setDescripcion] = useState(category?.descripcion ?? "");
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (category)
        await api.patch(`/categories/${category.id}`, { nombre, descripcion });
      else await api.post("/categories", { nombre, descripcion });
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
      onClose();
      feedback.success(
        category ? "Categoría actualizada" : "Categoría creada",
        category
          ? "Los cambios se guardaron correctamente."
          : "La nueva categoría está disponible en el catálogo.",
      );
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo guardar la categoría", message);
    }
  };
  return (
    <Modal
      title={category ? "Editar categoría" : "Nueva categoría"}
      onClose={onClose}
    >
      <form className="form-stack" onSubmit={submit}>
        <Field label="Nombre">
          <input
            className="input"
            required
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </Field>
        <Field label="Descripción">
          <textarea
            className="input"
            rows={4}
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
          />
        </Field>
        <div className="modal-actions">
          <button type="button" className="btn-outline" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn">Guardar</button>
        </div>
      </form>
    </Modal>
  );
}

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [editing, setEditing] = useState<Category | "new" | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const list = useQuery({
    queryKey: ["categories", "admin", query, status, page],
    queryFn: () =>
      api
        .get<Paged<Category>>("/admin/categories", { params: { q: query || undefined, status: status || undefined, page } })
        .then((r) => r.data),
  });
  const action = async (
    operation: () => Promise<unknown>,
    successMessage: string,
  ) => {
    try {
      await operation();
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
      feedback.success("Operación realizada", successMessage);
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo completar la operación", message);
    }
  };
  return (
    <>
      <Header
        eyebrow="Clasificación"
        title="Categorías"
        description="Organice los productos publicados en el catálogo."
        action={
          <button className="btn" onClick={() => setEditing("new")}>
            <Plus /> Nueva categoría
          </button>
        }
      />
      <div className="toolbar">
        <SearchField value={query} onChange={(value) => { setQuery(value); setPage(1); }} placeholder="Buscar categoría…" />
        <select className="input" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="active">Activas</option><option value="inactive">Inactivas</option></select>
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.data?.items.length ? (
        <>
          <div className="data-cards">
            {list.data.items.map((item) => (
              <article className="data-card" key={item.id}>
                <div className="data-card-main">
                  <div className="avatar">
                    <Store />
                  </div>
                  <div>
                    <div className="flex gap-2">
                      <h2>{item.nombre}</h2>
                      <StatusBadge value={item.estado} />
                    </div>
                    <p>{item.descripcion || "Sin descripción"}</p>
                  </div>
                </div>
                <div className="data-card-actions">
                  <button
                    className="btn-outline"
                    onClick={() => setEditing(item)}
                  >
                    <Edit3 size={17} /> Editar
                  </button>
                  <ConfirmButton
                    className="btn-outline"
                    question={`¿${item.estado ? "Inhabilitar" : "Activar"} la categoría ${item.nombre}?`}
                    onConfirm={() =>
                      action(
                        () => api.patch(`/categories/${item.id}/status`, {
                          active: !item.estado,
                        }),
                        item.estado
                          ? "La categoría fue inhabilitada correctamente."
                          : "La categoría fue activada correctamente.",
                      )
                    }
                  >
                    {item.estado ? "Inhabilitar" : "Activar"}
                  </ConfirmButton>
                  <ConfirmButton
                    question={`¿Eliminar la categoría ${item.nombre}? Solo será posible si no tiene productos.`}
                    onConfirm={() =>
                      action(
                        () => api.delete(`/categories/${item.id}`),
                        "La categoría fue eliminada correctamente.",
                      )
                    }
                  >
                    <Trash2 size={17} />
                  </ConfirmButton>
                </div>
              </article>
            ))}
          </div>
          <PaginationBar pagination={list.data.pagination} onPage={setPage} />
        </>
      ) : (
        <Empty title="No hay categorías" />
      )}
      {editing && (
        <CategoryForm
          category={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}

type FairDraft = {
  nombre: string;
  descripcion: string;
  lugar: string;
  direccion: string;
  departamento: string;
  municipio: string;
  fecha_inicio: string;
  fecha_fin: string;
  observaciones: string;
  imagen_portada: string;
};
const blankFair: FairDraft = {
  nombre: "",
  descripcion: "",
  lugar: "",
  direccion: "",
  departamento: "La Paz",
  municipio: "",
  fecha_inicio: "",
  fecha_fin: "",
  observaciones: "",
  imagen_portada: "",
};

function ImagePreviewModal({ src, title, onClose }: { src: string; title: string; onClose: () => void }) {
  return <Modal title={title} onClose={onClose} wide>
    <div className="image-preview-dialog">
      <img src={src} alt={title} />
      <div className="modal-actions"><button type="button" className="btn" onClick={onClose} autoFocus>OK</button></div>
    </div>
  </Modal>;
}

function FairForm({
  fair,
  onClose,
}: {
  fair: Fair | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [draft, setDraft] = useState<FairDraft>(
    fair
      ? {
          nombre: fair.nombre,
          lugar: fair.lugar,
          imagen_portada: fair.imagen_portada ?? "",
          observaciones: fair.observaciones ?? "",
          descripcion: fair.descripcion ?? "",
          direccion: fair.direccion ?? "",
          departamento: fair.departamento,
          municipio: fair.municipio,
          fecha_inicio: fair.fecha_inicio,
          fecha_fin: fair.fecha_fin,
        }
      : blankFair,
  );
  const [cover, setCover] = useState<File | null>(null);
  const [coverMode, setCoverMode] = useState<"UPLOAD" | "URL">(
    /^https?:\/\//i.test(fair?.imagen_portada ?? "") ? "URL" : "UPLOAD",
  );
  const [coverPreview, setCoverPreview] = useState(assetUrl(fair?.imagen_portada));
  const [showCoverPreview, setShowCoverPreview] = useState(false);
  useEffect(() => () => {
    if (coverPreview.startsWith("blob:")) URL.revokeObjectURL(coverPreview);
  }, [coverPreview]);
  const [pending, setPending] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const change = (key: keyof FairDraft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    if (draft.fecha_fin < draft.fecha_inicio) {
      setPending(false);
      const message = "La fecha final no puede ser anterior a la inicial.";
      feedback.error("Fechas incorrectas", message);
      return;
    }
    try {
      const imagen_portada =
        coverMode === "URL"
          ? draft.imagen_portada.trim()
          : cover
            ? await uploadFile(cover, "ferias", setUploadProgress)
            : /^https?:\/\//i.test(draft.imagen_portada)
              ? ""
              : draft.imagen_portada;
      const payload = { ...draft, imagen_portada };
      if (fair) await api.patch(`/fairs/${fair.id}`, payload);
      else await api.post("/fairs", payload);
      await queryClient.invalidateQueries({ queryKey: ["fairs"] });
      onClose();
      feedback.success(
        fair ? "Feria actualizada" : "Feria creada",
        fair
          ? "Los cambios se guardaron correctamente."
          : "La feria fue registrada correctamente.",
      );
    } catch (reason) {
      const message = apiError(reason, "No se pudo guardar la feria.");
      feedback.error("No se pudo guardar la feria", message);
    } finally {
      setPending(false);
      setUploadProgress(0);
    }
  };
  return <>
    <Modal title={fair ? "Editar feria" : "Nueva feria"} onClose={onClose} wide>
      <form className="form-grid" onSubmit={submit}>
        <Field label="Nombre">
          <input
            className="input"
            required
            value={draft.nombre}
            onChange={(e) => change("nombre", e.target.value)}
          />
        </Field>
        <Field label="Lugar">
          <input
            className="input"
            required
            value={draft.lugar}
            onChange={(e) => change("lugar", e.target.value)}
          />
        </Field>
        <Field label="Dirección">
          <input
            className="input"
            value={draft.direccion}
            onChange={(e) => change("direccion", e.target.value)}
          />
        </Field>
        <LocationFields
          department={draft.departamento}
          municipality={draft.municipio}
          onDepartment={(value) => change("departamento", value)}
          onMunicipality={(value) => change("municipio", value)}
        />
        <Field label="Fecha de inicio">
          <input
            className="input"
            type="date"
            required
            value={draft.fecha_inicio}
            onChange={(e) => change("fecha_inicio", e.target.value)}
          />
        </Field>
        <Field label="Fecha final">
          <input
            className="input"
            type="date"
            required
            value={draft.fecha_fin}
            onChange={(e) => change("fecha_fin", e.target.value)}
          />
        </Field>
        <Field label="Origen de la portada">
          <select
            className="input"
            value={coverMode}
            onChange={(event) => {
              const mode = event.target.value as "UPLOAD" | "URL";
              setCoverMode(mode);
              setCover(null);
              if (mode === "URL") setCoverPreview(assetUrl(draft.imagen_portada));
            }}
          >
            <option value="UPLOAD">Cargar desde el dispositivo</option>
            <option value="URL">Usar URL de imagen</option>
          </select>
        </Field>
        <Field
          label={coverMode === "URL" ? "URL de la portada" : "Archivo de portada"}
        >
          {coverMode === "URL" ? (
            <input
              className="input"
              type="url"
              required
              placeholder="https://ejemplo.com/portada.jpg"
              value={draft.imagen_portada}
              onChange={(event) => {
                change("imagen_portada", event.target.value);
                setCover(null);
                setCoverPreview(assetUrl(event.target.value));
              }}
              onBlur={() => {
                if (draft.imagen_portada.trim())
                  feedback.success("Imagen cargada satisfactoriamente", "El enlace de la portada está listo para guardar.");
              }}
            />
          ) : (
            <input
              type="file"
              accept="image/*"
              required={!fair && !draft.imagen_portada}
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                if (!file) return;
                if (!file.type.startsWith("image/")) {
                  event.target.value = "";
                  feedback.error("Archivo no válido", "Seleccione únicamente una imagen.");
                  return;
                }
                setCover(file);
                change("imagen_portada", "");
                setCoverPreview(URL.createObjectURL(file));
                feedback.success("Imagen cargada satisfactoriamente", "La portada está lista y puede verla antes de guardar la feria.");
              }}
            />
          )}
        </Field>
        {coverPreview && (
          <div className="full fair-cover-preview">
            <span>Vista previa de la portada</span>
            <button type="button" onClick={() => setShowCoverPreview(true)} title="Ampliar imagen">
              <img src={coverPreview} alt="Vista previa de la portada de la feria" />
              <small>Haga clic para ampliar</small>
            </button>
          </div>
        )}
        <UploadProgress value={uploadProgress} />
        <Field label="Descripción">
          <textarea
            className="input"
            rows={4}
            value={draft.descripcion}
            onChange={(e) => change("descripcion", e.target.value)}
          />
        </Field>
        <Field label="Observaciones">
          <textarea
            className="input"
            rows={4}
            value={draft.observaciones}
            onChange={(e) => change("observaciones", e.target.value)}
          />
        </Field>
        <div className="full alert-warning">
          <strong>Publicación automática</strong>
          <p>
            El estado se determina según las fechas. No es necesario activar la
            feria manualmente.
          </p>
        </div>
        <div className="modal-actions full">
          <button className="btn-outline" type="button" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn" disabled={pending}>
            Guardar feria
          </button>
        </div>
      </form>
    </Modal>
    {showCoverPreview && coverPreview && <ImagePreviewModal src={coverPreview} title="Vista previa de la portada" onClose={() => setShowCoverPreview(false)} />}
  </>;
}

function AssignmentEditor({
  item,
  terminal,
  onSave,
}: {
  item: Assignment;
  terminal: boolean;
  onSave: (patch: {
    estado: AssignmentStatus;
    numero_stand: string;
    sector: string;
    observaciones: string;
  }) => Promise<void>;
}) {
  const [draft, setDraft] = useState({
    estado: item.estado,
    numero_stand: item.numero_stand ?? "",
    sector: item.sector ?? "",
    observaciones: item.observaciones ?? "",
  });
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await onSave(draft);
    } finally {
      setSaving(false);
    }
  };
  return (
    <article className="assignment-editor">
      <strong>{item.nombre_comercial}</strong>
      <select
        className="input compact"
        disabled={terminal}
        value={draft.estado}
        aria-label={`Estado de ${item.nombre_comercial}`}
        onChange={(event) =>
          setDraft({ ...draft, estado: event.target.value as AssignmentStatus })
        }
      >
        <option value="AUTHORIZED">Autorizado</option>
        <option value="PENDING">Pendiente</option>
        <option value="REJECTED">Rechazado</option>
        <option value="REVOKED">Revocado</option>
      </select>
      <input
        className="input compact"
        disabled={terminal}
        aria-label={`Stand de ${item.nombre_comercial}`}
        placeholder="Stand"
        value={draft.numero_stand}
        onChange={(event) =>
          setDraft({ ...draft, numero_stand: event.target.value })
        }
      />
      <input
        className="input compact"
        disabled={terminal}
        aria-label={`Sector de ${item.nombre_comercial}`}
        placeholder="Sector"
        value={draft.sector}
        onChange={(event) => setDraft({ ...draft, sector: event.target.value })}
      />
      <input
        className="input compact"
        disabled={terminal}
        aria-label={`Observaciones de ${item.nombre_comercial}`}
        placeholder="Observaciones"
        value={draft.observaciones}
        onChange={(event) =>
          setDraft({ ...draft, observaciones: event.target.value })
        }
      />
      <button
        type="button"
        className="btn-outline"
        disabled={terminal || saving}
        onClick={save}
      >
        <Save size={17} /> {saving ? "Guardando…" : "Guardar"}
      </button>
    </article>
  );
}

function FairWorkspace({
  fair,
  exhibitors,
  onClose,
}: {
  fair: Fair;
  exhibitors: Exhibitor[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const terminal = fair.estado === "FINISHED" || fair.estado === "DISABLED";
  const [form, setForm] = useState({
    exhibitor_id: "",
    estado: "AUTHORIZED" as AssignmentStatus,
    numero_stand: "",
    sector: "",
    observaciones: "",
  });
  const assignments = useQuery({
    queryKey: ["fair-assignments", fair.id],
    queryFn: () =>
      api
        .get<Paged<Assignment>>(`/fairs/${fair.id}/exhibitors`, {
          params: { per_page: 100 },
        })
        .then((r) => r.data.items),
  });
  const mutate = async (
    operation: () => Promise<unknown>,
    key: string[],
    successMessage: string,
  ) => {
    try {
      await operation();
      await queryClient.invalidateQueries({ queryKey: key });
      feedback.success("Operación realizada", successMessage);
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo completar la operación", message);
    }
  };
  const assign = (e: React.FormEvent) => {
    e.preventDefault();
    void mutate(
      () => api.post(`/fairs/${fair.id}/exhibitors`, form),
      ["fair-assignments", fair.id],
      "El expositor fue asignado correctamente a la feria.",
    );
  };
  return (
    <Modal title={`Gestión de ${fair.nombre}`} onClose={onClose} wide>
      <h3>Participantes</h3>
      {terminal && (
        <div className="alert-warning">
          Esta feria es terminal y ya no admite modificaciones.
        </div>
      )}
      <form className="inline-form" onSubmit={assign}>
            <select
              className="input"
              required
              disabled={terminal}
              value={form.exhibitor_id}
              onChange={(e) =>
                setForm({ ...form, exhibitor_id: e.target.value })
              }
            >
              <option value="">Seleccione expositor</option>
              {exhibitors.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre_comercial}
                </option>
              ))}
            </select>
            <input
              className="input"
              disabled={terminal}
              placeholder="Stand"
              value={form.numero_stand}
              onChange={(e) =>
                setForm({ ...form, numero_stand: e.target.value })
              }
            />
            <input
              className="input"
              disabled={terminal}
              placeholder="Sector"
              value={form.sector}
              onChange={(e) => setForm({ ...form, sector: e.target.value })}
            />
            <button className="btn" disabled={terminal}>
              Asignar
            </button>
          </form>
          <p className="form-hint">
            Los productos vigentes del expositor autorizado se publican
            automáticamente; no se seleccionan por feria.
          </p>
          {assignments.isLoading ? (
            <Loading />
          ) : assignments.data?.length ? (
            <div className="compact-list">
              {assignments.data.map((item) => (
                <AssignmentEditor
                  key={item.id}
                  item={item}
                  terminal={terminal}
                  onSave={(patch) =>
                    mutate(
                      () => api.patch(`/fair-exhibitors/${item.id}`, patch),
                      ["fair-assignments", fair.id],
                      "La asignación del expositor fue actualizada.",
                    )
                  }
                />
              ))}
            </div>
          ) : (
            <Empty title="No hay expositores asignados" />
          )}
    </Modal>
  );
}

export function FairsPage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [department, setDepartment] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Fair | "new" | null>(null);
  const [workspace, setWorkspace] = useState<Fair | null>(null);
  const list = useQuery({
    queryKey: ["fairs", query, status, department, municipality, dateFrom, dateTo, page],
    queryFn: () =>
      api
        .get<Paged<Fair>>("/fairs", {
          params: { q: query || undefined, estado: status || undefined, departamento: department || undefined, municipio: municipality || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, page },
        })
        .then((r) => r.data),
  });
  const exhibitors = useQuery({
    queryKey: ["exhibitors", "fair-options"],
    queryFn: () =>
      api
        .get<Paged<Exhibitor>>("/exhibitors", {
          params: { per_page: 100, estado: "ACTIVE" },
        })
        .then((r) => r.data.items),
  });
  const finish = async (fair: Fair, state: FairStatus) => {
    try {
      await api.patch(`/fairs/${fair.id}/status`, { status: state });
      await queryClient.invalidateQueries({ queryKey: ["fairs"] });
      feedback.success(
        state === "FINISHED" ? "Feria finalizada" : "Feria cancelada",
        state === "FINISHED"
          ? "La feria fue finalizada correctamente."
          : "La feria fue cancelada correctamente.",
      );
    } catch (reason) {
      const message = apiError(reason);
      feedback.error("No se pudo actualizar la feria", message);
    }
  };
  return (
    <>
      <Header
        eyebrow="Programación"
        title="Ferias"
        description="Las fechas controlan automáticamente la publicación del catálogo."
        action={
          <button className="btn" onClick={() => setEditing("new")}>
            <Plus /> Nueva feria
          </button>
        }
      />
      <div className="toolbar">
        <SearchField
          value={query}
          onChange={(v) => {
            setQuery(v);
            setPage(1);
          }}
          placeholder="Buscar feria…"
        />
        <select
          className="input"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Todos los estados</option>
          <option value="DRAFT">En preparación</option>
          <option value="PUBLISHED">Publicada</option>
          <option value="FINISHED">Finalizada</option>
          <option value="DISABLED">Cancelada</option>
        </select>
        <SearchableSelect value={department} options={[{ value: "", label: "Todos los departamentos" }, ...BOLIVIA_DEPARTMENTS.map((item) => ({ value: item, label: item }))]} placeholder="Todos los departamentos" ariaLabel="Departamento de feria" onChange={(value) => { setDepartment(value); setMunicipality(""); setPage(1); }} />
        <SearchableSelect disabled={!department} value={municipality} options={[{ value: "", label: "Todos los municipios" }, ...municipalitiesFor(department).map((item) => ({ value: item, label: item }))]} placeholder="Todos los municipios" ariaLabel="Municipio de feria" onChange={(value) => { setMunicipality(value); setPage(1); }} />
        <input className="input" type="date" aria-label="Ferias desde" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} />
        <input className="input" type="date" aria-label="Ferias hasta" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} />
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.data?.items.length ? (
        <>
          <div className="fair-admin-grid">
            {list.data.items.map((fair) => {
              const terminal =
                fair.estado === "FINISHED" || fair.estado === "DISABLED";
              return (
                <article className="fair-admin-card" key={fair.id}>
                  {fair.imagen_portada ? (
                    <img src={assetUrl(fair.imagen_portada)} alt="" />
                  ) : (
                    <div className="image-placeholder">
                      <ImagePlus />
                    </div>
                  )}
                  <div className="card-body">
                    <div className="flex justify-between gap-2">
                      <h2>{fair.nombre}</h2>
                      <StatusBadge value={fair.estado} />
                    </div>
                    <p>
                      {fair.lugar}, {fair.municipio}
                    </p>
                    <small>
                      {fair.fecha_inicio} – {fair.fecha_fin}
                    </small>
                    <div className="data-card-actions">
                      <button
                        className="btn-outline"
                        disabled={terminal}
                        onClick={() => setEditing(fair)}
                      >
                        <Edit3 size={17} /> Editar
                      </button>
                      <button
                        className="btn-outline"
                        onClick={() => setWorkspace(fair)}
                      >
                        <Users size={17} /> Participantes
                      </button>
                      {!terminal && (
                        <>
                          <ConfirmButton
                            question="¿Finalizar esta feria? Sus imágenes se eliminarán y no podrá reactivarse."
                            onConfirm={() => finish(fair, "FINISHED")}
                          >
                            <RefreshCw size={17} /> Finalizar
                          </ConfirmButton>
                          <ConfirmButton
                            question="¿Cancelar definitivamente esta feria? Sus imágenes se eliminarán."
                            onConfirm={() => finish(fair, "DISABLED")}
                          >
                            <Trash2 size={17} /> Cancelar
                          </ConfirmButton>
                        </>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          <PaginationBar pagination={list.data.pagination} onPage={setPage} />
        </>
      ) : (
        <Empty title="No hay ferias registradas" />
      )}
      {editing && (
        <FairForm
          fair={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}{" "}
      {workspace && (
        <FairWorkspace
          fair={workspace}
          exhibitors={exhibitors.data ?? []}
          onClose={() => setWorkspace(null)}
        />
      )}
    </>
  );
}

export function ProductsPage() {
  return <ProductManager mode="admin" />;
}

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const list = useQuery({
    queryKey: ["audit", query, action, entity, dateFrom, dateTo, page],
    queryFn: () =>
      api
        .get<Paged<AuditItem>>("/audit", { params: { q: query || undefined, action: action || undefined, entity: entity || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, page } })
        .then((r) => r.data),
  });
  const actions = useMemo(
    () => [...new Set(list.data?.items.map((item) => item.accion) ?? [])].sort(),
    [list.data],
  );
  const entities = useMemo(
    () => [...new Set(list.data?.items.map((item) => item.entidad) ?? [])].sort(),
    [list.data],
  );
  const reportOptions = useQuery({ queryKey: ["report-options"], queryFn: () => api.get<{ actions: string[]; entities: string[] }>("/reports/options").then((response) => response.data) });
  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase("es");
    return (list.data?.items ?? []).filter(
      (item) =>
        (!action || item.accion === action) &&
        (!entity || item.entidad === entity) &&
        (!term ||
          `${item.usuario} ${item.accion} ${item.entidad} ${item.descripcion ?? ""}`
            .toLocaleLowerCase("es")
            .includes(term)),
    );
  }, [list.data, query, action, entity]);
  return (
    <>
      <Header
        eyebrow="Trazabilidad"
        title="Auditoría"
        description="Historial de las operaciones relevantes realizadas en el sistema."
      />
      <div className="toolbar">
        <SearchField
          value={query}
          onChange={(value) => { setQuery(value); setPage(1); }}
          placeholder="Buscar en esta página…"
        />
        <select
          className="input"
          aria-label="Filtrar por acción"
          value={action}
          onChange={(event) => setAction(event.target.value)}
        >
          <option value="">Todas las acciones</option>
          {(reportOptions.data?.actions ?? actions).map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
        <select
          className="input"
          aria-label="Filtrar por entidad"
          value={entity}
          onChange={(event) => setEntity(event.target.value)}
        >
          <option value="">Todas las entidades</option>
          {(reportOptions.data?.entities ?? entities).map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
        <input className="input" type="date" aria-label="Auditoría desde" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} />
        <input className="input" type="date" aria-label="Auditoría hasta" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} />
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.error ? (
        <ErrorBox message={apiError(list.error)} />
      ) : list.data?.items.length ? (
        <>
          <div className="audit-table">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Usuario</th>
                  <th>Acción</th>
                  <th>Entidad</th>
                  <th>Descripción</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td>{new Date(item.created_at).toLocaleString("es-BO")}</td>
                    <td>{item.usuario}</td>
                    <td>
                      <strong>{item.accion}</strong>
                    </td>
                    <td>{item.entidad}</td>
                    <td>{item.descripcion || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <Empty
              title="No hay coincidencias en esta página"
              description="Cambie los filtros o avance a otra página."
            />
          )}
          <PaginationBar
            pagination={list.data.pagination ?? emptyPagination}
            onPage={setPage}
          />
        </>
      ) : (
        <Empty title="No hay eventos de auditoría" />
      )}
    </>
  );
}
