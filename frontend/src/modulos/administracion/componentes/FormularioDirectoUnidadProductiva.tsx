import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ChevronDown, Send } from "lucide-react";
import {
  api,
  type Paged,
  type ProductiveSector,
  type ProductiveUnit,
} from "../../../compartido";
import { BOLIVIA_DEPARTMENTS } from "../../../compartido/constantes/ubicacionesBolivia";
import { CajaError, Campo, EstadoCarga, useRetroalimentacion } from "../../../compartido/componentes";
import { LIMITE_IMAGEN_MB, validarArchivoImagen } from "../../../compartido/validaciones/imagenes";
import { limpiar, mensaje } from "../utilidades/administracionCompartida";
import {
  EMAIL_PATTERN,
  registroVacio,
  REGISTRATION_FIELD_LABELS,
  REPRESENTATIVE_NAME_PATTERN,
  sanearNombreRepresentante,
  SOCIAL_URL_PATTERNS,
  CampoUrlSocial,
  type BorradorRegistro,
} from "../../registro/componentes/formularioRegistro";

export function FormularioDirectoUnidadProductiva({
  onCreated,
  onClose,
}: {
  onCreated: () => void;
  onClose: () => void;
}) {
  const feedback = useRetroalimentacion();
  const formRef = useRef<HTMLFormElement | null>(null);
  const [draft, setDraft] = useState(registroVacio);
  const [sectorIds, setSectorIds] = useState<string[]>([]);
  const [mobileSectorMenuOpen, setMobileSectorMenuOpen] = useState(false);
  const [otherDetail, setOtherDetail] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const sectors = useQuery({
    queryKey: ["productive-sectors", "active"],
    queryFn: () =>
      api
        .get<Paged<ProductiveSector>>("/productive-sectors", {
          params: { per_page: 100 },
        })
        .then((response) => response.data.items),
  });
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
    if (errorMessage.includes("correo")) return "correo_electronico";
    if (errorMessage.includes("nit")) return "nit";
    if (errorMessage.includes("logotipo")) return "logo";
    return "";
  };
  const change = (key: keyof BorradorRegistro, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const toggleSector = (sectorId: string) =>
    setSectorIds((current) =>
      current.includes(sectorId)
        ? current.filter((id) => id !== sectorId)
        : [...current, sectorId],
    );
  const mobileSectorLabel = !sectorIds.length
    ? "Seleccione uno o varios sectores"
    : sectorIds.length === 1
      ? sectors.data?.find((item) => item.id === sectorIds[0])?.nombre ?? "1 sector seleccionado"
      : `${sectorIds.length} sectores seleccionados`;
  const mutation = useMutation({
    mutationFn: async () => {
      let logo_url: string | null = null;
      if (logo) {
        const form = new FormData();
        form.append("file", logo);
        logo_url = (
          await api.post<{ url: string }>("/registration-requests/logo", form)
        ).data.url;
      }
      const selected = sectorIds.map((id) => {
        const sector = sectors.data?.find((item) => item.id === id);
        return {
          productive_sector_id: id,
          detalle_otro: sector?.es_otro ? limpiar(otherDetail) : null,
        };
      });
      return api.post<ProductiveUnit>("/admin/productive-units", {
        ...draft,
        nit: limpiar(draft.nit),
        registro_seprec: limpiar(draft.registro_seprec),
        registro_pro_bolivia: limpiar(draft.registro_pro_bolivia),
        facebook_url: limpiar(draft.facebook_url),
        instagram_url: limpiar(draft.instagram_url),
        tiktok_url: limpiar(draft.tiktok_url),
        logo_url,
        sectores: selected,
      });
    },
    onSuccess: () => {
      feedback.success(
        "Unidad Productiva registrada",
        "Las credenciales fueron enviadas al correo de la nueva unidad.",
      );
      onCreated();
    },
    onError: (error) => {
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
      feedback.error(
        "No se pudo registrar la Unidad Productiva",
        mensaje(error),
      );
    },
  });
  const otherSelected = sectors.data?.some(
    (item) => item.es_otro && sectorIds.includes(item.id),
  );
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
        REGISTRATION_FIELD_LABELS[invalidControl.name] ?? "indicado";
      const popupMessage = invalidControl.validity.valueMissing
        ? `Complete el campo "${label}". Al cerrar este mensaje quedará marcado para que pueda corregirlo.`
        : `Revise el formato del campo "${label}". Al cerrar este mensaje quedará marcado para que pueda corregirlo.`;
      focusInvalidControl(invalidControl, popupMessage);
      return;
    }
    if (!sectorIds.length) {
      const firstSector =
        Array.from(
          event.currentTarget.querySelectorAll<HTMLInputElement>(
            'input[name="sectores"]',
          ),
        ).find((input) => input.offsetParent !== null) ??
        event.currentTarget.querySelector<HTMLInputElement>(
          'input[name="sectores"]',
        );
      if (firstSector)
        focusInvalidControl(
          firstSector,
          "Seleccione al menos un Sector Productivo. Al cerrar este mensaje podrá elegirlo.",
        );
      return;
    }
    mutation.mutate();
  };
  return (
    <form
      ref={formRef}
      className="registration-form"
      noValidate
      onSubmit={submit}
      onInput={(event) =>
        (event.target as HTMLElement).removeAttribute("aria-invalid")
      }
    >
      {" "}
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>01</span>
          <div>
            <h2>Datos de la unidad</h2>
            <p>Información comercial y registros institucionales.</p>
          </div>
        </div>
        <div className="registration-grid">
          {" "}
          <Campo label="Nombre comercial" required>
            <input
              className="input"
              name="nombre_comercial"
              required
              maxLength={200}
              autoComplete="organization"
              placeholder="Nombre con el que se presenta al público"
              value={draft.nombre_comercial}
              onChange={(e) => change("nombre_comercial", e.target.value)}
            />
          </Campo>{" "}
          <Campo label="Razón social" required>
            <input
              className="input"
              name="razon_social"
              required
              placeholder="Nombre legal de la organización"
              value={draft.razon_social}
              onChange={(e) => change("razon_social", e.target.value)}
            />
          </Campo>{" "}
          <Campo label="NIT" optional>
            <input
              className="input"
              name="nit"
              inputMode="numeric"
              pattern="[0-9]{5,12}"
              maxLength={12}
              placeholder="Número de identificación tributaria"
              value={draft.nit}
              onChange={(e) =>
                change("nit", e.target.value.replace(/\D/g, "").slice(0, 12))
              }
            />
          </Campo>{" "}
          <Campo label="Registro SEPREC" optional>
            <input
              className="input"
              name="registro_seprec"
              inputMode="numeric"
              pattern="[0-9]{5,12}"
              maxLength={12}
              placeholder="Número de Matrícula de Comercio"
              value={draft.registro_seprec}
              onChange={(e) =>
                change(
                  "registro_seprec",
                  e.target.value.replace(/\D/g, "").slice(0, 12),
                )
              }
            />
          </Campo>{" "}
          <Campo label="Registro PRO-BOLIVIA" optional>
            <input
              className="input"
              name="registro_pro_bolivia"
              inputMode="numeric"
              pattern="[0-9]{5,12}"
              maxLength={12}
              placeholder="Número de registro PRO-BOLIVIA"
              value={draft.registro_pro_bolivia}
              onChange={(e) =>
                change(
                  "registro_pro_bolivia",
                  e.target.value.replace(/\D/g, "").slice(0, 12),
                )
              }
            />
          </Campo>{" "}
        </div>
      </section>{" "}
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>02</span>
          <div>
            <h2>Contacto y ubicación</h2>
            <p>Datos de la persona responsable y medios de contacto.</p>
          </div>
        </div>
        <div className="registration-grid">
          {" "}
          <Campo label="Nombres del representante" required>
            <input
              className="input"
              name="nombres_representante"
              required
              maxLength={100}
              pattern={REPRESENTATIVE_NAME_PATTERN}
              placeholder="Nombres"
              value={draft.nombres_representante}
              onChange={(e) =>
                change(
                  "nombres_representante",
                  sanearNombreRepresentante(e.target.value),
                )
              }
            />
          </Campo>{" "}
          <Campo label="Apellido paterno" required>
            <input
              className="input"
              name="apellido_paterno_representante"
              required
              maxLength={100}
              pattern={REPRESENTATIVE_NAME_PATTERN}
              placeholder="Apellido paterno"
              value={draft.apellido_paterno_representante}
              onChange={(e) =>
                change(
                  "apellido_paterno_representante",
                  sanearNombreRepresentante(e.target.value),
                )
              }
            />
          </Campo>{" "}
          <Campo label="Apellido materno" required>
            <input
              className="input"
              name="apellido_materno_representante"
              required
              maxLength={100}
              pattern={REPRESENTATIVE_NAME_PATTERN}
              placeholder="Apellido materno"
              value={draft.apellido_materno_representante}
              onChange={(e) =>
                change(
                  "apellido_materno_representante",
                  sanearNombreRepresentante(e.target.value),
                )
              }
            />
          </Campo>{" "}
          <Campo label="Departamento" required>
            <select
              className="input"
              name="departamento"
              required
              value={draft.departamento}
              onChange={(e) => change("departamento", e.target.value)}
            >
              <option value="">Seleccione un departamento</option>
              {BOLIVIA_DEPARTMENTS.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Campo>{" "}
          <Campo
            label="Dirección física de la Planta de Producción o Taller"
            required
          >
            <input
              className="input"
              name="direccion_fisica"
              required
              placeholder="Zona, avenida o calle"
              value={draft.direccion_fisica}
              onChange={(e) => change("direccion_fisica", e.target.value)}
            />
          </Campo>{" "}
          <Campo label="Teléfono o WhatsApp" required>
            <input
              className="input"
              name="telefono_whatsapp"
              type="tel"
              required
              inputMode="numeric"
              pattern="[67][0-9]{7}"
              maxLength={8}
              placeholder="Ej. 70000000"
              value={draft.telefono_whatsapp}
              onChange={(e) =>
                change(
                  "telefono_whatsapp",
                  e.target.value.replace(/\D/g, "").slice(0, 8),
                )
              }
            />
          </Campo>{" "}
          <Campo label="Correo electrónico" required>
            <input
              className="input"
              name="correo_electronico"
              type="email"
              required
              inputMode="email"
              maxLength={255}
              pattern={EMAIL_PATTERN}
              placeholder="correo@dominio.com"
              value={draft.correo_electronico}
              onChange={(e) => change("correo_electronico", e.target.value)}
            />
          </Campo>{" "}
        </div>
      </section>{" "}
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>03</span>
          <div>
            <h2>Presencia digital</h2>
            <p>Redes sociales y logotipo opcional de la unidad.</p>
          </div>
        </div>
        <div className="registration-grid">
          {" "}
          <CampoUrlSocial
            name="facebook_url"
            label="Facebook"
            value={draft.facebook_url}
            example="https://facebook.com/mi.unidad"
            pattern={SOCIAL_URL_PATTERNS.facebook}
            error="Ingrese una URL válida de Facebook que comience con https://"
            onChange={(value) => change("facebook_url", value)}
          />{" "}
          <CampoUrlSocial
            name="instagram_url"
            label="Instagram"
            value={draft.instagram_url}
            example="https://instagram.com/mi.unidad"
            pattern={SOCIAL_URL_PATTERNS.instagram}
            error="Ingrese una URL válida de Instagram que comience con https://"
            onChange={(value) => change("instagram_url", value)}
          />{" "}
          <CampoUrlSocial
            name="tiktok_url"
            label="TikTok"
            value={draft.tiktok_url}
            example="https://tiktok.com/@mi.unidad"
            pattern={SOCIAL_URL_PATTERNS.tiktok}
            error="Ingrese una URL válida de TikTok que comience con https://"
            onChange={(value) => change("tiktok_url", value)}
          />{" "}
          <Campo
            label="Logotipo"
            optional
            hint={`Formatos permitidos: PNG, JPG, JPEG y WebP. Tamaño máximo: ${LIMITE_IMAGEN_MB} MB.`}
          >
            <input
              className="input registration-file"
              name="logo"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                if (!file) {
                  setLogo(null);
                  return;
                }
                const validation = validarArchivoImagen(file, {
                  label: "el logotipo",
                });
                if (!validation.ok) {
                  event.target.value = "";
                  setLogo(null);
                  feedback.error(validation.title, validation.message);
                  return;
                }
                setLogo(file);
              }}
            />
          </Campo>{" "}
        </div>
      </section>{" "}
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>04</span>
          <div>
            <h2>Actividad productiva</h2>
            <p>
              Seleccione al menos un sector y describa brevemente su oferta.
            </p>
          </div>
        </div>{" "}
        <Campo label="Sectores Productivos" required>
          {sectors.isLoading ? (
            <EstadoCarga label="Cargando sectores..." />
          ) : sectors.error ? (
            <CajaError mensaje={mensaje(sectors.error)} />
          ) : (
            <>
              <div className="registration-sectors">
                {sectors.data?.map((item) => (
                  <label key={item.id}>
                    <input
                      name="sectores"
                      type="checkbox"
                      checked={sectorIds.includes(item.id)}
                      onChange={() => toggleSector(item.id)}
                    />
                    <span>{item.nombre}</span>
                  </label>
                ))}
              </div>
              <div
                className={`admin-mobile-sector-select ${mobileSectorMenuOpen ? "is-open" : ""}`}
              >
                <button
                  type="button"
                  className="admin-mobile-sector-select-trigger"
                  aria-expanded={mobileSectorMenuOpen}
                  aria-label="Seleccionar sectores productivos"
                  onClick={() => setMobileSectorMenuOpen((current) => !current)}
                >
                  <span>{mobileSectorLabel}</span>
                  <ChevronDown size={18} />
                </button>
                {mobileSectorMenuOpen && (
                  <div className="admin-mobile-sector-select-menu">
                    <div className="admin-mobile-sector-select-actions">
                      <button
                        type="button"
                        onClick={() => {
                          setSectorIds([]);
                          setMobileSectorMenuOpen(false);
                        }}
                      >
                        Limpiar
                      </button>
                    </div>
                    <div className="admin-mobile-sector-select-options">
                      {sectors.data?.map((item) => (
                        <label key={item.id}>
                          <input
                            name="sectores"
                            type="checkbox"
                            checked={sectorIds.includes(item.id)}
                            onChange={() => toggleSector(item.id)}
                          />
                          <span>{item.nombre}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </Campo>{" "}
        {otherSelected && (
          <Campo label="Detalle de Otros" required>
            <input
              className="input"
              name="detalle_otro"
              required
              placeholder="Describa su actividad productiva"
              value={otherDetail}
              onChange={(e) => setOtherDetail(e.target.value)}
            />
          </Campo>
        )}{" "}
        <div className="registration-review-field">
          <Campo label="Reseña comercial" required>
            <textarea
              className="input"
              name="resena_comercial"
              required
              rows={5}
              placeholder="Cuéntenos qué produce, cómo trabaja y qué distingue a su unidad"
              value={draft.resena_comercial}
              onChange={(e) => change("resena_comercial", e.target.value)}
            />
          </Campo>
        </div>{" "}
      </section>{" "}
      <footer className="registration-actions">
        <span>
          {sectorIds.length
            ? "Las credenciales se enviarán al correo registrado."
            : "Seleccione al menos un sector productivo."}
        </span>
        <div className="modal-actions">
          <button
            type="button"
            className="admin-unit-action-button admin-unit-action-button-danger"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            className="admin-unit-action-button registration-submit"
            disabled={mutation.isPending}
          >
            <Send aria-hidden="true" />
            {mutation.isPending ? "Registrando..." : "Registrar"}
          </button>
        </div>
      </footer>{" "}
    </form>
  );
}
