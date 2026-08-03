import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  BadgeCheck,
  BriefcaseBusiness,
  IdCard,
  Mail,
  PencilLine,
  Phone,
  Save,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";
import { errorApi, type AdminUser } from "../../../compartido";
import {
  CajaError,
  Campo,
  EstadoCarga,
  InsigniaEstado,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { useAutenticacion } from "../../autenticacion/contexto/ContextoAutenticacion";
import { TarjetaContrasenaPerfil } from "../../autenticacion/componentes/TarjetaContrasenaPerfil";
import { servicioPerfilAdmin } from "../servicios/servicioPerfilAdmin";
import "../../unidad-productiva/estilos/perfil.css";

type PerfilAdminEditable = Pick<
  AdminUser,
  | "first_name"
  | "apellido_paterno"
  | "apellido_materno"
  | "email"
  | "phone"
  | "cargo"
  | "unidad"
  | "observaciones"
>;

type ErroresPerfilAdmin = Partial<Record<keyof PerfilAdminEditable, string>>;

type PerfilAdminDraft = {
  first_name: string;
  apellido_paterno: string;
  apellido_materno: string;
  email: string;
  phone: string;
  cargo: string;
  unidad: string;
  observaciones: string;
};

const textoNombre = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$/;
const textoTelefono = /^\d{8}$/;
const textoCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function inicialesPerfil(user: AdminUser) {
  const first = user.first_name?.trim().charAt(0) ?? "";
  const last = user.apellido_paterno?.trim().charAt(0) ?? "";
  return `${first}${last}`.trim() || "A";
}

function construirBorrador(user: AdminUser): PerfilAdminDraft {
  return {
    first_name: user.first_name ?? "",
    apellido_paterno: user.apellido_paterno ?? "",
    apellido_materno: user.apellido_materno ?? "",
    email: user.email ?? "",
    phone: user.phone ?? "",
    cargo: user.cargo ?? "",
    unidad: user.unidad ?? "",
    observaciones: user.observaciones ?? "",
  };
}

function validarPerfil(draft: PerfilAdminDraft) {
  const errors: ErroresPerfilAdmin = {};
  const firstName = draft.first_name.trim();
  const paternalLastName = draft.apellido_paterno.trim();
  const maternalLastName = draft.apellido_materno.trim();
  const email = draft.email.trim();
  const phone = draft.phone.trim();

  if (!firstName) errors.first_name = "Ingrese sus nombres.";
  else if (!textoNombre.test(firstName)) errors.first_name = "Use solamente letras y espacios.";

  if (!paternalLastName) errors.apellido_paterno = "Ingrese su apellido paterno.";
  else if (!textoNombre.test(paternalLastName)) errors.apellido_paterno = "Use solamente letras y espacios.";

  if (!maternalLastName) {
    errors.apellido_materno = "Ingrese su apellido materno.";
  } else if (!textoNombre.test(maternalLastName)) {
    errors.apellido_materno = "Use solamente letras y espacios.";
  }

  if (!email) errors.email = "Ingrese su correo electrónico.";
  else if (!textoCorreo.test(email)) errors.email = "Ingrese un correo electrónico válido.";

  if (phone && !textoTelefono.test(phone)) {
    errors.phone = "Ingrese exactamente ocho dígitos.";
  }

  return errors;
}

function TarjetaDato({
  icon: Icon,
  label,
  value,
  secondary,
}: {
  icon: typeof UserRound;
  label: string;
  value: string;
  secondary?: string;
}) {
  return (
    <article className="admin-profile-info-card">
      <span className="admin-profile-info-icon">
        <Icon size={18} />
      </span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        {secondary ? <span>{secondary}</span> : null}
      </div>
    </article>
  );
}

export default function PaginaPerfilAdmin() {
  const queryClient = useQueryClient();
  const feedback = useRetroalimentacion();
  const { refresh } = useAutenticacion();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<PerfilAdminDraft | null>(null);
  const [errors, setErrors] = useState<ErroresPerfilAdmin>({});

  const profile = useQuery({
    queryKey: ["admin-profile"],
    queryFn: servicioPerfilAdmin.get,
  });

  if (profile.isLoading) return <EstadoCarga />;
  if (profile.error || !profile.data) {
    return <CajaError mensaje={errorApi(profile.error, "No se pudo cargar su perfil administrativo.")} />;
  }

  const user = profile.data;

  const startEditing = () => {
    setDraft(construirBorrador(user));
    setErrors({});
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setDraft(null);
    setErrors({});
  };

  const updateDraft = (field: keyof PerfilAdminEditable, rawValue: string) => {
    const value = field === "phone"
      ? rawValue.replace(/\D/g, "").slice(0, 8)
      : rawValue;
    setDraft((current) => (current ? { ...current, [field]: value } : current));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const save = async () => {
    if (!draft) return;
    const nextErrors = validarPerfil(draft);
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      feedback.error("Revise su información", Object.values(nextErrors)[0] ?? "Hay campos inválidos.");
      return;
    }

    setSaving(true);
    try {
      await servicioPerfilAdmin.update({
        first_name: draft.first_name.trim(),
        apellido_paterno: draft.apellido_paterno.trim(),
        apellido_materno: draft.apellido_materno.trim(),
        email: draft.email.trim(),
        phone: draft.phone.trim() || null,
        cargo: draft.cargo.trim() || null,
        unidad: draft.unidad.trim() || null,
        observaciones: draft.observaciones.trim() || null,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin-profile"] });
      await refresh();
      cancelEditing();
      feedback.success("Perfil actualizado", "Se guardaron los cambios de su cuenta personal.");
    } catch (error) {
      feedback.error("No se pudo actualizar su perfil", errorApi(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="admin-profile-page">
      <header className="admin-profile-hero panel">
        <div className="admin-profile-identity">
          <span className="admin-profile-avatar">{inicialesPerfil(user)}</span>
          <div className="admin-profile-identity-copy">
            <span className="eyebrow">Mi perfil</span>
            <h1>{[user.first_name, user.apellido_paterno, user.apellido_materno].filter(Boolean).join(" ")}</h1>
            <div className="admin-profile-status-row">
              <InsigniaEstado value={user.status} />
              <span>@{user.username}</span>
            </div>
            <p className="admin-profile-registered-at">
              Registrado el: {new Date(user.created_at).toLocaleDateString("es-BO")}
            </p>
          </div>
        </div>
        {!editing ? (
          <button
            className="admin-unit-action-button admin-profile-primary-button"
            onClick={startEditing}
          >
            <PencilLine size={18} />
            Editar mis datos
          </button>
        ) : null}
      </header>

      <div className="admin-profile-layout">
        {editing && draft ? (
          <section className="panel admin-profile-editor">
            <div className="admin-profile-editor-header">
              <div>
                <span className="eyebrow">Edición segura</span>
                <h2>Actualizar mis datos</h2>
              </div>
              <button
                className="admin-unit-action-button admin-unit-action-button-danger admin-profile-danger-button"
                onClick={cancelEditing}
              >
                <X size={18} />
                Cancelar
              </button>
            </div>

            <div className="admin-profile-save-row">
              <span>
                Los campos marcados con <strong>*</strong> son obligatorios.
              </span>
            </div>

            <div className="form-grid admin-profile-form-grid">
              <Campo label="Nombres" required>
                <input
                  className={`input ${errors.first_name ? "input-error" : ""}`}
                  value={draft.first_name}
                  maxLength={100}
                  aria-invalid={Boolean(errors.first_name)}
                  onChange={(event) => updateDraft("first_name", event.target.value)}
                />
                {errors.first_name ? <small className="field-error">{errors.first_name}</small> : null}
              </Campo>

              <Campo label="Apellido paterno" required>
                <input
                  className={`input ${errors.apellido_paterno ? "input-error" : ""}`}
                  value={draft.apellido_paterno}
                  maxLength={100}
                  aria-invalid={Boolean(errors.apellido_paterno)}
                  onChange={(event) => updateDraft("apellido_paterno", event.target.value)}
                />
                {errors.apellido_paterno ? <small className="field-error">{errors.apellido_paterno}</small> : null}
              </Campo>

              <Campo label="Apellido materno" required>
                <input
                  className={`input ${errors.apellido_materno ? "input-error" : ""}`}
                  value={draft.apellido_materno}
                  maxLength={100}
                  aria-invalid={Boolean(errors.apellido_materno)}
                  onChange={(event) => updateDraft("apellido_materno", event.target.value)}
                />
                {errors.apellido_materno ? <small className="field-error">{errors.apellido_materno}</small> : null}
              </Campo>

              <Campo label="Correo electrónico" required>
                <input
                  className={`input ${errors.email ? "input-error" : ""}`}
                  type="email"
                  value={draft.email}
                  maxLength={255}
                  aria-invalid={Boolean(errors.email)}
                  onChange={(event) => updateDraft("email", event.target.value)}
                />
                {errors.email ? <small className="field-error">{errors.email}</small> : null}
              </Campo>

              <Campo label="Teléfono" optional hint="Si lo registra, debe tener exactamente 8 dígitos." hintAsHelp>
                <input
                  className={`input ${errors.phone ? "input-error" : ""}`}
                  value={draft.phone}
                  inputMode="numeric"
                  maxLength={8}
                  aria-invalid={Boolean(errors.phone)}
                  onChange={(event) => updateDraft("phone", event.target.value)}
                />
                {errors.phone ? <small className="field-error">{errors.phone}</small> : null}
              </Campo>

              <Campo label="Cargo" optional>
                <input
                  className="input"
                  value={draft.cargo}
                  maxLength={150}
                  onChange={(event) => updateDraft("cargo", event.target.value)}
                />
              </Campo>

              <Campo label="Unidad administrativa" optional>
                <input
                  className="input"
                  value={draft.unidad}
                  maxLength={150}
                  onChange={(event) => updateDraft("unidad", event.target.value)}
                />
              </Campo>
            </div>

            <Campo label="Observaciones" optional>
              <textarea
                className="input"
                rows={4}
                value={draft.observaciones}
                onChange={(event) => updateDraft("observaciones", event.target.value)}
              />
            </Campo>

            <div className="profile-save-row admin-profile-save-row">
              <button
                className="admin-unit-action-button registration-submit admin-profile-primary-button"
                disabled={saving}
                onClick={() => void save()}
              >
                <Save size={18} />
                {saving ? "Guardando..." : "Guardar cambios"}
              </button>
            </div>
          </section>
        ) : (
          <article className="panel admin-profile-summary-card">
            <div className="profile-security-heading">
              <span>
                <BadgeCheck />
              </span>
              <div>
                <h2>Cuenta personal</h2>
                <p>Desde aquí puede revisar y actualizar únicamente la información de su propia cuenta administrativa.</p>
              </div>
            </div>
            <div className="admin-profile-info-grid">
              <TarjetaDato
                icon={UserRound}
                label="NOMBRE COMPLETO"
                value={[user.first_name, user.apellido_paterno, user.apellido_materno].filter(Boolean).join(" ")}
              />
              <TarjetaDato icon={Mail} label="CORREO" value={user.email} />
              <TarjetaDato icon={Phone} label="TELÉFONO" value={user.phone || "No registrado"} />
              <TarjetaDato icon={BriefcaseBusiness} label="CARGO" value={user.cargo || "No registrado"} />
              <TarjetaDato icon={ShieldCheck} label="UNIDAD" value={user.unidad || "No registrada"} />
              <TarjetaDato
                icon={IdCard}
                label="USUARIO"
                value={`@${user.username}`}
              />
            </div>
            <div className="admin-profile-notes">
              <small>OBSERVACIONES</small>
              <p>{user.observaciones || "No registró observaciones personales."}</p>
            </div>
          </article>
        )}

        <TarjetaContrasenaPerfil />
      </div>
    </section>
  );
}
