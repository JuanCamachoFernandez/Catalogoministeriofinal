import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, KeyRound, Link2, Mail, Send } from "lucide-react";
import { Link } from "react-router-dom";
import { api, apiError, assetUrl, emptyPagination, type CanonicalFair, type CanonicalProduct, type FairParticipation, type Paged, type ProductiveSector, type ProductiveSectorLink, type ProductiveUnit, type RegistrationRequest } from "./api";
import { BOLIVIA_DEPARTMENTS } from "./boliviaLocations";
import { ConfirmButton, Empty, ErrorBox, FeedbackProvider, Field, Loading, Modal, PaginationBar, SearchField, StatusBadge, UploadProgress, useFeedback } from "./ui";
import { PublicHeader } from "./Layouts";

const pageData = <T,>(value?: Paged<T>) => value ?? { items: [], pagination: emptyPagination };
const message = (error: unknown) => apiError(error, "No se pudo completar la operación.");
const clean = (value: string) => value.trim() || null;

export function AdminHomePage() {
  return <section><div className="page-heading"><div><span className="eyebrow">Administración</span><h1>Gestión institucional</h1><p>Revise solicitudes, Unidades Productivas, productos y ferias desde el contrato canónico.</p></div></div><div className="stat-grid"><Link className="stat-card" to="/admin/solicitudes"><strong>Solicitudes</strong><span>Revisión y aprobación</span></Link><Link className="stat-card" to="/admin/unidades-productivas"><strong>Unidades Productivas</strong><span>Gestión institucional</span></Link><Link className="stat-card" to="/admin/ferias"><strong>Ferias</strong><span>Participaciones completas</span></Link></div></section>;
}

