import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  BadgeCheck,
  Building2,
  Camera,
  Edit3,
  Factory,
  Mail,
  MapPin,
  Phone,
  UserRound,
} from "lucide-react";
import { errorApi, urlRecurso, type ProductiveUnit } from "../../../compartido";
import { BOLIVIA_DEPARTMENTS } from "../../../compartido/constantes/ubicacionesBolivia";
import {
  CajaError,
  Campo,
  EstadoCarga,
  Modal,
  InsigniaEstado,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { TarjetaContrasenaPerfil } from "../../autenticacion/componentes/TarjetaContrasenaPerfil";
import { servicioUnidadProductiva } from "../servicios/servicioUnidadProductiva";
import "../estilos/unidad-productiva.css";
import "../estilos/perfil.css";

type EditableProfileKey =
  | "nombre_comercial"
  | "razon_social"
  | "nombres_representante"
  | "apellido_paterno_representante"
  | "apellido_materno_representante"
  | "departamento"
  | "direccion_fisica"
  | "telefono_whatsapp"
  | "correo_electronico"
  | "facebook_url"
  | "instagram_url"
  | "tiktok_url"
  | "resena_comercial";

type ProfileErrors = Partial<Record<EditableProfileKey, string>>;

type ProfileFieldDefinition = {
  key: Exclude<EditableProfileKey, "resena_comercial">;
  label: string;
  hint: string;
  placeholder: string;
  required?: boolean;
  type?: "text" | "email" | "url";
  maxLength?: number;
};

const identityFields: ProfileFieldDefinition[] = [
  {
    key: "nombre_comercial",
    label: "Nombre comercial",
    hint: "Ingrese el nombre con el que su unidad se presenta al público.",
    placeholder: "Ej.: Sabores del Valle",
    required: true,
    maxLength: 200,
  },
  {
    key: "razon_social",
    label: "Razón social",
    hint: "Ingrese el nombre legal o registrado de la unidad productiva.",
    placeholder: "Ej.: Sabores del Valle SRL",
    required: true,
    maxLength: 200,
  },
];

const representativeFields: ProfileFieldDefinition[] = [
  {
    key: "nombres_representante",
    label: "Nombres del representante",
    hint: "Ingrese únicamente los nombres de la persona representante.",
    placeholder: "Ej.: María Elena",
    required: true,
    maxLength: 100,
  },
  {
    key: "apellido_paterno_representante",
    label: "Apellido paterno",
    hint: "Ingrese únicamente el apellido paterno del representante.",
    placeholder: "Ej.: Quispe",
    required: true,
    maxLength: 100,
  },
  {
    key: "apellido_materno_representante",
    label: "Apellido materno",
    hint: "Ingrese únicamente el apellido materno del representante.",
    placeholder: "Ej.: Mamani",
    required: true,
    maxLength: 100,
  },
  {
    key: "departamento",
    label: "Departamento",
    hint: "Seleccione el departamento donde funciona la unidad productiva.",
    placeholder: "Seleccione un departamento",
    required: true,
  },
  {
    key: "direccion_fisica",
    label: "Dirección",
    hint: "Ingrese la zona, avenida, calle y número donde se encuentra la unidad.",
    placeholder: "Ej.: Zona Central, avenida Bolivia N.º 120",
    required: true,
    maxLength: 255,
  },
];

const contactFields: ProfileFieldDefinition[] = [
  {
    key: "telefono_whatsapp",
    label: "WhatsApp",
    hint: "Ingrese un número de WhatsApp de exactamente ocho dígitos.",
    placeholder: "Ej.: 71234567",
    required: true,
    maxLength: 8,
  },
  {
    key: "correo_electronico",
    label: "Correo electrónico",
    hint: "Ingrese un correo válido que pueda recibir mensajes.",
    placeholder: "Ej.: contacto@empresa.com",
    required: true,
    type: "email",
    maxLength: 255,
  },
];

const socialFields: ProfileFieldDefinition[] = [
  {
    key: "facebook_url",
    label: "Facebook",
    hint: "Pegue el enlace completo de la página o perfil de Facebook.",
    placeholder: "https://facebook.com/miunidad",
    type: "url",
  },
  {
    key: "instagram_url",
    label: "Instagram",
    hint: "Pegue el enlace completo del perfil de Instagram.",
    placeholder: "https://instagram.com/miunidad",
    type: "url",
  },
  {
    key: "tiktok_url",
    label: "TikTok",
    hint: "Pegue el enlace completo del perfil de TikTok.",
    placeholder: "https://tiktok.com/@miunidad",
    type: "url",
  },
];

const alphanumericProfileText = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$/;
const personNameText = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$/;
const emailText = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const isValidCommercialName = (value: string) =>
  [...value].every((character) => {
    const code = character.charCodeAt(0);
    return code > 31 && code !== 127;
  });

function isWebUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function validateProfileDraft(draft: Partial<ProductiveUnit>): ProfileErrors {
  const errors: ProfileErrors = {};
  const required: EditableProfileKey[] = [
    "nombre_comercial",
    "razon_social",
    "nombres_representante",
    "apellido_paterno_representante",
    "apellido_materno_representante",
    "departamento",
    "direccion_fisica",
    "telefono_whatsapp",
    "correo_electronico",
    "resena_comercial",
  ];
  required.forEach((key) => {
    if (!String(draft[key] ?? "").trim())
      errors[key] = "Este campo es obligatorio.";
  });
  const commercialName = String(draft.nombre_comercial ?? "").trim();
  if (commercialName && !isValidCommercialName(commercialName))
    errors.nombre_comercial =
      "Use letras, números, espacios o signos visibles, sin saltos de línea.";
  const legalName = String(draft.razon_social ?? "").trim();
  if (legalName && !alphanumericProfileText.test(legalName))
    errors.razon_social = "Use solamente letras, números y espacios.";
  (
    [
      "nombres_representante",
      "apellido_paterno_representante",
      "apellido_materno_representante",
    ] as const
  ).forEach((key) => {
    const value = String(draft[key] ?? "").trim();
    if (value && !personNameText.test(value))
      errors[key] = "Use solamente letras y espacios.";
  });
  if (draft.departamento && !BOLIVIA_DEPARTMENTS.includes(draft.departamento))
    errors.departamento = "Seleccione un departamento válido.";
  if (draft.telefono_whatsapp && !/^\d{8}$/.test(draft.telefono_whatsapp))
    errors.telefono_whatsapp = "Ingrese exactamente ocho dígitos.";
  if (
    draft.correo_electronico &&
    !emailText.test(draft.correo_electronico.trim())
  )
    errors.correo_electronico = "Ingrese un correo electrónico válido.";
  (["facebook_url", "instagram_url", "tiktok_url"] as const).forEach((key) => {
    const value = String(draft[key] ?? "").trim();
    if (value && !isWebUrl(value))
      errors[key] =
        "Ingrese un enlace completo que comience con http:// o https://.";
  });
  return errors;
}

export function PaginaPerfilUnidadProductiva() {
  const queryClient = useQueryClient();
  const feedback = useRetroalimentacion();
  const [editing, setEditing] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [draft, setDraft] = useState<Partial<ProductiveUnit>>({});
  const [profileErrors, setProfileErrors] = useState<ProfileErrors>({});

  const profile = useQuery({
    queryKey: ["productive-unit-profile"],
    queryFn: servicioUnidadProductiva.getProfile,
  });
  if (profile.isLoading) return <EstadoCarga />;
  if (profile.error || !profile.data) {
    return <CajaError mensaje={errorApi(profile.error)} />;
  }

  const unit = profile.data;
  const startEditing = () => {
    setDraft(unit);
    setProfileErrors({});
    setEditing(true);
  };
  const save = async () => {
    const errors = validateProfileDraft(draft);
    if (Object.keys(errors).length) {
      setProfileErrors(errors);
      feedback.error(
        "Revise el formulario",
        Object.values(errors)[0] ?? "Hay datos inválidos.",
      );
      return;
    }
    const {
      nombre_comercial,
      razon_social,
      nit,
      registro_seprec,
      registro_pro_bolivia,
      nombres_representante,
      apellido_paterno_representante,
      apellido_materno_representante,
      departamento,
      direccion_fisica,
      telefono_whatsapp,
      correo_electronico,
      facebook_url,
      instagram_url,
      tiktok_url,
      resena_comercial,
    } = draft;

    try {
      await servicioUnidadProductiva.updateProfile({
        nombre_comercial: nombre_comercial?.trim(),
        razon_social: razon_social?.trim(),
        nit,
        registro_seprec,
        registro_pro_bolivia,
        nombres_representante: nombres_representante?.trim(),
        apellido_paterno_representante: apellido_paterno_representante?.trim(),
        apellido_materno_representante: apellido_materno_representante?.trim(),
        departamento,
        direccion_fisica: direccion_fisica?.trim(),
        telefono_whatsapp,
        correo_electronico: correo_electronico?.trim(),
        facebook_url: facebook_url?.trim() || null,
        instagram_url: instagram_url?.trim() || null,
        tiktok_url: tiktok_url?.trim() || null,
        resena_comercial: resena_comercial?.trim(),
      });
      await queryClient.invalidateQueries({
        queryKey: ["productive-unit-profile"],
      });
      setEditing(false);
      feedback.success("Perfil actualizado", unit.nombre_comercial);
    } catch (error) {
      feedback.error("No se pudo actualizar", errorApi(error));
    }
  };

  const updateDraftValue = (key: EditableProfileKey, rawValue: string) => {
    let value = rawValue;
    if (
      [
        "nombres_representante",
        "apellido_paterno_representante",
        "apellido_materno_representante",
      ].includes(key)
    ) {
      value = value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]/g, "");
    }
    if (key === "razon_social") {
      value = value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]/g, "");
    }
    if (key === "telefono_whatsapp") {
      value = value.replace(/\D/g, "").slice(0, 8);
    }
    setDraft((current) => ({ ...current, [key]: value }));
    setProfileErrors((current) => ({ ...current, [key]: undefined }));
  };

  const renderProfileField = (field: ProfileFieldDefinition) => {
    const value = String(draft[field.key] ?? "");
    const error = profileErrors[field.key];
    const optional = !field.required;
    return (
      <Campo
        key={field.key}
        label={field.label}
        hint={field.hint}
        hintAsHelp
        required={field.required}
        optional={optional}
      >
        {field.key === "departamento" ? (
          <select
            className={`input ${error ? "input-error" : ""}`}
            aria-label={field.label}
            value={value}
            aria-invalid={Boolean(error)}
            onChange={(event) =>
              updateDraftValue(field.key, event.target.value)
            }
          >
            <option value="">Seleccione un departamento</option>
            {BOLIVIA_DEPARTMENTS.map((department) => (
              <option key={department} value={department}>
                {department}
              </option>
            ))}
          </select>
        ) : (
          <input
            className={`input ${error ? "input-error" : ""}`}
            aria-label={field.label}
            type={field.type ?? "text"}
            inputMode={
              field.key === "telefono_whatsapp" ? "numeric" : undefined
            }
            maxLength={field.maxLength}
            placeholder={field.placeholder}
            required={field.required}
            aria-invalid={Boolean(error)}
            value={value}
            onChange={(event) =>
              updateDraftValue(field.key, event.target.value)
            }
          />
        )}
        {error && (
          <small className="field-error" role="alert">
            {error}
          </small>
        )}
      </Campo>
    );
  };

  return (
    <section className="unit-profile-page">
      <header className="unit-profile-hero">
        <div className="unit-profile-identity">
          <span className="unit-profile-hero-icon">
            <Factory size={28} />
          </span>
          <div>
            <span className="unit-profile-kicker">MI UNIDAD PRODUCTIVA</span>
            <h1>{unit.nombre_comercial}</h1>
            <div className="unit-profile-status-row">
              <InsigniaEstado value={unit.estado} />
              <span>{unit.razon_social}</span>
            </div>
          </div>
        </div>
        <button
          className="unit-profile-edit-button"
          aria-label="Editar perfil"
          onClick={startEditing}
        >
          <Edit3 size={18} />
          Editar información
        </button>
      </header>

      <div className="unit-profile-layout">
        <aside className="unit-profile-logo-card">
          <div className="unit-profile-card-heading">
            <div>
              <span>IDENTIDAD VISUAL</span>
              <h2>Logotipo</h2>
            </div>
            <Camera size={20} />
          </div>
          <div
            className={`unit-profile-logo-frame ${unit.logo_url ? "has-logo" : ""}`}
          >
            {unit.logo_url ? (
              <img
                src={urlRecurso(unit.logo_url)}
                alt={`Logo de ${unit.nombre_comercial}`}
              />
            ) : (
              <div className="unit-profile-logo-placeholder">
                <Factory size={42} />
                <strong>Sin logotipo</strong>
                <span>Agregue la imagen representativa de su unidad.</span>
              </div>
            )}
          </div>
          <label
            className={`unit-profile-logo-button ${uploadingLogo ? "is-busy" : ""}`}
          >
            <Camera size={17} />
            <span>
              {uploadingLogo
                ? "Actualizando…"
                : unit.logo_url
                  ? "Cambiar logotipo"
                  : "Agregar logotipo"}
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={uploadingLogo}
              onChange={async (event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                setUploadingLogo(true);
                try {
                  await servicioUnidadProductiva.uploadLogo(file);
                  await queryClient.invalidateQueries({
                    queryKey: ["productive-unit-profile"],
                  });
                  feedback.success(
                    "Logotipo actualizado",
                    unit.nombre_comercial,
                  );
                } catch (error) {
                  feedback.error(
                    "No se pudo actualizar el logotipo",
                    errorApi(error),
                  );
                } finally {
                  setUploadingLogo(false);
                }
              }}
            />
          </label>
          <small className="unit-profile-logo-hint">
            Use una imagen clara en formato JPG, PNG o WebP.
          </small>
        </aside>

        <div className="unit-profile-details">
          <article className="unit-profile-about-card">
            <div className="unit-profile-card-heading">
              <div>
                <span>PERFIL COMERCIAL</span>
                <h2>Sobre la unidad</h2>
              </div>
              <Building2 size={21} />
            </div>
            <p>
              {unit.resena_comercial ||
                "Todavía no se registró una reseña comercial."}
            </p>
          </article>

          <div className="unit-profile-info-grid">
            <article className="unit-profile-info-card">
              <span className="unit-profile-info-icon">
                <UserRound size={20} />
              </span>
              <div>
                <small>REPRESENTANTE</small>
                <strong>{unit.nombre_representante}</strong>
              </div>
            </article>
            <article className="unit-profile-info-card">
              <span className="unit-profile-info-icon">
                <Phone size={20} />
              </span>
              <div>
                <small>WHATSAPP</small>
                <strong>{unit.telefono_whatsapp}</strong>
              </div>
            </article>
            <article className="unit-profile-info-card">
              <span className="unit-profile-info-icon">
                <Mail size={20} />
              </span>
              <div>
                <small>CORREO ELECTRÓNICO</small>
                <strong>{unit.correo_electronico}</strong>
              </div>
            </article>
            <article className="unit-profile-info-card">
              <span className="unit-profile-info-icon">
                <MapPin size={20} />
              </span>
              <div>
                <small>UBICACIÓN</small>
                <strong>{unit.departamento}</strong>
                <span>{unit.direccion_fisica}</span>
              </div>
            </article>
          </div>

          <article className="unit-profile-records-card">
            <div className="unit-profile-card-heading">
              <div>
                <span>DATOS INSTITUCIONALES</span>
                <h2>Registros</h2>
              </div>
              <BadgeCheck size={21} />
            </div>
            <div className="unit-profile-records-grid">
              <div>
                <small>Razón social</small>
                <strong>{unit.razon_social}</strong>
              </div>
              <div>
                <small>NIT</small>
                <strong>{unit.nit || "No registrado"}</strong>
              </div>
              <div>
                <small>Registro SEPREC</small>
                <strong>{unit.registro_seprec || "No registrado"}</strong>
              </div>
              <div>
                <small>Registro PRO-BOLIVIA</small>
                <strong>{unit.registro_pro_bolivia || "No registrado"}</strong>
              </div>
            </div>
          </article>

          <article className="unit-profile-sectors-card">
            <div className="unit-profile-card-heading">
              <div>
                <span>ACTIVIDAD PRODUCTIVA</span>
                <h2>Sectores</h2>
              </div>
              <Factory size={21} />
            </div>
            <div className="unit-profile-sector-list">
              {unit.sectores.length ? (
                unit.sectores.map((sector) => (
                  <span key={sector.id}>{sector.nombre}</span>
                ))
              ) : (
                <p>Sin sectores registrados.</p>
              )}
            </div>
          </article>
        </div>
      </div>
      {editing && (
        <Modal
          title="Editar perfil"
          wide
          hideHeader
          className="unit-profile-editor-modal"
          onClose={() => {
            setEditing(false);
            setProfileErrors({});
          }}
        >
          <div className="unit-profile-editor-intro">
            <span>PERFIL DE LA UNIDAD PRODUCTIVA</span>
            <h3>Actualice su información</h3>
            <p>
              Estos datos identifican a su unidad y se mostrarán en el catálogo
              público.
            </p>
          </div>

          <div className="unit-profile-editor-section-heading">
            <span>01</span>
            <div>
              <h3>Identidad comercial</h3>
              <p>Nombre público y denominación legal de la unidad.</p>
            </div>
          </div>
          <div className="form-grid unit-profile-editor-form">
            {identityFields.map(renderProfileField)}
          </div>

          <div className="unit-profile-editor-section-heading">
            <span>02</span>
            <div>
              <h3>Representante y ubicación</h3>
              <p>Datos de la persona responsable y dirección de trabajo.</p>
            </div>
          </div>
          <div className="form-grid unit-profile-editor-form">
            {representativeFields.map(renderProfileField)}
          </div>

          <div className="unit-profile-editor-section-heading">
            <span>03</span>
            <div>
              <h3>Información de contacto</h3>
              <p>Canales que utilizarán los visitantes para comunicarse.</p>
            </div>
          </div>
          <div className="form-grid unit-profile-editor-form">
            {contactFields.map(renderProfileField)}
          </div>

          <div className="unit-profile-editor-section-heading">
            <span>04</span>
            <div>
              <h3>Redes sociales</h3>
              <p>Enlaces opcionales a los perfiles oficiales de la unidad.</p>
            </div>
          </div>
          <div className="form-grid unit-profile-editor-form unit-profile-social-grid">
            {socialFields.map(renderProfileField)}
          </div>

          <div className="unit-profile-editor-section-heading">
            <span>05</span>
            <div>
              <h3>Reseña comercial</h3>
              <p>Presentación breve para los visitantes del catálogo.</p>
            </div>
          </div>
          <div className="unit-profile-editor-form unit-profile-editor-review">
            <Campo
              label="Reseña"
              hint="Describa qué produce, cómo trabaja y qué distingue a su unidad productiva."
              hintAsHelp
              required
            >
              <textarea
                className={`input ${profileErrors.resena_comercial ? "input-error" : ""}`}
                aria-label="Reseña"
                rows={5}
                maxLength={5000}
                placeholder="Cuente brevemente la historia, especialidad y fortalezas de su unidad."
                aria-invalid={Boolean(profileErrors.resena_comercial)}
                value={draft.resena_comercial ?? ""}
                onChange={(event) =>
                  updateDraftValue("resena_comercial", event.target.value)
                }
              />
              {profileErrors.resena_comercial && (
                <small className="field-error" role="alert">
                  {profileErrors.resena_comercial}
                </small>
              )}
            </Campo>
          </div>

          <div className="unit-profile-editor-footer">
            <p>
              Los campos marcados con <strong>*</strong> son obligatorios.
            </p>
            <div>
              <button
                className="btn-outline"
                onClick={() => {
                  setEditing(false);
                  setProfileErrors({});
                }}
              >
                Cancelar
              </button>
              <button className="btn" onClick={() => void save()}>
                Guardar cambios
              </button>
            </div>
          </div>
        </Modal>
      )}

      <TarjetaContrasenaPerfil />
    </section>
  );
}
