import { Link2 } from "lucide-react";
import { Campo } from "../../../compartido/componentes";

export type BorradorRegistro = {
  nombre_comercial: string;
  razon_social: string;
  nit: string;
  registro_seprec: string;
  registro_pro_bolivia: string;
  nombres_representante: string;
  apellido_paterno_representante: string;
  apellido_materno_representante: string;
  departamento: string;
  direccion_fisica: string;
  telefono_whatsapp: string;
  correo_electronico: string;
  facebook_url: string;
  instagram_url: string;
  tiktok_url: string;
  resena_comercial: string;
};
export type BorradorProductoSolicitado = {
  nombre_comercial: string;
  descripcion_tecnica: string;
  precio_referencia: string;
  imagen: File | null;
};
export const registroVacio: BorradorRegistro = {
  nombre_comercial: "",
  razon_social: "",
  nit: "",
  registro_seprec: "",
  registro_pro_bolivia: "",
  nombres_representante: "",
  apellido_paterno_representante: "",
  apellido_materno_representante: "",
  departamento: "",
  direccion_fisica: "",
  telefono_whatsapp: "",
  correo_electronico: "",
  facebook_url: "",
  instagram_url: "",
  tiktok_url: "",
  resena_comercial: "",
};
export const productoSolicitadoVacio = (): BorradorProductoSolicitado => ({
  nombre_comercial: "",
  descripcion_tecnica: "",
  precio_referencia: "",
  imagen: null,
});
export const REPRESENTATIVE_NAME_PATTERN =
  "[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '’\\-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*";
export const EMAIL_PATTERN = String.raw`[^@\s]+@[^@\s]+\.[^@\s]+`;
export const IDENTIFICADOR_REGISTRO_PATTERN = String.raw`[0-9/_-]{5,20}`;
export const PRO_BOLIVIA_PATTERN = String.raw`[0-9/_-]{5,20}[Ee]?`;
export const sanearNombreRepresentante = (value: string) =>
  value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ '’-]/g, "");
export const sanearIdentificadorRegistro = (value: string) =>
  value.replace(/[^0-9/_-]/g, "").slice(0, 20);
export const sanearRegistroProBolivia = (value: string) => {
  const upper = value.toUpperCase();
  const endsWithE = upper.endsWith("E");
  const base = (endsWithE ? upper.slice(0, -1) : upper).replace(/[^0-9/_-]/g, "");
  return `${base.slice(0, 20)}${endsWithE ? "E" : ""}`;
};
export const SOCIAL_URL_PATTERNS = {
  facebook: String.raw`https://((www|m|web)\.)?(facebook\.com|fb\.com)/.+`,
  instagram: String.raw`https://(www\.)?instagram\.com/.+`,
  tiktok: String.raw`https://(www\.)?tiktok\.com/@[^/?#]+.*`,
};
export const REGISTRATION_FIELD_LABELS: Record<string, string> = {
  nombre_comercial: "Nombre comercial",
  razon_social: "Razón social",
  nit: "NIT",
  registro_seprec: "Registro SEPREC",
  registro_pro_bolivia: "Registro PRO-BOLIVIA",
  nombres_representante: "Nombres del representante",
  apellido_paterno_representante: "Apellido paterno",
  apellido_materno_representante: "Apellido materno",
  departamento: "Departamento",
  direccion_fisica: "Dirección física",
  telefono_whatsapp: "Teléfono o WhatsApp",
  correo_electronico: "Correo electrónico",
  facebook_url: "Facebook",
  instagram_url: "Instagram",
  tiktok_url: "TikTok",
  logo: "Logotipo",
  sectores: "Sectores Productivos",
  detalle_otro: "Detalle de Otros",
  resena_comercial: "Reseña comercial",
};
export const REGISTRATION_FIELD_HELP: Record<string, string> = {
  nombre_comercial:
    "Es el nombre con el que su unidad se da a conocer. Ejemplo: 'Miel Los Andes'.",
  razon_social:
    "Es el nombre legal del negocio. Si es pequeño y no usa otro, puede poner el mismo nombre comercial.",
  nit:
    "Número tributario si ya lo tiene. Puede usar números y algunos símbolos.",
  registro_seprec:
    "Matrícula de Comercio, si la tiene. Puede usar números y algunos símbolos.",
  registro_pro_bolivia:
    "Registro de PRO-BOLIVIA, si existe. Ejemplos: 228770-E, 227630E o 227630.",
  nombres_representante:
    "Nombres de la persona responsable de la unidad. Ejemplo: 'Ana María'.",
  apellido_paterno_representante:
    "Primer apellido de la persona responsable. Ejemplo: 'Quispe'.",
  apellido_materno_representante:
    "Segundo apellido de la persona responsable. Ejemplo: 'Mamani'.",
  departamento:
    "Seleccione el departamento donde trabaja o produce la unidad.",
  direccion_fisica:
    "Dirección de la planta, taller o lugar principal de trabajo. Ejemplo: zona, calle y número.",
  telefono_whatsapp:
    "Celular boliviano de contacto. Debe tener 8 dígitos, sin guiones.",
  correo_electronico:
    "Correo donde recibirá avisos y credenciales si la solicitud es aprobada.",
  facebook_url:
    "Pegue el enlace completo del perfil o página. Ejemplo: https://facebook.com/miunidad",
  instagram_url:
    "Pegue el enlace completo del perfil. Ejemplo: https://instagram.com/miunidad",
  tiktok_url:
    "Pegue el enlace completo del perfil. Ejemplo: https://tiktok.com/@miunidad",
  logo:
    "Suba el logotipo o una imagen representativa de la unidad en PNG, JPG o WebP.",
  sectores:
    "Elija uno o varios sectores que describan lo que produce su unidad.",
  detalle_otro:
    "Si eligió 'Otros', describa brevemente a qué se dedica.",
  resena_comercial:
    "Escriba una descripción breve de lo que produce y qué hace especial a su unidad.",
  "productos.nombre_comercial":
    "Nombre con el que presentará el producto. Ejemplo: 'Mermelada de tumbo 454gr'.",
  "productos.precio_referencia":
    "Precio aproximado de venta en bolivianos. Ejemplo: 25 o 25.50.",
  "productos.descripcion_tecnica":
    "Describa el producto de forma breve: qué es, de qué está hecho, colores o cómo se presenta.",
  "productos.imagen":
    "Suba una foto clara del producto en PNG, JPG o WebP.",
};
export function CampoUrlSocial({
  name,
  label,
  value,
  example,
  pattern,
  error,
  hint,
  onChange,
}: {
  name: "facebook_url" | "instagram_url" | "tiktok_url";
  label: string;
  value: string;
  example: string;
  pattern: string;
  error: string;
  hint?: string;
  onChange: (value: string) => void;
}) {
  return (
    <Campo label={label} optional hint={hint} hintAsHelp={Boolean(hint)}>
      {" "}
      <div className="social-url-input">
        {" "}
        <Link2 aria-hidden="true" />{" "}
        <input
          className="input"
          name={name}
          type="url"
          inputMode="url"
          maxLength={500}
          pattern={pattern}
          placeholder={example}
          title={error}
          value={value}
          onInvalid={(event) => event.currentTarget.setCustomValidity(error)}
          onInput={(event) => event.currentTarget.setCustomValidity("")}
          onBlur={(event) => onChange(event.currentTarget.value.trim())}
          onChange={(event) => onChange(event.target.value)}
        />{" "}
      </div>{" "}
    </Campo>
  );
}