type RegistrationDraft = {
  nombre_comercial: string; razon_social: string; nit: string; registro_seprec: string; registro_pro_bolivia: string;
  nombres_representante: string; apellido_paterno_representante: string; apellido_materno_representante: string;
  departamento: string; direccion_fisica: string; telefono_whatsapp: string; correo_electronico: string;
  facebook_url: string; instagram_url: string; tiktok_url: string; resena_comercial: string;
};
const emptyRegistration: RegistrationDraft = { nombre_comercial: "", razon_social: "", nit: "", registro_seprec: "", registro_pro_bolivia: "", nombres_representante: "", apellido_paterno_representante: "", apellido_materno_representante: "", departamento: "", direccion_fisica: "", telefono_whatsapp: "", correo_electronico: "", facebook_url: "", instagram_url: "", tiktok_url: "", resena_comercial: "" };
const REPRESENTATIVE_NAME_PATTERN = "[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '’\\-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*";
const EMAIL_PATTERN = String.raw`[^@\s]+@[^@\s]+\.[^@\s]+`;
const sanitizeRepresentativeName = (value: string) => value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ '’-]/g, "");
const SOCIAL_URL_PATTERNS = {
  facebook: String.raw`https://((www|m|web)\.)?(facebook\.com|fb\.com)/.+`,
  instagram: String.raw`https://(www\.)?instagram\.com/.+`,
  tiktok: String.raw`https://(www\.)?tiktok\.com/@[^/?#]+.*`,
};
const REGISTRATION_FIELD_LABELS: Record<string, string> = {
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

function SocialUrlField({ name, label, value, example, pattern, error, onChange }: {
  name: "facebook_url" | "instagram_url" | "tiktok_url";
  label: string;
  value: string;
  example: string;
  pattern: string;
  error: string;
  onChange: (value: string) => void;
}) {
  return <Field label={label} optional>
    <div className="social-url-input">
      <Link2 aria-hidden="true"/>
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
        onInvalid={event=>event.currentTarget.setCustomValidity(error)}
        onInput={event=>event.currentTarget.setCustomValidity("")}
        onBlur={event=>onChange(event.currentTarget.value.trim())}
        onChange={event=>onChange(event.target.value)}
      />
    </div>
  </Field>;
}

export function RegistrationPage() {
  return <FeedbackProvider><RegistrationPageContent/></FeedbackProvider>;
}

function RegistrationPageContent() {
  const feedback = useFeedback();
  const formRef = useRef<HTMLFormElement>(null);
  const [draft, setDraft] = useState(emptyRegistration);
  const [sectorIds, setSectorIds] = useState<string[]>([]);
  const [otherDetail, setOtherDetail] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [created, setCreated] = useState<RegistrationRequest | null>(null);
  const sectors = useQuery({ queryKey: ["productive-sectors", "active"], queryFn: () => api.get<Paged<ProductiveSector>>("/productive-sectors", { params: { per_page: 100 } }).then(r => r.data.items) });
  const focusInvalidControl = (control: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, popupMessage: string) => {
    formRef.current?.querySelectorAll<HTMLElement>('[aria-invalid="true"]').forEach(item=>item.removeAttribute("aria-invalid"));
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
    const response = (error as { response?: { data?: { details?: Record<string, unknown>; error?: string } } })?.response;
    const details = response?.data?.details;
    const detailedField = details ? Object.keys(details)[0] : "";
    if (detailedField) return detailedField;
    const errorMessage = (response?.data?.error ?? "").toLowerCase();
    if (errorMessage.includes("correo")) return "correo_electronico";
    if (errorMessage.includes("nit")) return "nit";
    if (errorMessage.includes("imagen") || errorMessage.includes("archivo") || errorMessage.includes("logotipo")) return "logo";
    return "";
  };
  const mutation = useMutation({ mutationFn: async () => {
    let logo_url: string | null = null;
    if (logo) { const form = new FormData(); form.append("file", logo); logo_url = (await api.post<{url:string}>("/registration-requests/logo", form)).data.url; }
    const selected = sectorIds.map(id => { const sector = sectors.data?.find(item => item.id === id); return { productive_sector_id: id, detalle_otro: sector?.es_otro ? clean(otherDetail) : null }; });
    return (await api.post<RegistrationRequest>("/registration-requests", { ...draft, nit: clean(draft.nit), registro_seprec: clean(draft.registro_seprec), registro_pro_bolivia: clean(draft.registro_pro_bolivia), facebook_url: clean(draft.facebook_url), instagram_url: clean(draft.instagram_url), tiktok_url: clean(draft.tiktok_url), logo_url, sectores: selected })).data;
  }, onSuccess: setCreated, onError: error => {
    const fieldName = fieldFromServerError(error);
    const control = fieldName ? formRef.current?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`[name="${fieldName}"]`) : null;
    if (control) {
      focusInvalidControl(control, message(error));
      return;
    }
    feedback.error("No se pudo enviar la solicitud", message(error));
  } });
  if (created) return <><PublicHeader/><main className="container public-main registration-page"><section className="registration-success">
    <div className="registration-success-icon"><CheckCircle2 aria-hidden="true"/></div>
    <span className="registration-success-eyebrow">Solicitud enviada correctamente</span>
    <h1>Recibimos su solicitud</h1>
    <p>La administración revisará la información de su Unidad Productiva. Por ahora no necesita realizar otro registro.</p>
    <div className="registration-next-steps">
      <h2>¿Qué sucederá ahora?</h2>
      <div>
        <article><span><Clock3 aria-hidden="true"/></span><div><strong>1. Revisión de la solicitud</strong><p>La administración verificará los datos y documentos enviados.</p></div></article>
        <article><span><Mail aria-hidden="true"/></span><div><strong>2. Aviso por correo electrónico</strong><p>Le comunicaremos si la solicitud fue aprobada o rechazada al correo <b>{created.correo_electronico}</b>.</p></div></article>
        <article><span><KeyRound aria-hidden="true"/></span><div><strong>3. Credenciales de acceso</strong><p>Si es aprobada, el correo incluirá su <b>nombre de usuario</b> y una <b>contraseña temporal</b>. Deberá cambiarla cuando ingrese por primera vez.</p></div></article>
      </div>
    </div>
    <div className="registration-email-note"><Mail aria-hidden="true"/><span>Revise también las carpetas de correo no deseado o spam.</span></div>
    <p className="registration-sent-at">Enviada el {new Date(created.fecha_solicitud).toLocaleString("es-BO")}</p>
    <Link className="registration-back-link" to="/catalogo">Volver a las ferias</Link>
  </section></main></>;
  const change = (key: keyof RegistrationDraft, value: string) => setDraft(current => ({ ...current, [key]: value }));
  const otherSelected = sectors.data?.some(item => item.es_otro && sectorIds.includes(item.id));
  const submitRegistration = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const controls = Array.from(event.currentTarget.elements).filter(
      (element): element is HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement =>
        element instanceof HTMLInputElement || element instanceof HTMLSelectElement || element instanceof HTMLTextAreaElement,
    );
    const invalidControl = controls.find(control=>!control.validity.valid);
    if (invalidControl) {
      const label = REGISTRATION_FIELD_LABELS[invalidControl.name] ?? "indicado";
      const popupMessage = invalidControl.validity.valueMissing
        ? `Complete el campo “${label}”. Al cerrar este mensaje quedará marcado para que pueda corregirlo.`
        : `Revise el formato del campo “${label}”. Al cerrar este mensaje quedará marcado para que pueda corregirlo.`;
      focusInvalidControl(invalidControl, popupMessage);
      return;
    }
    if (sectorIds.length === 0) {
      const firstSector = event.currentTarget.querySelector<HTMLInputElement>('input[name="sectores"]');
      if (firstSector) focusInvalidControl(firstSector, "Seleccione al menos un Sector Productivo. Al cerrar este mensaje podrá elegirlo.");
      return;
    }
    mutation.mutate();
  };
  return <><PublicHeader/><main className="container public-main registration-page">
    <header className="registration-intro"><h1>Solicitud de Unidad Productiva</h1><p>Complete la información para solicitar su incorporación. Cuando la administración apruebe la solicitud, recibirá las credenciales de acceso.</p><small><b className="field-required" aria-hidden="true">*</b> Los campos marcados con asterisco son obligatorios.</small></header>
    <form ref={formRef} className="registration-form" noValidate onSubmit={submitRegistration} onInput={event=>(event.target as HTMLElement).removeAttribute("aria-invalid")}>
      <section className="registration-section"><div className="registration-section-heading"><span>01</span><div><h2>Datos de la unidad</h2><p>Información comercial y registros institucionales.</p></div></div><div className="registration-grid">
        <Field label="Nombre comercial" required><input className="input" name="nombre_comercial" required autoComplete="organization" placeholder="Nombre con el que se presenta al público" value={draft.nombre_comercial} onChange={e=>change("nombre_comercial",e.target.value)}/></Field>
        <Field label="Razón social" required><input className="input" name="razon_social" required placeholder="Nombre legal de la organización" value={draft.razon_social} onChange={e=>change("razon_social",e.target.value)}/></Field>
        <Field label="NIT" optional><input className="input" name="nit" inputMode="numeric" pattern="[0-9]{5,12}" maxLength={12} placeholder="Número de identificación tributaria" value={draft.nit} onInvalid={e=>e.currentTarget.setCustomValidity("Solo números, de 5 a 12 dígitos.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("nit",e.target.value.replace(/\D/g, "").slice(0, 12))}/></Field>
        <Field label="Registro SEPREC" optional><input className="input" name="registro_seprec" inputMode="numeric" pattern="[0-9]{5,12}" maxLength={12} placeholder="Número de Matrícula de Comercio" value={draft.registro_seprec} onInvalid={e=>e.currentTarget.setCustomValidity("Solo números, de 5 a 12 dígitos.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("registro_seprec",e.target.value.replace(/\D/g, "").slice(0, 12))}/></Field>
        <Field label="Registro PRO-BOLIVIA" optional><input className="input" name="registro_pro_bolivia" inputMode="numeric" pattern="[0-9]{5,12}" maxLength={12} placeholder="Número de registro PRO-BOLIVIA" value={draft.registro_pro_bolivia} onInvalid={e=>e.currentTarget.setCustomValidity("Solo números, de 5 a 12 dígitos.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("registro_pro_bolivia",e.target.value.replace(/\D/g, "").slice(0, 12))}/></Field>
      </div></section>
      <section className="registration-section"><div className="registration-section-heading"><span>02</span><div><h2>Contacto y ubicación</h2><p>Datos de la persona responsable y medios de contacto.</p></div></div><div className="registration-grid">
        <Field label="Nombres del representante" required><input className="input" name="nombres_representante" required autoComplete="given-name" maxLength={100} pattern={REPRESENTATIVE_NAME_PATTERN} placeholder="Nombres" value={draft.nombres_representante} onInvalid={e=>e.currentTarget.setCustomValidity("Ingrese únicamente letras, espacios, apóstrofes o guiones.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("nombres_representante",sanitizeRepresentativeName(e.target.value))}/></Field>
        <Field label="Apellido paterno" required><input className="input" name="apellido_paterno_representante" required autoComplete="family-name" maxLength={100} pattern={REPRESENTATIVE_NAME_PATTERN} placeholder="Apellido paterno" value={draft.apellido_paterno_representante} onInvalid={e=>e.currentTarget.setCustomValidity("Ingrese únicamente letras, espacios, apóstrofes o guiones.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("apellido_paterno_representante",sanitizeRepresentativeName(e.target.value))}/></Field>
        <Field label="Apellido materno" required><input className="input" name="apellido_materno_representante" required maxLength={100} pattern={REPRESENTATIVE_NAME_PATTERN} placeholder="Apellido materno" value={draft.apellido_materno_representante} onInvalid={e=>e.currentTarget.setCustomValidity("Ingrese únicamente letras, espacios, apóstrofes o guiones.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("apellido_materno_representante",sanitizeRepresentativeName(e.target.value))}/></Field>
        <Field label="Departamento" required><select className="input" name="departamento" required value={draft.departamento} onChange={e=>change("departamento",e.target.value)}><option value="">Seleccione un departamento</option>{BOLIVIA_DEPARTMENTS.map(item=><option key={item}>{item}</option>)}</select></Field>
        <Field label="Dirección física de la Planta de Producción o Taller" required><input className="input" name="direccion_fisica" required autoComplete="street-address" placeholder="Zona, avenida o calle" value={draft.direccion_fisica} onChange={e=>change("direccion_fisica",e.target.value)}/></Field>
        <Field label="Teléfono o WhatsApp" required><input className="input" name="telefono_whatsapp" type="tel" required autoComplete="tel" inputMode="numeric" pattern="[67][0-9]{7}" maxLength={8} placeholder="Ej. 70000000" value={draft.telefono_whatsapp} onInvalid={e=>e.currentTarget.setCustomValidity("Ingrese 8 dígitos de un celular boliviano que comience con 6 o 7.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("telefono_whatsapp",e.target.value.replace(/\D/g, "").slice(0, 8))}/></Field>
        <Field label="Correo electrónico" required><input className="input" name="correo_electronico" type="email" required autoComplete="email" inputMode="email" maxLength={255} pattern={EMAIL_PATTERN} placeholder="correo@dominio.com" value={draft.correo_electronico} onInvalid={e=>e.currentTarget.setCustomValidity("Ingrese un correo electrónico válido, por ejemplo: nombre@dominio.com.")} onInput={e=>e.currentTarget.setCustomValidity("")} onChange={e=>change("correo_electronico",e.target.value)}/></Field>
      </div></section>
      <section className="registration-section"><div className="registration-section-heading"><span>03</span><div><h2>Presencia digital</h2><p>Redes sociales y logotipo de la unidad.</p></div></div>
        <div className="social-url-guide"><Link2 aria-hidden="true"/><div><strong>Ingrese el enlace completo de cada perfil</strong><span>Abra su perfil en la red social, copie el enlace y péguelo aquí. Debe comenzar con <b>https://</b>.</span></div></div>
        <div className="registration-grid">
        <SocialUrlField name="facebook_url" label="Facebook" value={draft.facebook_url} example="https://facebook.com/mi.unidad" pattern={SOCIAL_URL_PATTERNS.facebook} error="Ingrese una URL válida de Facebook que comience con https://, por ejemplo: https://facebook.com/mi.unidad" onChange={value=>change("facebook_url",value)}/>
        <SocialUrlField name="instagram_url" label="Instagram" value={draft.instagram_url} example="https://instagram.com/mi.unidad" pattern={SOCIAL_URL_PATTERNS.instagram} error="Ingrese una URL válida de Instagram que comience con https://, por ejemplo: https://instagram.com/mi.unidad" onChange={value=>change("instagram_url",value)}/>
        <SocialUrlField name="tiktok_url" label="TikTok" value={draft.tiktok_url} example="https://tiktok.com/@mi.unidad" pattern={SOCIAL_URL_PATTERNS.tiktok} error="Ingrese una URL válida de TikTok que comience con https://, por ejemplo: https://tiktok.com/@mi.unidad" onChange={value=>change("tiktok_url",value)}/>
        <Field label="Logotipo" optional hint="Formatos permitidos: PNG, JPG, JPEG y WebP."><input className="input registration-file" name="logo" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setLogo(e.target.files?.[0]??null)}/></Field>
      </div></section>
      <section className="registration-section"><div className="registration-section-heading"><span>04</span><div><h2>Actividad productiva</h2><p>Seleccione al menos un sector y describa brevemente su oferta.</p></div></div>
        <Field label="Sectores Productivos" required>{sectors.isLoading?<Loading label="Cargando sectores…"/>:sectors.error?<ErrorBox message={message(sectors.error)}/>:<div className="registration-sectors">{sectors.data?.map(item=><label key={item.id}><input name="sectores" type="checkbox" checked={sectorIds.includes(item.id)} onChange={()=>setSectorIds(ids=>ids.includes(item.id)?ids.filter(id=>id!==item.id):[...ids,item.id])}/><span>{item.nombre}</span></label>)}</div>}</Field>
        {otherSelected&&<Field label="Detalle de Otros" required><input className="input" name="detalle_otro" required placeholder="Describa su actividad productiva" value={otherDetail} onChange={e=>setOtherDetail(e.target.value)}/></Field>}
        <div className="registration-review-field"><Field label="Reseña comercial" required><textarea className="input" name="resena_comercial" required rows={5} placeholder="Cuéntenos qué produce, cómo trabaja y qué distingue a su unidad" value={draft.resena_comercial} onChange={e=>change("resena_comercial",e.target.value)}/></Field></div>
      </section>
      <footer className="registration-actions"><span>{sectorIds.length===0?"Seleccione al menos un sector productivo.":"Revise sus datos antes de enviar la solicitud."}</span><button className="registration-submit" disabled={mutation.isPending}><Send aria-hidden="true"/>{mutation.isPending?"Enviando…":"Enviar solicitud"}</button></footer>
    </form>
  </main></>;
}

export function RegistrationRequestsPage() {
  const [page,setPage]=useState(1),[q,setQ]=useState(""),[estado,setEstado]=useState("");
  const [selected,setSelected]=useState<RegistrationRequest|null>(null),[rejectReason,setRejectReason]=useState("");
  const qc=useQueryClient(), feedback=useFeedback();
  const list=useQuery({queryKey:["registration-requests",q,estado,page],queryFn:()=>api.get<Paged<RegistrationRequest>>("/admin/registration-requests",{params:{q:q||undefined,estado:estado||undefined,page}}).then(r=>r.data)});
  const act=async(path:string,payload?:object)=>{try{await api.post(path,payload);await qc.invalidateQueries({queryKey:["registration-requests"]});setSelected(null);feedback.success("Operación completada","La solicitud fue actualizada.");}catch(error){feedback.error("No se pudo actualizar",message(error));}};
  const data=pageData(list.data);
  return <section><div className="page-heading"><div><span className="eyebrow">Incorporación</span><h1>Solicitudes de registro</h1></div></div><div className="toolbar"><SearchField value={q} onChange={v=>{setQ(v);setPage(1)}} placeholder="Buscar nombre, correo o NIT…"/><select className="input" value={estado} onChange={e=>{setEstado(e.target.value);setPage(1)}}><option value="">Todos los estados</option><option>PENDING</option><option>APPROVED</option><option>REJECTED</option></select></div>{list.isLoading?<Loading/>:list.error?<ErrorBox message={message(list.error)}/>:data.items.length?<><div className="table-wrap"><table><thead><tr><th>Unidad Productiva</th><th>Contacto</th><th>Departamento</th><th>Estado</th><th></th></tr></thead><tbody>{data.items.map(item=><tr key={item.id}><td><strong>{item.nombre_comercial}</strong><small>{item.razon_social}</small></td><td>{item.correo_electronico}</td><td>{item.departamento}</td><td><StatusBadge value={item.estado}/></td><td><button className="btn-small" onClick={()=>setSelected(item)}>Revisar</button></td></tr>)}</tbody></table></div><PaginationBar pagination={data.pagination} onPageChange={setPage}/></>:<Empty title="No hay solicitudes"/>}
  {selected&&<Modal title={`Solicitud: ${selected.nombre_comercial}`} onClose={()=>setSelected(null)}><div className="detail-grid"><p><strong>Representante</strong><br/>{selected.nombre_representante}</p><p><strong>Contacto</strong><br/>{selected.telefono_whatsapp}<br/>{selected.correo_electronico}</p><p><strong>Dirección</strong><br/>{selected.departamento}, {selected.direccion_fisica}</p><p><strong>Sectores</strong><br/>{selected.sectores.map(s=>s.nombre+(s.detalle_otro?`: ${s.detalle_otro}`:"")).join(", ")}</p></div><p>{selected.resena_comercial}</p>{selected.logo_url&&<img className="detail-logo" src={assetUrl(selected.logo_url)} alt={`Logo de ${selected.nombre_comercial}`}/>} {selected.estado==="PENDING"&&<div className="modal-actions"><button className="btn" onClick={()=>void act(`/admin/registration-requests/${selected.id}/approve`,{observaciones:null})}>Aprobar</button><Field label="Motivo de rechazo"><textarea className="input" value={rejectReason} onChange={e=>setRejectReason(e.target.value)}/></Field><button className="btn-danger" disabled={!rejectReason.trim()} onClick={()=>void act(`/admin/registration-requests/${selected.id}/reject`,{motivo:rejectReason})}>Rechazar</button></div>}{selected.estado==="APPROVED"&&<button className="btn-secondary" onClick={()=>void act(`/admin/registration-requests/${selected.id}/resend-credentials`)}>Reenviar credenciales</button>}</Modal>}</section>;
}

export function ProductiveUnitsPage() {
  const [page,setPage]=useState(1),[q,setQ]=useState(""),[estado,setEstado]=useState(""),[selected,setSelected]=useState<ProductiveUnit|null>(null);
  const qc=useQueryClient(),feedback=useFeedback();
  const list=useQuery({queryKey:["productive-units",q,estado,page],queryFn:()=>api.get<Paged<ProductiveUnit>>("/admin/productive-units",{params:{q:q||undefined,estado:estado||undefined,page,include_deleted:true}}).then(r=>r.data)});
  const changeStatus=async(item:ProductiveUnit,status:string)=>{try{await api.patch(`/admin/productive-units/${item.id}/status`,{estado:status});await qc.invalidateQueries({queryKey:["productive-units"]});feedback.success("Estado actualizado",item.nombre_comercial);}catch(e){feedback.error("No se pudo cambiar el estado",message(e));}};
  const data=pageData(list.data);
  return <section><div className="page-heading"><div><span className="eyebrow">Directorio</span><h1>Unidades Productivas</h1><p>Las nuevas unidades se crean exclusivamente al aprobar solicitudes.</p></div></div><div className="toolbar"><SearchField value={q} onChange={v=>{setQ(v);setPage(1)}} placeholder="Buscar Unidad Productiva…"/><select className="input" value={estado} onChange={e=>setEstado(e.target.value)}><option value="">Todos</option><option>ACTIVE</option><option>INACTIVE</option><option>SUSPENDED</option></select></div>{list.isLoading?<Loading/>:list.error?<ErrorBox message={message(list.error)}/>:data.items.length?<><div className="card-grid">{data.items.map(item=><article className="catalog-card" key={item.id}>{item.logo_url&&<img src={assetUrl(item.logo_url)} alt=""/>}<div className="card-body"><StatusBadge value={item.estado}/><h2>{item.nombre_comercial}</h2><p>{item.nombre_representante}</p><small>{item.departamento} · {item.telefono_whatsapp}</small><div className="card-actions"><button className="btn-small" onClick={()=>setSelected(item)}>Detalle</button><select className="input compact" value={item.estado} onChange={e=>void changeStatus(item,e.target.value)}><option>ACTIVE</option><option>INACTIVE</option><option>SUSPENDED</option></select></div></div></article>)}</div><PaginationBar pagination={data.pagination} onPageChange={setPage}/></>:<Empty title="No hay Unidades Productivas"/>}{selected&&<Modal title={selected.nombre_comercial} onClose={()=>setSelected(null)}><p><strong>Razón social:</strong> {selected.razon_social}</p><p><strong>Representante:</strong> {selected.nombre_representante}</p><p><strong>Correo:</strong> {selected.correo_electronico}</p><p><strong>Dirección:</strong> {selected.direccion_fisica}</p><p><strong>Sectores:</strong> {selected.sectores.map(s=>s.nombre).join(", ")||"Sin sectores"}</p><p>{selected.resena_comercial}</p><div className="modal-actions"><ConfirmButton question="¿Eliminar lógicamente esta Unidad Productiva?" onConfirm={async()=>{await api.delete(`/admin/productive-units/${selected.id}`);await qc.invalidateQueries({queryKey:["productive-units"]});setSelected(null)}}>Eliminar</ConfirmButton><button className="btn-secondary" onClick={async()=>{await api.post(`/admin/productive-units/${selected.id}/restore`);await qc.invalidateQueries({queryKey:["productive-units"]});setSelected(null)}}>Restaurar</button></div></Modal>}</section>;
}

export function ProductiveSectorsPage() {
  const [editing,setEditing]=useState<ProductiveSector|null>(null),[creating,setCreating]=useState(false),[name,setName]=useState(""),[description,setDescription]=useState(""),[other,setOther]=useState(false);
  const qc=useQueryClient(),feedback=useFeedback();
  const list=useQuery({queryKey:["productive-sectors","admin"],queryFn:()=>api.get<Paged<ProductiveSector>>("/admin/productive-sectors",{params:{per_page:100}}).then(r=>r.data)});
  const open=(item?:ProductiveSector)=>{setEditing(item??null);setCreating(!item);setName(item?.nombre??"");setDescription(item?.descripcion??"");setOther(item?.es_otro??false)};
  const save=async()=>{try{if(editing)await api.patch(`/admin/productive-sectors/${editing.id}`,{nombre:name,descripcion:clean(description),es_otro:other});else await api.post("/admin/productive-sectors",{nombre:name,descripcion:clean(description),es_otro:other});await qc.invalidateQueries({queryKey:["productive-sectors"]});setEditing(null);setCreating(false);feedback.success("Sector guardado",name)}catch(e){feedback.error("No se pudo guardar",message(e))}};
  const items=list.data?.items??[];
  return <section><div className="page-heading"><div><span className="eyebrow">Clasificación institucional</span><h1>Sectores Productivos</h1></div><button className="btn" onClick={()=>open()}>Nuevo sector</button></div>{list.isLoading?<Loading/>:<div className="table-wrap"><table><thead><tr><th>Sector</th><th>Descripción</th><th>Tipo</th><th>Estado</th><th></th></tr></thead><tbody>{items.map(item=><tr key={item.id}><td>{item.nombre}</td><td>{item.descripcion}</td><td>{item.es_otro?"Otros":"Regular"}</td><td><StatusBadge value={item.estado}/></td><td><button className="btn-small" onClick={()=>open(item)}>Editar</button> <button className="btn-small" onClick={async()=>{await api.patch(`/admin/productive-sectors/${item.id}/status`,{estado:item.estado==="ACTIVE"?"INACTIVE":"ACTIVE"});await qc.invalidateQueries({queryKey:["productive-sectors"]})}}>{item.estado==="ACTIVE"?"Inactivar":"Activar"}</button></td></tr>)}</tbody></table></div>}{(editing||creating)&&<Modal title={editing?"Editar sector":"Nuevo sector"} onClose={()=>{setEditing(null);setCreating(false)}}><Field label="Nombre"><input className="input" required value={name} onChange={e=>setName(e.target.value)}/></Field><Field label="Descripción"><textarea className="input" value={description} onChange={e=>setDescription(e.target.value)}/></Field><label><input type="checkbox" checked={other} onChange={e=>setOther(e.target.checked)}/> Es el sector “Otros”</label><div className="modal-actions"><button className="btn" disabled={!name.trim()} onClick={()=>void save()}>Guardar</button></div></Modal>}</section>;
}

type ProductDraft={nombre_comercial:string;descripcion_tecnica:string;materia_prima:string;dimensiones:string;colores_disponibles:string;certificaciones:string;presentacion_empaque:string;precio_referencia:string;capacidad_produccion_stock:string};
const emptyProduct:ProductDraft={nombre_comercial:"",descripcion_tecnica:"",materia_prima:"",dimensiones:"",colores_disponibles:"",certificaciones:"",presentacion_empaque:"",precio_referencia:"",capacidad_produccion_stock:""};

export function ProductsPage({admin=false}:{admin?:boolean}) {
  const [page,setPage]=useState(1),[editing,setEditing]=useState<CanonicalProduct|null>(null),[creating,setCreating]=useState(false),[draft,setDraft]=useState(emptyProduct),[imagesFor,setImagesFor]=useState<CanonicalProduct|null>(null);
  const qc=useQueryClient(),feedback=useFeedback(),base=admin?"/admin/products":"/productive-unit/products";
  const list=useQuery({queryKey:["canonical-products",admin,page],queryFn:()=>api.get<Paged<CanonicalProduct>>(base,{params:{page}}).then(r=>r.data)}),data=pageData(list.data);
  const open=(p?:CanonicalProduct)=>{setEditing(p??null);setCreating(!p);setDraft(p?{nombre_comercial:p.nombre_comercial,descripcion_tecnica:p.descripcion_tecnica,materia_prima:p.materia_prima,dimensiones:p.dimensiones??"",colores_disponibles:p.colores_disponibles??"",certificaciones:p.certificaciones??"",presentacion_empaque:p.presentacion_empaque,precio_referencia:String(p.precio_referencia),capacidad_produccion_stock:p.capacidad_produccion_stock}:emptyProduct)};
  const save=async()=>{try{const payload={...draft,dimensiones:clean(draft.dimensiones),colores_disponibles:clean(draft.colores_disponibles),certificaciones:clean(draft.certificaciones),precio_referencia:draft.precio_referencia};if(editing)await api.patch(`/productive-unit/products/${editing.id}`,payload);else await api.post("/productive-unit/products",payload);await qc.invalidateQueries({queryKey:["canonical-products"]});setEditing(null);setCreating(false);feedback.success("Producto guardado",draft.nombre_comercial)}catch(e){feedback.error("No se pudo guardar",message(e))}};
  return <section><div className="page-heading"><div><span className="eyebrow">Oferta productiva</span><h1>{admin?"Productos registrados":"Mis productos"}</h1><p>Cada producto requiere exactamente tres imágenes para ser publicable.</p></div>{!admin&&<button className="btn" onClick={()=>open()}>Nuevo producto</button>}</div>{list.isLoading?<Loading/>:list.error?<ErrorBox message={message(list.error)}/>:data.items.length?<><div className="card-grid">{data.items.map(p=><article className="catalog-card" key={p.id}>{p.imagenes[0]&&<img src={assetUrl(p.imagenes.find(i=>i.es_principal)?.url_imagen??p.imagenes[0].url_imagen)} alt=""/>}<div className="card-body"><StatusBadge value={p.estado}/><h2>{p.nombre_comercial}</h2><p>{p.descripcion_tecnica}</p><strong>Bs {Number(p.precio_referencia).toFixed(2)}</strong><small>{p.imagenes.length}/3 imágenes · {p.publicable?"Publicable":"No publicable"}</small><div className="card-actions">{!admin&&<><button className="btn-small" onClick={()=>open(p)}>Editar</button><button className="btn-small" onClick={()=>setImagesFor(p)}>Imágenes</button></>}<select className="input compact" value={p.estado} onChange={async e=>{await api.patch(`${admin?"/admin/products":"/productive-unit/products"}/${p.id}/status`,{estado:e.target.value});await qc.invalidateQueries({queryKey:["canonical-products"]})}}><option>DRAFT</option><option>AVAILABLE</option><option>OUT_OF_STOCK</option><option>RETIRED</option></select></div></div></article>)}</div><PaginationBar pagination={data.pagination} onPageChange={setPage}/></>:<Empty title="No hay productos"/>}{(editing||creating)&&<Modal title={editing?"Editar producto":"Nuevo producto"} onClose={()=>{setEditing(null);setCreating(false)}}><div className="form-grid">{([['nombre_comercial','Nombre comercial'],['materia_prima','Materia prima'],['presentacion_empaque','Presentación o empaque'],['precio_referencia','Precio de referencia'],['capacidad_produccion_stock','Capacidad o stock'],['dimensiones','Dimensiones'],['colores_disponibles','Colores disponibles'],['certificaciones','Certificaciones']] as [keyof ProductDraft,string][]).map(([key,label])=><Field key={key} label={label}><input className="input" required={['nombre_comercial','materia_prima','presentacion_empaque','precio_referencia','capacidad_produccion_stock'].includes(key)} type={key==='precio_referencia'?'number':'text'} value={draft[key]} onChange={e=>setDraft(d=>({...d,[key]:e.target.value}))}/></Field>)}</div><Field label="Descripción técnica"><textarea className="input" required rows={4} value={draft.descripcion_tecnica} onChange={e=>setDraft(d=>({...d,descripcion_tecnica:e.target.value}))}/></Field><button className="btn" onClick={()=>void save()}>Guardar</button></Modal>}{imagesFor&&<ProductImagesModal product={imagesFor} onClose={()=>setImagesFor(null)} onChanged={()=>qc.invalidateQueries({queryKey:["canonical-products"]})}/>}</section>;
}

export function AdminProductsPage(){return <ProductsPage admin/>}

function ProductImagesModal({product,onClose,onChanged}:{product:CanonicalProduct;onClose:()=>void;onChanged:()=>void}) {
  const [busy,setBusy]=useState(false),feedback=useFeedback();
  const refresh=async()=>{onChanged();};
  return <Modal title={`Imágenes: ${product.nombre_comercial}`} onClose={onClose}><p>Cargue exactamente tres imágenes. Defina una como portada.</p><div className="image-grid">{product.imagenes.map(img=><article key={img.id}><img src={assetUrl(img.url_imagen)} alt={img.texto_alternativo??"Imagen del producto"}/><StatusBadge value={img.es_principal?"PRINCIPAL":`${img.orden_visualizacion+1}`}/><button className="btn-small" onClick={async()=>{await api.patch(`/productive-unit/products/${product.id}/images/${img.id}/main`);await refresh();onClose()}}>Hacer principal</button><ConfirmButton question="¿Eliminar esta imagen?" onConfirm={async()=>{await api.delete(`/productive-unit/products/${product.id}/images/${img.id}`);await refresh();onClose()}}>Eliminar</ConfirmButton></article>)}</div>{product.imagenes.length<3&&<Field label="Agregar imagen"><input className="input" disabled={busy} type="file" accept="image/png,image/jpeg,image/webp" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;setBusy(true);try{const form=new FormData();form.append("file",file);form.append("alt_text",`Imagen de ${product.nombre_comercial}`);await api.post(`/productive-unit/products/${product.id}/images`,form);await refresh();onClose()}catch(err){feedback.error("No se pudo cargar",message(err))}finally{setBusy(false)}}}/></Field>}</Modal>;
}

export function ProductiveUnitProfilePage() {
  const qc=useQueryClient(),feedback=useFeedback();
  const profile=useQuery({queryKey:["productive-unit-profile"],queryFn:()=>api.get<ProductiveUnit>("/productive-unit/profile").then(r=>r.data)});
  const sectors=useQuery({queryKey:["productive-sectors","active"],queryFn:()=>api.get<Paged<ProductiveSector>>("/productive-sectors",{params:{per_page:100}}).then(r=>r.data.items)});
  const [editing,setEditing]=useState(false),[draft,setDraft]=useState<Partial<ProductiveUnit>>({});
  if(profile.isLoading)return <Loading/>;if(profile.error||!profile.data)return <ErrorBox message={message(profile.error)}/>;
  const unit=profile.data, start=()=>{setDraft(unit);setEditing(true)};
  const save=async()=>{try{const {nombre_comercial,razon_social,nit,registro_seprec,registro_pro_bolivia,nombres_representante,apellido_paterno_representante,apellido_materno_representante,departamento,direccion_fisica,telefono_whatsapp,correo_electronico,facebook_url,instagram_url,tiktok_url,resena_comercial}=draft;await api.patch("/productive-unit/profile",{nombre_comercial,razon_social,nit,registro_seprec,registro_pro_bolivia,nombres_representante,apellido_paterno_representante,apellido_materno_representante,departamento,direccion_fisica,telefono_whatsapp,correo_electronico,facebook_url,instagram_url,tiktok_url,resena_comercial});await qc.invalidateQueries({queryKey:["productive-unit-profile"]});setEditing(false);feedback.success("Perfil actualizado",unit.nombre_comercial)}catch(e){feedback.error("No se pudo actualizar",message(e))}};
  return <section>
    <div className="page-heading"><div><span className="eyebrow">Mi Unidad Productiva</span><h1>{unit.nombre_comercial}</h1><StatusBadge value={unit.estado}/></div><button className="btn" onClick={start}>Editar perfil</button></div>
    <div className="profile-grid"><article className="panel">{unit.logo_url?<img className="profile-logo" src={assetUrl(unit.logo_url)} alt={`Logo de ${unit.nombre_comercial}`}/>:<Empty title="Sin logotipo"/>}<Field label="Actualizar logotipo"><input className="input" type="file" accept="image/*" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;const form=new FormData();form.append("file",file);await api.post("/productive-unit/logo",form);await qc.invalidateQueries({queryKey:["productive-unit-profile"]})}}/></Field></article><article className="panel"><p><strong>Razón social:</strong> {unit.razon_social}</p><p><strong>Representante:</strong> {unit.nombre_representante}</p><p><strong>Contacto:</strong> {unit.telefono_whatsapp} · {unit.correo_electronico}</p><p><strong>Dirección:</strong> {unit.departamento}, {unit.direccion_fisica}</p><p>{unit.resena_comercial}</p><p><strong>Sectores:</strong> {unit.sectores.map(s=>s.nombre).join(", ")}</p></article></div>
    {editing&&<Modal title="Editar perfil" onClose={()=>setEditing(false)}><div className="form-grid">{([['nombre_comercial','Nombre comercial'],['razon_social','Razón social'],['nombres_representante','Nombres del representante'],['apellido_paterno_representante','Apellido paterno'],['apellido_materno_representante','Apellido materno'],['departamento','Departamento'],['direccion_fisica','Dirección'],['telefono_whatsapp','WhatsApp'],['correo_electronico','Correo'],['facebook_url','Facebook'],['instagram_url','Instagram'],['tiktok_url','TikTok']] as [keyof ProductiveUnit,string][]).map(([key,label])=><Field key={key} label={label}><input className="input" value={String(draft[key]??"")} onChange={e=>setDraft(d=>({...d,[key]:e.target.value}))}/></Field>)}</div><Field label="Reseña"><textarea className="input" value={draft.resena_comercial??""} onChange={e=>setDraft(d=>({...d,resena_comercial:e.target.value}))}/></Field><Field label="Sectores"><div className="check-grid">{sectors.data?.map(s=><label key={s.id}><input type="checkbox" checked={unit.sectores.some(x=>x.id===s.id)} readOnly/>{s.nombre}</label>)}</div><small>La gestión detallada de sectores usa el contrato específico de perfil.</small></Field><button className="btn" onClick={()=>void save()}>Guardar</button></Modal>}
  </section>;
}

export function UnitSectorsPage(){
  const qc=useQueryClient(),feedback=useFeedback(),[selected,setSelected]=useState<Record<string,string>>({});
  const available=useQuery({queryKey:["productive-sectors","active"],queryFn:()=>api.get<{items:ProductiveSector[]}>("/productive-sectors").then(r=>r.data.items)});
  const own=useQuery({queryKey:["productive-unit-sectors"],queryFn:()=>api.get<{sectores:ProductiveSectorLink[]}>("/productive-unit/sectors").then(r=>r.data.sectores)});
  const effective=Object.keys(selected).length?selected:Object.fromEntries((own.data??[]).map(s=>[s.id,s.detalle_otro??""]));
  const toggle=(sector:ProductiveSector)=>setSelected(current=>{const base=Object.keys(current).length?{...current}:Object.fromEntries((own.data??[]).map(s=>[s.id,s.detalle_otro??""]));if(sector.id in base)delete base[sector.id];else base[sector.id]="";return base});
  const save=async()=>{try{const rows=Object.entries(effective).map(([productive_sector_id,detalle_otro])=>({productive_sector_id,detalle_otro:clean(detalle_otro)}));await api.put("/productive-unit/sectors",{sectores:rows});setSelected({});await qc.invalidateQueries({queryKey:["productive-unit-sectors"]});await qc.invalidateQueries({queryKey:["productive-unit-profile"]});feedback.success("Sectores actualizados","La clasificación de la Unidad Productiva fue guardada.")}catch(e){feedback.error("No se pudieron guardar",message(e))}};
  if(available.isLoading||own.isLoading)return <Loading/>;
  return <section><div className="page-heading"><div><span className="eyebrow">Clasificación</span><h1>Mis Sectores Productivos</h1><p>Seleccione al menos uno. Si elige “Otros”, detalle su actividad.</p></div></div><div className="panel check-grid">{available.data?.map(s=><div key={s.id}><label><input type="checkbox" checked={s.id in effective} onChange={()=>toggle(s)}/>{s.nombre}</label>{s.es_otro&&s.id in effective&&<input className="input" required placeholder="Detalle de Otros" value={effective[s.id]} onChange={e=>setSelected(current=>({...effective,...current,[s.id]:e.target.value}))}/>}</div>)}</div><button className="btn" disabled={!Object.keys(effective).length} onClick={()=>void save()}>Guardar sectores</button></section>;
}

type FairDraft={nombre:string;descripcion:string;ubicacion:string;departamento:string;municipio:string;fecha_inicio:string;fecha_fin:string};
const emptyFair:FairDraft={nombre:"",descripcion:"",ubicacion:"",departamento:"",municipio:"",fecha_inicio:"",fecha_fin:""};
export function FairsPage() {
  const page=1;const [editing,setEditing]=useState<CanonicalFair|null>(null),[creating,setCreating]=useState(false),[draft,setDraft]=useState(emptyFair),[participants,setParticipants]=useState<CanonicalFair|null>(null),[saving,setSaving]=useState(false),[cover,setCover]=useState<File|null>(null),[coverPreview,setCoverPreview]=useState(""),[showCoverPreview,setShowCoverPreview]=useState(false),[uploadProgress,setUploadProgress]=useState(0);
  const qc=useQueryClient(),feedback=useFeedback();const list=useQuery({queryKey:["canonical-fairs",page],queryFn:()=>api.get<Paged<CanonicalFair>>("/admin/fairs",{params:{page}}).then(r=>r.data)}),data=pageData(list.data);
  useEffect(()=>()=>{if(coverPreview.startsWith("blob:"))URL.revokeObjectURL(coverPreview)},[coverPreview]);
  const open=(f?:CanonicalFair)=>{setEditing(f??null);setCreating(!f);setDraft(f?{nombre:f.nombre,descripcion:f.descripcion??"",ubicacion:f.ubicacion,departamento:f.departamento??"",municipio:f.municipio??"",fecha_inicio:f.fecha_inicio,fecha_fin:f.fecha_fin}:emptyFair);setCover(null);setCoverPreview(assetUrl(f?.imagen_portada));setShowCoverPreview(false);setUploadProgress(0)};
  const save=async()=>{
    if(draft.fecha_fin<draft.fecha_inicio){feedback.notify({title:"Revise las fechas",message:"La fecha de finalización no puede ser anterior a la fecha de inicio.",tone:"warning"});return}
    if(!editing&&!cover){feedback.error("Falta la portada","Seleccione una imagen de portada para crear la feria.");return}
    const wasEditing=Boolean(editing);let createdNow=false;
    setSaving(true);
    try{
      const response=editing?await api.patch<CanonicalFair>(`/admin/fairs/${editing.id}`,draft):await api.post<CanonicalFair>("/admin/fairs",draft);
      if(!editing){createdNow=true;setEditing(response.data);setCreating(false)}
      if(cover){const form=new FormData();form.append("file",cover);await api.post(`/admin/fairs/${response.data.id}/cover`,form,{onUploadProgress:event=>{if(event.total)setUploadProgress(Math.min(100,Math.round(event.loaded*100/event.total)))}})}
      await qc.invalidateQueries({queryKey:["canonical-fairs"]});setEditing(null);setCreating(false);setCover(null);setCoverPreview("");feedback.success(wasEditing?"Feria actualizada":"Feria creada",cover?"Los datos y la imagen de portada se guardaron correctamente.":"Los cambios se guardaron conservando la portada actual.")
    }catch(e){feedback.error(createdNow?"Feria creada, portada pendiente":"No se pudo guardar",createdNow?`La feria se creó, pero la portada no pudo subirse. Vuelva a guardar para reintentar. ${message(e)}`:message(e))}
    finally{setSaving(false);setUploadProgress(0)}
  };
  const closeForm=()=>{if(saving)return;setEditing(null);setCreating(false);setCover(null);setCoverPreview("");setShowCoverPreview(false);setUploadProgress(0)};
  return <section>
    <div className="page-heading"><div><span className="eyebrow">Programación</span><h1>Ferias</h1></div><button className="btn" onClick={()=>open()}>Nueva feria</button></div>
    {list.isLoading?<Loading/>:<div className="card-grid">{data.items.map(f=><article className="catalog-card" key={f.id}>{f.imagen_portada&&<img src={assetUrl(f.imagen_portada)} alt=""/>}<div className="card-body"><StatusBadge value={f.estado}/><h2>{f.nombre}</h2><p>{f.ubicacion}</p><small>{f.fecha_inicio} — {f.fecha_fin}</small><div className="card-actions"><button className="btn-small" disabled={['FINISHED','DISABLED'].includes(f.estado)} onClick={()=>open(f)}>Editar</button><button className="btn-small" onClick={()=>setParticipants(f)}>Participaciones</button>{!['FINISHED','DISABLED'].includes(f.estado)&&<><ConfirmButton question="¿Finalizar esta feria?" onConfirm={async()=>{await api.post(`/admin/fairs/${f.id}/finish`);await qc.invalidateQueries({queryKey:["canonical-fairs"]})}}>Finalizar</ConfirmButton><ConfirmButton question="¿Deshabilitar esta feria?" onConfirm={async()=>{await api.post(`/admin/fairs/${f.id}/disable`);await qc.invalidateQueries({queryKey:["canonical-fairs"]})}}>Deshabilitar</ConfirmButton></>}</div></div></article>)}</div>}
    {(editing||creating)&&<Modal title={editing?"Editar feria":"Crear nueva feria"} onClose={closeForm} wide className="fair-form-modal">
      <form className="fair-form" onSubmit={event=>{event.preventDefault();void save()}}>
        <div className="fair-form-intro"><span>Información de la feria</span><p>Complete los datos que se mostrarán en el catálogo público.</p></div>
        <div className="fair-form-grid">
          <div className="fair-field-name"><Field label="Nombre de la feria"><input className="input" required placeholder="Ej.: Feria Productiva Nacional" value={draft.nombre} onChange={e=>setDraft(d=>({...d,nombre:e.target.value}))}/></Field></div>
          <div className="fair-field-description"><Field label="Descripción"><textarea className="input" rows={4} placeholder="Cuente brevemente qué encontrarán los visitantes" value={draft.descripcion} onChange={e=>setDraft(d=>({...d,descripcion:e.target.value}))}/></Field></div>
          <div className="fair-field-cover">
            <span className="fair-cover-label">Imagen de portada</span>
            <div className="fair-cover-control">
              {coverPreview?<button type="button" className="fair-cover-thumb has-image" onClick={()=>setShowCoverPreview(true)} aria-label="Ampliar imagen de portada" title="Haga clic para ampliar"><img src={coverPreview} alt="Vista previa completa de la portada"/><small>Ampliar</small></button>:<div className="fair-cover-thumb"><span>Sin imagen</span></div>}
              <div className="fair-cover-copy">
                <strong>{cover?cover.name:editing&&coverPreview?"Portada actual":"Seleccione una imagen"}</strong>
                <p>Se admite una sola imagen JPG, PNG o WebP, de hasta 10 MB.</p>
                <label className="btn-outline fair-cover-picker">{coverPreview?"Cambiar imagen":"Elegir imagen"}<input type="file" accept="image/png,image/jpeg,image/webp" onChange={event=>{const file=event.target.files?.[0]??null;if(!file)return;if(!["image/png","image/jpeg","image/webp"].includes(file.type)){event.target.value="";feedback.error("Archivo no válido","Seleccione una imagen JPG, PNG o WebP.");return}if(file.size>10*1024*1024){event.target.value="";feedback.error("Imagen demasiado grande","La portada no puede superar los 10 MB.");return}setCover(file);setCoverPreview(URL.createObjectURL(file))}}/></label>
              </div>
            </div>
            <UploadProgress value={uploadProgress}/>
          </div>
          <Field label="Lugar o dirección"><input className="input" required placeholder="Ej.: Campo Ferial, pabellón central" value={draft.ubicacion} onChange={e=>setDraft(d=>({...d,ubicacion:e.target.value}))}/></Field>
          <Field label="Departamento"><select className="input" required value={draft.departamento} onChange={e=>setDraft(d=>({...d,departamento:e.target.value}))}><option value="">Seleccione un departamento</option>{BOLIVIA_DEPARTMENTS.map(item=><option key={item} value={item}>{item}</option>)}</select></Field>
          <Field label="Municipio"><input className="input" required placeholder="Ej.: La Paz" value={draft.municipio} onChange={e=>setDraft(d=>({...d,municipio:e.target.value}))}/></Field>
          <div className="fair-form-dates"><span className="fair-form-section-title">Duración de la feria</span><div><Field label="Fecha de inicio"><input className="input" required type="date" value={draft.fecha_inicio} onChange={e=>setDraft(d=>({...d,fecha_inicio:e.target.value}))}/></Field><Field label="Fecha de finalización"><input className="input" required type="date" min={draft.fecha_inicio||undefined} value={draft.fecha_fin} onChange={e=>setDraft(d=>({...d,fecha_fin:e.target.value}))}/></Field></div></div>
        </div>
        <div className="fair-form-actions"><button type="button" className="btn-outline" disabled={saving} onClick={closeForm}>Cancelar</button><button type="submit" className="btn" disabled={saving}>{saving?uploadProgress>0?`Subiendo imagen ${uploadProgress}%`:"Guardando…":editing?"Guardar cambios":"Crear feria"}</button></div>
      </form>
    </Modal>}
    {showCoverPreview&&coverPreview&&<Modal title="Vista previa de la portada" onClose={()=>setShowCoverPreview(false)} wide className="image-preview-dialog fair-cover-preview-dialog"><img src={coverPreview} alt="Imagen de portada completa"/><div className="modal-actions"><button type="button" className="btn" onClick={()=>setShowCoverPreview(false)}>OK</button></div></Modal>}
    {participants&&<ParticipationsModal fair={participants} onClose={()=>setParticipants(null)}/>}
  </section>;
}

function ParticipationsModal({fair,onClose}:{fair:CanonicalFair;onClose:()=>void}) {
  const [unitId,setUnitId]=useState(""),qc=useQueryClient(),feedback=useFeedback();
  const list=useQuery({queryKey:["fair-participations",fair.id],queryFn:()=>api.get<Paged<FairParticipation>>(`/admin/fairs/${fair.id}/participations`,{params:{per_page:100}}).then(r=>r.data.items)});
  const units=useQuery({queryKey:["productive-units","options"],queryFn:()=>api.get<Paged<ProductiveUnit>>("/admin/productive-units",{params:{per_page:100,estado:"ACTIVE"}}).then(r=>r.data.items)});
  const act=async(path:string)=>{try{await api.post(path);await qc.invalidateQueries({queryKey:["fair-participations",fair.id]})}catch(e){feedback.error("No se pudo actualizar",message(e))}};
  return <Modal title={`Participaciones: ${fair.nombre}`} onClose={onClose}><p>Se asigna la Unidad Productiva completa; sus productos publicables se incorporan automáticamente.</p><div className="toolbar"><select className="input" value={unitId} onChange={e=>setUnitId(e.target.value)}><option value="">Seleccione Unidad Productiva</option>{units.data?.map(u=><option key={u.id} value={u.id}>{u.nombre_comercial}</option>)}</select><button className="btn" disabled={!unitId} onClick={async()=>{await api.post(`/admin/fairs/${fair.id}/participations`,{productive_unit_id:unitId,observaciones:null});setUnitId("");await qc.invalidateQueries({queryKey:["fair-participations",fair.id]})}}>Asignar unidad</button></div>{list.isLoading?<Loading/>:list.data?.length?<div className="table-wrap"><table><thead><tr><th>Unidad Productiva</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{list.data.map(p=><tr key={p.id}><td>{p.nombre_comercial}</td><td><StatusBadge value={p.estado}/></td><td><button className="btn-small" onClick={()=>void act(`/admin/fairs/${fair.id}/participations/${p.id}/authorize`)}>Autorizar</button><button className="btn-small" onClick={()=>void act(`/admin/fairs/${fair.id}/participations/${p.id}/revoke`)}>Revocar</button></td></tr>)}</tbody></table></div>:<Empty title="Sin participaciones"/>}</Modal>;
}

export function PublicCatalogPage() {
  const [q,setQ]=useState(""),[sector,setSector]=useState(""),[department,setDepartment]=useState(""),[page,setPage]=useState(1),[cart,setCart]=useState<Record<string,number>>({});
  const active=useQuery({queryKey:["public","active-fair"],queryFn:()=>api.get<{active:boolean;fair:CanonicalFair|null}>("/public/fairs/active").then(r=>r.data)});
  const sectors=useQuery({queryKey:["productive-sectors","public"],queryFn:()=>api.get<Paged<ProductiveSector>>("/productive-sectors",{params:{per_page:100}}).then(r=>r.data.items)});
  const products=useQuery({queryKey:["public","products",q,sector,department,page],queryFn:()=>api.get<Paged<CanonicalProduct>&{active_catalog:boolean;fair?:CanonicalFair}>("/public/products",{params:{q:q||undefined,sector_id:sector||undefined,departamento:department||undefined,page}}).then(r=>r.data)}),data=pageData(products.data);
  const groups=useMemo(()=>Object.entries(cart).filter(([,quantity])=>quantity>0),[cart]);
  return <><PublicHeader/><main className="container public-main">{active.isLoading?<Loading/>:!active.data?.active?<Empty title="No hay una feria activa" description="El catálogo volverá a estar disponible cuando una feria esté publicada dentro de sus fechas."/>:<><section className="public-hero"><div><span className="eyebrow">Feria activa</span><h1>{active.data.fair?.nombre}</h1><p>{active.data.fair?.descripcion}</p><strong>{active.data.fair?.ubicacion} · {active.data.fair?.fecha_inicio} al {active.data.fair?.fecha_fin}</strong></div>{active.data.fair?.imagen_portada&&<img src={assetUrl(active.data.fair.imagen_portada)} alt={`Portada de ${active.data.fair.nombre}`}/>}</section><div className="toolbar"><SearchField value={q} onChange={v=>{setQ(v);setPage(1)}} placeholder="Buscar productos o unidades…"/><select className="input" value={sector} onChange={e=>setSector(e.target.value)}><option value="">Todos los sectores</option>{sectors.data?.map(s=><option key={s.id} value={s.id}>{s.nombre}</option>)}</select><select className="input" value={department} onChange={e=>setDepartment(e.target.value)}><option value="">Todos los departamentos</option>{BOLIVIA_DEPARTMENTS.map(d=><option key={d}>{d}</option>)}</select></div>{products.isLoading?<Loading/>:products.error?<ErrorBox message={message(products.error)}/>:data.items.length?<><div className="card-grid">{data.items.map(p=><article className="catalog-card" key={p.id}><img src={assetUrl(p.imagenes.find(i=>i.es_principal)?.url_imagen??p.imagenes[0]?.url_imagen)} alt={p.nombre_comercial}/><div className="card-body"><StatusBadge value={p.estado}/><h2>{p.nombre_comercial}</h2><p>{p.descripcion_tecnica}</p><small>{p.unidad_productiva?.nombre_comercial}</small><strong>Bs {Number(p.precio_referencia).toFixed(2)}</strong><Field label="Cantidad"><input className="input compact" type="number" min="0" value={cart[p.id]??0} onChange={e=>setCart(c=>({...c,[p.id]:Math.max(0,Number(e.target.value))}))}/></Field></div></article>)}</div><PaginationBar pagination={data.pagination} onPageChange={setPage}/></>:<Empty title="No se encontraron productos"/>}{groups.length>0&&<button className="floating-cart" onClick={async()=>{try{const response=await api.post<{url:string}>("/public/whatsapp",{items:groups.map(([product_id,quantity])=>({product_id,quantity}))});window.open(response.data.url,"_blank","noopener,noreferrer")}catch(e){alert(message(e))}}}>Consultar por WhatsApp ({groups.length})</button>}</>}</main></>;
}

export function NotFoundPage(){return <><PublicHeader/><main className="container public-main"><Empty title="Página no encontrada"/><Link className="btn" to="/catalogo">Ir al catálogo</Link></main></>}
