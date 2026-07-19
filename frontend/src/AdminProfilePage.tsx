import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Save, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiError, assetUrl, uploadFile, type AdminUser } from "./api";
import { useAuth } from "./AuthContext";
import { gmailAddress, gmailLocalPart } from "./adminUserUtils";
import { ProfilePasswordCard } from "./ProfilePasswordCard";
import { ErrorBox, Field, Loading, Modal, UploadProgress, useFeedback } from "./ui";

type AdminProfileDraft = {
  first_name: string;
  apellido_paterno: string;
  apellido_materno: string;
  numero_documento: string;
  email_local: string;
  phone: string;
  cargo: string;
  unidad: string;
  observaciones: string;
  foto_perfil: string;
};

const empty: AdminProfileDraft = {
  first_name: "",
  apellido_paterno: "",
  apellido_materno: "",
  numero_documento: "",
  email_local: "",
  phone: "",
  cargo: "",
  unidad: "",
  observaciones: "",
  foto_perfil: "",
};

export function AdminProfilePage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const { user, refresh } = useAuth();
  const profile = useQuery({
    queryKey: ["admin", "own-profile", user?.id],
    queryFn: () => api.get<AdminUser>("/admin/profile").then((response) => response.data),
  });
  const [draft, setDraft] = useState(empty);
  const [draftOwnerId, setDraftOwnerId] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState("");
  const [zoomedPhoto, setZoomedPhoto] = useState("");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState(0);
  /* eslint-disable react-hooks/set-state-in-effect -- hidrata el formulario con el perfil remoto */
  useEffect(() => {
    if (!profile.data || profile.data.id !== user?.id) return;
    setDraft({
      first_name: profile.data.first_name ?? "",
      apellido_paterno: profile.data.apellido_paterno ?? profile.data.last_name ?? "",
      apellido_materno: profile.data.apellido_materno ?? "",
      numero_documento: profile.data.numero_documento ?? "",
      email_local: gmailLocalPart(profile.data.email),
      phone: profile.data.phone ?? "",
      cargo: profile.data.cargo ?? "",
      unidad: profile.data.unidad ?? "",
      observaciones: profile.data.observaciones ?? "",
      foto_perfil: profile.data.foto_perfil ?? "",
    });
    setDraftOwnerId(profile.data.id);
  }, [profile.data, user?.id]);
  /* eslint-enable react-hooks/set-state-in-effect */
  useEffect(() => () => {
    if (photoPreview.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
  }, [photoPreview]);
  const change = (field: keyof AdminProfileDraft, value: string) =>
    setDraft((current) => ({ ...current, [field]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.first_name.trim() || !draft.apellido_paterno.trim() || !draft.numero_documento.trim() || !draft.email_local.trim()) {
      feedback.error("Faltan datos del perfil", "Complete nombres, apellido paterno, CI y Gmail.");
      return;
    }
    setPending(true);
    try {
      const photoUrl = photo
        ? await uploadFile(photo, "perfiles", setProgress)
        : draft.foto_perfil || null;
      await api.patch("/admin/profile", {
        first_name: draft.first_name.trim(),
        apellido_paterno: draft.apellido_paterno.trim(),
        apellido_materno: draft.apellido_materno.trim() || null,
        numero_documento: draft.numero_documento.trim(),
        email: gmailAddress(draft.email_local),
        phone: draft.phone.trim() || null,
        cargo: draft.cargo.trim() || null,
        unidad: draft.unidad.trim() || null,
        observaciones: draft.observaciones.trim() || null,
        foto_perfil: photoUrl,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin", "own-profile", user?.id] });
      await refresh();
      setPhoto(null);
      setPhotoPreview("");
      feedback.success("Perfil actualizado", "Sus datos personales se guardaron correctamente.");
    } catch (reason) {
      feedback.error("No se pudo guardar el perfil", apiError(reason, "Revise los datos e inténtelo nuevamente."));
    } finally {
      setPending(false);
      setProgress(0);
    }
  };
  if (profile.isLoading || draftOwnerId !== user?.id) return <Loading label="Cargando su perfil…" />;
  if (profile.error) return <ErrorBox message={apiError(profile.error)} />;
  return <>
    <div className="page-header">
      <div><span className="eyebrow">Cuenta personal</span><h1>Mi perfil</h1><p>Administre sus datos personales y la fotografía de su cuenta.</p></div>
    </div>
    <form className="profile-layout profile-page" onSubmit={submit} noValidate>
      <aside className="panel profile-logo-card">
        <button type="button" className="profile-image-frame profile-photo-frame profile-image-button" onClick={() => setZoomedPhoto(photoPreview || assetUrl(draft.foto_perfil))} disabled={!photoPreview && !draft.foto_perfil}>
          {photoPreview || draft.foto_perfil
            ? <img src={photoPreview || assetUrl(draft.foto_perfil)} alt="Fotografía de perfil" />
            : <div className="avatar large"><UserRound /></div>}
        </button>
        <label className="profile-file-button"><Camera size={18}/><span>{photo ? "Cambiar fotografía" : "Seleccionar fotografía"}</span><input type="file" accept="image/*" onChange={(event) => {
          const selected = event.target.files?.[0] ?? null;
          setPhoto(selected);
          setPhotoPreview(selected ? URL.createObjectURL(selected) : "");
        }}/></label>
        {photo && <small className="selected-file-name">{photo.name}</small>}
        <UploadProgress value={progress}/>
        <div className="profile-identity"><ShieldCheck/><div><strong>{profile.data?.username}</strong><small>{profile.data?.role === "SUPERADMIN" ? "Superadministrador" : "Administrador"}</small></div></div>
      </aside>
      <section className="panel form-grid profile-form-card">
        <Field label="Nombres"><input className="input" value={draft.first_name} onChange={(event) => change("first_name", event.target.value)}/></Field>
        <Field label="Apellido paterno"><input className="input" value={draft.apellido_paterno} onChange={(event) => change("apellido_paterno", event.target.value)}/></Field>
        <Field label="Apellido materno"><input className="input" value={draft.apellido_materno} onChange={(event) => change("apellido_materno", event.target.value)}/></Field>
        <Field label="CI"><input className="input" value={draft.numero_documento} onChange={(event) => change("numero_documento", event.target.value)}/></Field>
        <Field label="Gmail"><div className="gmail-input"><input className="input" value={draft.email_local} onChange={(event) => change("email_local", event.target.value.replace(/@.*$/, ""))}/><span>@gmail.com</span></div></Field>
        <Field label="Celular"><input className="input" inputMode="tel" value={draft.phone} onChange={(event) => change("phone", event.target.value)}/></Field>
        <Field label="Cargo"><input className="input" value={draft.cargo} onChange={(event) => change("cargo", event.target.value)}/></Field>
        <Field label="Unidad"><input className="input" value={draft.unidad} onChange={(event) => change("unidad", event.target.value)}/></Field>
        <Field label="Observaciones"><textarea className="input" rows={4} value={draft.observaciones} onChange={(event) => change("observaciones", event.target.value)}/></Field>
        <div className="full profile-save-row"><button className="btn" disabled={pending}><Save/>{pending ? "Guardando…" : "Guardar cambios"}</button></div>
      </section>
    </form>
    <ProfilePasswordCard/>
    {zoomedPhoto && <Modal title="Fotografía de perfil" onClose={() => setZoomedPhoto("")}><div className="image-preview-dialog"><img src={zoomedPhoto} alt="Fotografía de perfil ampliada"/><div className="modal-actions"><button type="button" className="btn" onClick={() => setZoomedPhoto("")} autoFocus>OK</button></div></div></Modal>}
  </>;
}
