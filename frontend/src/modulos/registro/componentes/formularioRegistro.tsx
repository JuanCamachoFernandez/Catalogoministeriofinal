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
export const sanearNombreRepresentante = (value: string) =>
  value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ '’-]/g, "");
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
export function CampoUrlSocial({
  name,
  label,
  value,
  example,
  pattern,
  error,
  onChange,
}: {
  name: "facebook_url" | "instagram_url" | "tiktok_url";
  label: string;
  value: string;
  example: string;
  pattern: string;
  error: string;
  onChange: (value: string) => void;
}) {
  return (
    <Campo label={label} optional>
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
