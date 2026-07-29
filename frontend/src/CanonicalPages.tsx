import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Clock3,
  ImageOff,
  ImagePlus,
  Images,
  KeyRound,
  PackageOpen,
  Pencil,
  Plus,
  Star,
  Trash2,
  Link2,
  Mail,
  Send,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  api,
  apiError,
  assetUrl,
  emptyPagination,
  type CanonicalProduct,
  type Paged,
  type ProductiveSector,
  type ProductiveUnit,
  type RegistrationRequest,
} from "./api";
import {
  ConfirmButton,
  Empty,
  ErrorBox,
  FeedbackProvider,
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
import { PublicHeader } from "./PublicHeader";
import { BOLIVIA_DEPARTMENTS } from "./boliviaLocations";
import {
  EMAIL_PATTERN,
  emptyRegistration,
  emptyRequestedProduct,
  REGISTRATION_FIELD_LABELS,
  REPRESENTATIVE_NAME_PATTERN,
  sanitizeRepresentativeName,
  SOCIAL_URL_PATTERNS,
  SocialUrlField,
  type RegistrationDraft,
  type RequestedProductDraft,
} from "./admin/registrationShared";
const pageData = <T,>(value?: Paged<T>) =>
  value ?? { items: [], pagination: emptyPagination };
const message = (error: unknown) =>
  apiError(error, "No se pudo completar la operación.");
const clean = (value: string) => value.trim() || null;
export function RegistrationPage() {
  return (
    <FeedbackProvider>
      <RegistrationPageContent />
    </FeedbackProvider>
  );
}
function RegistrationPageContent() {
  const feedback = useFeedback();
  const formRef = useRef<HTMLFormElement>(null);
  const [draft, setDraft] = useState(emptyRegistration);
  const [sectorIds, setSectorIds] = useState<string[]>([]);
  const [otherDetail, setOtherDetail] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [products, setProducts] = useState<RequestedProductDraft[]>([
    emptyRequestedProduct(),
    emptyRequestedProduct(),
    emptyRequestedProduct(),
  ]);
  const [created, setCreated] = useState<RegistrationRequest | null>(null);
  const sectors = useQuery({
    queryKey: ["productive-sectors", "active"],
    queryFn: () =>
      api
        .get<Paged<ProductiveSector>>("/productive-sectors", {
          params: { per_page: 100 },
        })
        .then((r) => r.data.items),
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
      message: popupMessage,
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
    if (errorMessage.includes("producto"))
      return "productos.0.nombre_comercial";
    if (errorMessage.includes("imagen") || errorMessage.includes("archivo"))
      return "productos.0.imagen";
    return "";
  };
  const mutation = useMutation({
    mutationFn: async () => {
      if (!logo) throw new Error("Debe subir el logotipo");
      const form = new FormData();
      form.append("file", logo);
      const logo_url = (
        await api.post<{ url: string }>("/registration-requests/logo", form)
      ).data.url;
      const uploadedProducts = await Promise.all(
        products.map(async (product) => {
          if (!product.imagen)
            throw new Error("Cada producto debe incluir una imagen");
          const productForm = new FormData();
          productForm.append("file", product.imagen);
          const imagen_url = (
            await api.post<{ url: string }>(
              "/registration-requests/products/image",
              productForm,
            )
          ).data.url;
          return {
            nombre_comercial: product.nombre_comercial,
            descripcion_tecnica: product.descripcion_tecnica,
            precio_referencia: product.precio_referencia,
            imagen_url,
          };
        }),
      );
      const selected = sectorIds.map((id) => {
        const sector = sectors.data?.find((item) => item.id === id);
        return {
          productive_sector_id: id,
          detalle_otro: sector?.es_otro ? clean(otherDetail) : null,
        };
      });
      return (
        await api.post<RegistrationRequest>("/registration-requests", {
          ...draft,
          nit: clean(draft.nit),
          registro_seprec: clean(draft.registro_seprec),
          registro_pro_bolivia: clean(draft.registro_pro_bolivia),
          facebook_url: clean(draft.facebook_url),
          instagram_url: clean(draft.instagram_url),
          tiktok_url: clean(draft.tiktok_url),
          logo_url,
          sectores: selected,
          productos: uploadedProducts,
        })
      ).data;
    },
    onSuccess: setCreated,
    onError: (error) => {
      const fieldName = fieldFromServerError(error);
      const control = fieldName
        ? formRef.current?.querySelector<
            HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
          >(`[name="${fieldName}"]`)
        : null;
      if (control) {
        focusInvalidControl(control, message(error));
        return;
      }
      feedback.error("No se pudo enviar la solicitud", message(error));
    },
  });
  if (created)
    return (
      <>
        <PublicHeader />
        <main className="container public-main registration-page">
          <section className="registration-success">
            {" "}
            <div className="registration-success-icon">
              <CheckCircle2 aria-hidden="true" />
            </div>{" "}
            <span className="registration-success-eyebrow">
              Solicitud enviada correctamente
            </span>{" "}
            <h1>Recibimos su solicitud</h1>{" "}
            <p>
              La administración revisará la información de su Unidad Productiva.
              Por ahora no necesita realizar otro registro.
            </p>{" "}
            <div className="registration-next-steps">
              {" "}
              <h2>¿Qué sucederá ahora?</h2>{" "}
              <div>
                {" "}
                <article>
                  <span>
                    <Clock3 aria-hidden="true" />
                  </span>
                  <div>
                    <strong>1. Revisión de la solicitud</strong>
                    <p>
                      La administración verificará los datos y documentos
                      enviados.
                    </p>
                  </div>
                </article>{" "}
                <article>
                  <span>
                    <Mail aria-hidden="true" />
                  </span>
                  <div>
                    <strong>2. Aviso por correo electrónico</strong>
                    <p>
                      Le comunicaremos si la solicitud fue aprobada o rechazada
                      al correo <b>{created.correo_electronico}</b>.
                    </p>
                  </div>
                </article>{" "}
                <article>
                  <span>
                    <KeyRound aria-hidden="true" />
                  </span>
                  <div>
                    <strong>3. Credenciales de acceso</strong>
                    <p>
                      Si es aprobada, el correo incluirá su{" "}
                      <b>nombre de usuario</b> y una <b>contraseña temporal</b>.
                      Deberá cambiarla cuando ingrese por primera vez.
                    </p>
                  </div>
                </article>{" "}
              </div>{" "}
            </div>{" "}
            <div className="registration-email-note">
              <Mail aria-hidden="true" />
              <span>
                Revise también las carpetas de correo no deseado o spam.
              </span>
            </div>{" "}
            <p className="registration-sent-at">
              Enviada el{" "}
              {new Date(created.fecha_solicitud).toLocaleString("es-BO")}
            </p>{" "}
            <Link className="registration-back-link" to="/catalogo">
              Volver a las ferias
            </Link>{" "}
          </section>
        </main>
      </>
    );
  const change = (key: keyof RegistrationDraft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const changeProduct = (
    index: number,
    key: keyof RequestedProductDraft,
    value: string | File | null,
  ) =>
    setProducts((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item,
      ),
    );
  const otherSelected = sectors.data?.some(
    (item) => item.es_otro && sectorIds.includes(item.id),
  );
  const submitRegistration = (event: React.FormEvent<HTMLFormElement>) => {
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
        ? `Complete el campo “${label}”. Al cerrar este mensaje quedará marcado para que pueda corregirlo.`
        : `Revise el formato del campo “${label}”. Al cerrar este mensaje quedará marcado para que pueda corregirlo.`;
      focusInvalidControl(invalidControl, popupMessage);
      return;
    }
    if (sectorIds.length === 0) {
      const firstSector = event.currentTarget.querySelector<HTMLInputElement>(
        'input[name="sectores"]',
      );
      if (firstSector)
        focusInvalidControl(
          firstSector,
          "Seleccione al menos un Sector Productivo. Al cerrar este mensaje podrá elegirlo.",
        );
      return;
    }
    const incompleteProductIndex = products.findIndex(
      (product) =>
        !product.nombre_comercial.trim() ||
        !product.descripcion_tecnica.trim() ||
        !product.precio_referencia.trim() ||
        !product.imagen,
    );
    if (incompleteProductIndex >= 0) {
      const firstProductField = event.currentTarget.querySelector<
        HTMLInputElement | HTMLTextAreaElement
      >(`[name="productos.${incompleteProductIndex}.nombre_comercial"]`);
      if (firstProductField)
        focusInvalidControl(
          firstProductField,
          "Complete obligatoriamente los tres productos requeridos.",
        );
      return;
    }
    mutation.mutate();
  };
  return (
    <>
      <PublicHeader />
      <main className="container public-main registration-page">
        {" "}
        <header className="registration-intro">
          <h1>Solicitud de Unidad Productiva</h1>
          <p>
            Complete la información para solicitar su incorporación. Cuando la
            administración apruebe la solicitud, recibirá las credenciales de
            acceso.
          </p>
          <small>
            <b className="field-required" aria-hidden="true">
              *
            </b>{" "}
            Los campos marcados con asterisco son obligatorios.
          </small>
        </header>{" "}
        <form
          ref={formRef}
          className="registration-form"
          noValidate
          onSubmit={submitRegistration}
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
              <Field label="Nombre comercial" required>
                <input
                  className="input"
                  name="nombre_comercial"
                  required
                  autoComplete="organization"
                  placeholder="Nombre con el que se presenta al público"
                  value={draft.nombre_comercial}
                  onChange={(e) => change("nombre_comercial", e.target.value)}
                />
              </Field>{" "}
              <Field label="Razón social" required>
                <input
                  className="input"
                  name="razon_social"
                  required
                  placeholder="Nombre legal de la organización"
                  value={draft.razon_social}
                  onChange={(e) => change("razon_social", e.target.value)}
                />
              </Field>{" "}
              <Field label="NIT" optional>
                <input
                  className="input"
                  name="nit"
                  inputMode="numeric"
                  pattern="[0-9]{5,12}"
                  maxLength={12}
                  placeholder="Número de identificación tributaria"
                  value={draft.nit}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Solo números, de 5 a 12 dígitos.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "nit",
                      e.target.value.replace(/\D/g, "").slice(0, 12),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Registro SEPREC" optional>
                <input
                  className="input"
                  name="registro_seprec"
                  inputMode="numeric"
                  pattern="[0-9]{5,12}"
                  maxLength={12}
                  placeholder="Número de Matrícula de Comercio"
                  value={draft.registro_seprec}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Solo números, de 5 a 12 dígitos.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "registro_seprec",
                      e.target.value.replace(/\D/g, "").slice(0, 12),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Registro PRO-BOLIVIA" optional>
                <input
                  className="input"
                  name="registro_pro_bolivia"
                  inputMode="numeric"
                  pattern="[0-9]{5,12}"
                  maxLength={12}
                  placeholder="Número de registro PRO-BOLIVIA"
                  value={draft.registro_pro_bolivia}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Solo números, de 5 a 12 dígitos.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "registro_pro_bolivia",
                      e.target.value.replace(/\D/g, "").slice(0, 12),
                    )
                  }
                />
              </Field>{" "}
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
              <Field label="Nombres del representante" required>
                <input
                  className="input"
                  name="nombres_representante"
                  required
                  autoComplete="given-name"
                  maxLength={100}
                  pattern={REPRESENTATIVE_NAME_PATTERN}
                  placeholder="Nombres"
                  value={draft.nombres_representante}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Ingrese únicamente letras, espacios, apóstrofes o guiones.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "nombres_representante",
                      sanitizeRepresentativeName(e.target.value),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Apellido paterno" required>
                <input
                  className="input"
                  name="apellido_paterno_representante"
                  required
                  autoComplete="family-name"
                  maxLength={100}
                  pattern={REPRESENTATIVE_NAME_PATTERN}
                  placeholder="Apellido paterno"
                  value={draft.apellido_paterno_representante}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Ingrese únicamente letras, espacios, apóstrofes o guiones.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "apellido_paterno_representante",
                      sanitizeRepresentativeName(e.target.value),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Apellido materno" required>
                <input
                  className="input"
                  name="apellido_materno_representante"
                  required
                  maxLength={100}
                  pattern={REPRESENTATIVE_NAME_PATTERN}
                  placeholder="Apellido materno"
                  value={draft.apellido_materno_representante}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Ingrese únicamente letras, espacios, apóstrofes o guiones.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "apellido_materno_representante",
                      sanitizeRepresentativeName(e.target.value),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Departamento" required>
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
              </Field>{" "}
              <Field
                label="Dirección física de la Planta de Producción o Taller"
                required
              >
                <input
                  className="input"
                  name="direccion_fisica"
                  required
                  autoComplete="street-address"
                  placeholder="Zona, avenida o calle"
                  value={draft.direccion_fisica}
                  onChange={(e) => change("direccion_fisica", e.target.value)}
                />
              </Field>{" "}
              <Field label="Teléfono o WhatsApp" required>
                <input
                  className="input"
                  name="telefono_whatsapp"
                  type="tel"
                  required
                  autoComplete="tel"
                  inputMode="numeric"
                  pattern="[67][0-9]{7}"
                  maxLength={8}
                  placeholder="Ej. 70000000"
                  value={draft.telefono_whatsapp}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Ingrese 8 dígitos de un celular boliviano que comience con 6 o 7.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) =>
                    change(
                      "telefono_whatsapp",
                      e.target.value.replace(/\D/g, "").slice(0, 8),
                    )
                  }
                />
              </Field>{" "}
              <Field label="Correo electrónico" required>
                <input
                  className="input"
                  name="correo_electronico"
                  type="email"
                  required
                  autoComplete="email"
                  inputMode="email"
                  maxLength={255}
                  pattern={EMAIL_PATTERN}
                  placeholder="correo@dominio.com"
                  value={draft.correo_electronico}
                  onInvalid={(e) =>
                    e.currentTarget.setCustomValidity(
                      "Ingrese un correo electrónico válido, por ejemplo: nombre@dominio.com.",
                    )
                  }
                  onInput={(e) => e.currentTarget.setCustomValidity("")}
                  onChange={(e) => change("correo_electronico", e.target.value)}
                />
              </Field>{" "}
            </div>
          </section>{" "}
          <section className="registration-section">
            <div className="registration-section-heading">
              <span>03</span>
              <div>
                <h2>Presencia digital</h2>
                <p>Redes sociales y logotipo de la unidad.</p>
              </div>
            </div>{" "}
            <div className="social-url-guide">
              <Link2 aria-hidden="true" />
              <div>
                <strong>Ingrese el enlace completo de cada perfil</strong>
                <span>
                  Abra su perfil en la red social, copie el enlace y péguelo
                  aquí. Debe comenzar con <b>https://</b>.
                </span>
              </div>
            </div>{" "}
            <div className="registration-grid">
              {" "}
              <SocialUrlField
                name="facebook_url"
                label="Facebook"
                value={draft.facebook_url}
                example="https://facebook.com/mi.unidad"
                pattern={SOCIAL_URL_PATTERNS.facebook}
                error="Ingrese una URL válida de Facebook que comience con https://, por ejemplo: https://facebook.com/mi.unidad"
                onChange={(value) => change("facebook_url", value)}
              />{" "}
              <SocialUrlField
                name="instagram_url"
                label="Instagram"
                value={draft.instagram_url}
                example="https://instagram.com/mi.unidad"
                pattern={SOCIAL_URL_PATTERNS.instagram}
                error="Ingrese una URL válida de Instagram que comience con https://, por ejemplo: https://instagram.com/mi.unidad"
                onChange={(value) => change("instagram_url", value)}
              />{" "}
              <SocialUrlField
                name="tiktok_url"
                label="TikTok"
                value={draft.tiktok_url}
                example="https://tiktok.com/@mi.unidad"
                pattern={SOCIAL_URL_PATTERNS.tiktok}
                error="Ingrese una URL válida de TikTok que comience con https://, por ejemplo: https://tiktok.com/@mi.unidad"
                onChange={(value) => change("tiktok_url", value)}
              />{" "}
              <Field
                label="Logotipo"
                required
                hint="Formatos permitidos: PNG, JPG, JPEG y WebP."
              >
                <input
                  className="input registration-file"
                  name="logo"
                  type="file"
                  required
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => setLogo(e.target.files?.[0] ?? null)}
                />
              </Field>{" "}
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
            <Field label="Sectores Productivos" required>
              {sectors.isLoading ? (
                <Loading label="Cargando sectores…" />
              ) : sectors.error ? (
                <ErrorBox message={message(sectors.error)} />
              ) : (
                <div className="registration-sectors">
                  {sectors.data?.map((item) => (
                    <label key={item.id}>
                      <input
                        name="sectores"
                        type="checkbox"
                        checked={sectorIds.includes(item.id)}
                        onChange={() =>
                          setSectorIds((ids) =>
                            ids.includes(item.id)
                              ? ids.filter((id) => id !== item.id)
                              : [...ids, item.id],
                          )
                        }
                      />
                      <span>{item.nombre}</span>
                    </label>
                  ))}
                </div>
              )}
            </Field>{" "}
            {otherSelected && (
              <Field label="Detalle de Otros" required>
                <input
                  className="input"
                  name="detalle_otro"
                  required
                  placeholder="Describa su actividad productiva"
                  value={otherDetail}
                  onChange={(e) => setOtherDetail(e.target.value)}
                />
              </Field>
            )}{" "}
            <div className="registration-review-field">
              <Field label="Reseña comercial" required>
                <textarea
                  className="input"
                  name="resena_comercial"
                  required
                  rows={5}
                  placeholder="Cuéntenos qué produce, cómo trabaja y qué distingue a su unidad"
                  value={draft.resena_comercial}
                  onChange={(e) => change("resena_comercial", e.target.value)}
                />
              </Field>
            </div>{" "}
          </section>{" "}
          <section className="registration-section">
            <div className="registration-section-heading">
              <span>05</span>
              <div>
                <h2>Productos iniciales</h2>
                <p>
                  Registre obligatoriamente tres productos para revisión. Cada
                  uno debe incluir nombre, imagen, reseña y precio.
                </p>
              </div>
            </div>
            <div className="registration-products">
              {products.map((product, index) => (
                <article key={index} className="registration-product-card">
                  <h3>Producto {index + 1}</h3>
                  <div className="registration-product-grid">
                    <Field label="Nombre del producto" required>
                      <input
                        className="input"
                        name={`productos.${index}.nombre_comercial`}
                        required
                        value={product.nombre_comercial}
                        onChange={(e) =>
                          changeProduct(
                            index,
                            "nombre_comercial",
                            e.target.value,
                          )
                        }
                      />
                    </Field>
                    <Field label="Precio" required>
                      <input
                        className="input"
                        name={`productos.${index}.precio_referencia`}
                        required
                        type="number"
                        min="0"
                        step="0.01"
                        value={product.precio_referencia}
                        onChange={(e) =>
                          changeProduct(
                            index,
                            "precio_referencia",
                            e.target.value,
                          )
                        }
                      />
                    </Field>
                    <div className="registration-product-full">
                      <Field label="Reseña o descripción" required>
                        <textarea
                          className="input"
                          name={`productos.${index}.descripcion_tecnica`}
                          required
                          rows={4}
                          value={product.descripcion_tecnica}
                          onChange={(e) =>
                            changeProduct(
                              index,
                              "descripcion_tecnica",
                              e.target.value,
                            )
                          }
                        />
                      </Field>
                    </div>
                    <div className="registration-product-full">
                      <Field label="Imagen" required>
                        <input
                          className="input registration-file"
                          name={`productos.${index}.imagen`}
                          required
                          type="file"
                          accept="image/png,image/jpeg,image/webp"
                          onChange={(e) =>
                            changeProduct(
                              index,
                              "imagen",
                              e.target.files?.[0] ?? null,
                            )
                          }
                        />
                      </Field>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>{" "}
          <footer className="registration-actions">
            <span>
              {sectorIds.length === 0
                ? "Seleccione al menos un sector productivo."
                : "Revise sus datos antes de enviar la solicitud."}
            </span>
            <button
              className="registration-submit"
              disabled={mutation.isPending}
            >
              <Send aria-hidden="true" />
              {mutation.isPending ? "Enviando…" : "Enviar solicitud"}
            </button>
          </footer>{" "}
        </form>{" "}
      </main>
    </>
  );
}
type ProductDraft = {
  nombre_comercial: string;
  descripcion_tecnica: string;
  materia_prima: string;
  dimensiones: string;
  colores_disponibles: string;
  certificaciones: string;
  presentacion_empaque: string;
  precio_referencia: string;
  capacidad_produccion_stock: string;
};
const emptyProduct: ProductDraft = {
  nombre_comercial: "",
  descripcion_tecnica: "",
  materia_prima: "",
  dimensiones: "",
  colores_disponibles: "",
  certificaciones: "",
  presentacion_empaque: "",
  precio_referencia: "",
  capacidad_produccion_stock: "",
};
export function ProductsPage({ admin = false }: { admin?: boolean }) {
  const [page, setPage] = useState(1),
    [editing, setEditing] = useState<CanonicalProduct | null>(null),
    [creating, setCreating] = useState(false),
    [draft, setDraft] = useState(emptyProduct),
    [imagesFor, setImagesFor] = useState<CanonicalProduct | null>(null);
  const qc = useQueryClient(),
    feedback = useFeedback(),
    base = admin ? "/admin/products" : "/productive-unit/products";
  const list = useQuery({
      queryKey: ["canonical-products", admin, page],
      queryFn: () =>
        api
          .get<Paged<CanonicalProduct>>(base, { params: { page } })
          .then((r) => r.data),
    }),
    data = pageData(list.data);
  const open = (p?: CanonicalProduct) => {
    setEditing(p ?? null);
    setCreating(!p);
    setDraft(
      p
        ? {
            nombre_comercial: p.nombre_comercial,
            descripcion_tecnica: p.descripcion_tecnica,
            materia_prima: p.materia_prima,
            dimensiones: p.dimensiones ?? "",
            colores_disponibles: p.colores_disponibles ?? "",
            certificaciones: p.certificaciones ?? "",
            presentacion_empaque: p.presentacion_empaque,
            precio_referencia: String(p.precio_referencia),
            capacidad_produccion_stock: p.capacidad_produccion_stock,
          }
        : emptyProduct,
    );
  };
  const save = async () => {
    try {
      const payload = {
        ...draft,
        dimensiones: clean(draft.dimensiones),
        colores_disponibles: clean(draft.colores_disponibles),
        certificaciones: clean(draft.certificaciones),
        precio_referencia: draft.precio_referencia,
      };
      if (editing)
        await api.patch(`/productive-unit/products/${editing.id}`, payload);
      else await api.post("/productive-unit/products", payload);
      await qc.invalidateQueries({ queryKey: ["canonical-products"] });
      setEditing(null);
      setCreating(false);
      feedback.success("Producto guardado", draft.nombre_comercial);
    } catch (e) {
      feedback.error("No se pudo guardar", message(e));
    }
  };
  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Oferta productiva</span>
          <h1>{admin ? "Productos registrados" : "Mis productos"}</h1>
          <p>
            Cada producto requiere exactamente tres imágenes para ser
            publicable.
          </p>
        </div>
        {!admin && (
          <button className="btn" onClick={() => open()}>
            Nuevo producto
          </button>
        )}
      </div>
      {list.isLoading ? (
        <Loading />
      ) : list.error ? (
        <ErrorBox message={message(list.error)} />
      ) : data.items.length ? (
        <>
          <div className="card-grid">
            {data.items.map((p) => (
              <article className="catalog-card" key={p.id}>
                {p.imagenes[0] && (
                  <img
                    src={assetUrl(
                      p.imagenes.find((i) => i.es_principal)?.url_imagen ??
                        p.imagenes[0].url_imagen,
                    )}
                    alt=""
                  />
                )}
                <div className="card-body">
                  <StatusBadge value={p.estado} />
                  <h2>{p.nombre_comercial}</h2>
                  <p>{p.descripcion_tecnica}</p>
                  <strong>Bs {Number(p.precio_referencia).toFixed(2)}</strong>
                  <small>
                    {p.imagenes.length}/3 imágenes ·{" "}
                    {p.publicable ? "Publicable" : "No publicable"}
                  </small>
                  <div className="card-actions">
                    {!admin && (
                      <>
                        <button className="btn-small" onClick={() => open(p)}>
                          Editar
                        </button>
                        <button
                          className="btn-small"
                          onClick={() => setImagesFor(p)}
                        >
                          Imágenes
                        </button>
                      </>
                    )}
                    <select
                      className="input compact"
                      value={p.estado}
                      onChange={async (e) => {
                        await api.patch(
                          `${admin ? "/admin/products" : "/productive-unit/products"}/${p.id}/status`,
                          { estado: e.target.value },
                        );
                        await qc.invalidateQueries({
                          queryKey: ["canonical-products"],
                        });
                      }}
                    >
                      <option>DRAFT</option>
                      <option>AVAILABLE</option>
                      <option>OUT_OF_STOCK</option>
                      <option>RETIRED</option>
                    </select>
                  </div>
                </div>
              </article>
            ))}
          </div>
          <PaginationBar pagination={data.pagination} onPageChange={setPage} />
        </>
      ) : (
        <Empty title="No hay productos" />
      )}
      {(editing || creating) && (
        <Modal
          title={editing ? "Editar producto" : "Nuevo producto"}
          onClose={() => {
            setEditing(null);
            setCreating(false);
          }}
        >
          <div className="form-grid">
            {(
              [
                ["nombre_comercial", "Nombre comercial"],
                ["materia_prima", "Materia prima"],
                ["presentacion_empaque", "Presentación o empaque"],
                ["precio_referencia", "Precio de referencia"],
                ["capacidad_produccion_stock", "Capacidad o stock"],
                ["dimensiones", "Dimensiones"],
                ["colores_disponibles", "Colores disponibles"],
                ["certificaciones", "Certificaciones"],
              ] as [keyof ProductDraft, string][]
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  className="input"
                  required={[
                    "nombre_comercial",
                    "materia_prima",
                    "presentacion_empaque",
                    "precio_referencia",
                    "capacidad_produccion_stock",
                  ].includes(key)}
                  type={key === "precio_referencia" ? "number" : "text"}
                  value={draft[key]}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, [key]: e.target.value }))
                  }
                />
              </Field>
            ))}
          </div>
          <Field label="Descripción técnica">
            <textarea
              className="input"
              required
              rows={4}
              value={draft.descripcion_tecnica}
              onChange={(e) =>
                setDraft((d) => ({ ...d, descripcion_tecnica: e.target.value }))
              }
            />
          </Field>
          <button className="btn" onClick={() => void save()}>
            Guardar
          </button>
        </Modal>
      )}
      {imagesFor && (
        <ProductImagesModal
          product={imagesFor}
          onClose={() => setImagesFor(null)}
          onChanged={() =>
            qc.invalidateQueries({ queryKey: ["canonical-products"] })
          }
        />
      )}
    </section>
  );
}
function ProductImagesModal({
  product,
  onClose,
  onChanged,
}: {
  product: CanonicalProduct;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false),
    feedback = useFeedback();
  const refresh = async () => {
    onChanged();
  };
  return (
    <Modal title={`Imágenes: ${product.nombre_comercial}`} onClose={onClose}>
      <p>Cargue exactamente tres imágenes. Defina una como portada.</p>
      <div className="image-grid">
        {product.imagenes.map((img) => (
          <article key={img.id}>
            <img
              src={assetUrl(img.url_imagen)}
              alt={img.texto_alternativo ?? "Imagen del producto"}
            />
            <StatusBadge
              value={
                img.es_principal
                  ? "PRINCIPAL"
                  : `${img.orden_visualizacion + 1}`
              }
            />
            <button
              className="btn-small"
              onClick={async () => {
                await api.patch(
                  `/productive-unit/products/${product.id}/images/${img.id}/main`,
                );
                await refresh();
                onClose();
              }}
            >
              Hacer principal
            </button>
            <ConfirmButton
              question="¿Eliminar esta imagen?"
              onConfirm={async () => {
                await api.delete(
                  `/productive-unit/products/${product.id}/images/${img.id}`,
                );
                await refresh();
                onClose();
              }}
            >
              Eliminar
            </ConfirmButton>
          </article>
        ))}
      </div>
      {product.imagenes.length < 3 && (
        <Field label="Agregar imagen">
          <input
            className="input"
            disabled={busy}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setBusy(true);
              try {
                const form = new FormData();
                form.append("file", file);
                form.append(
                  "alt_text",
                  `Imagen de ${product.nombre_comercial}`,
                );
                await api.post(
                  `/productive-unit/products/${product.id}/images`,
                  form,
                );
                await refresh();
                onClose();
              } catch (err) {
                feedback.error("No se pudo cargar", message(err));
              } finally {
                setBusy(false);
              }
            }}
          />
        </Field>
      )}
    </Modal>
  );
}
export function NotFoundPage() {
  return (
    <>
      <PublicHeader />
      <main className="container public-main">
        <Empty title="Página no encontrada" />
        <Link className="btn" to="/catalogo">
          Ir al catálogo
        </Link>
      </main>
    </>
  );
}
