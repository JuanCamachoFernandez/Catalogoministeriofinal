import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, Store } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiError, assetUrl, uploadFile, type Exhibitor } from "./api";
import { BOLIVIA_DEPARTMENTS, municipalitiesFor } from "./boliviaLocations";
import { ProductManager } from "./ProductManager";
import { ProfilePasswordCard } from "./ProfilePasswordCard";
import { useAuth } from "./AuthContext";
import { ErrorBox, Field, Loading, Modal, SearchableSelect, UploadProgress, useFeedback } from "./ui";

export function ExhibitorProductsPage() {
  return <ProductManager mode="exhibitor" />;
}

type ProfileDraft = {
  nombre_comercial: string;
  telefono_whatsapp: string;
  departamento: string;
  municipio: string;
  direccion: string;
  descripcion: string;
  descripcion_productos: string;
  logo: string;
};
const empty: ProfileDraft = {
  nombre_comercial: "",
  telefono_whatsapp: "",
  departamento: "",
  municipio: "",
  direccion: "",
  descripcion: "",
  descripcion_productos: "",
  logo: "",
};

export function ExhibitorProfilePage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const { user, refresh: refreshSession } = useAuth();
  const profile = useQuery({
    queryKey: ["exhibitor", "profile", user?.id],
    queryFn: () => api.get<Exhibitor>("/exhibitor/profile").then((r) => r.data),
  });
  const [draft, setDraft] = useState<ProfileDraft>(empty);
  const [draftOwnerId, setDraftOwnerId] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [zoomedLogo, setZoomedLogo] = useState("");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState(0);
  /* eslint-disable react-hooks/set-state-in-effect -- hidrata un formulario editable desde la respuesta remota */
  useEffect(() => {
    // El formulario se hidrata cuando termina la consulta remota del perfil.
    if (profile.data && profile.data.user_id === user?.id) {
      setDraft({
        nombre_comercial: profile.data.nombre_comercial,
        telefono_whatsapp: profile.data.telefono_whatsapp ?? "",
        departamento: profile.data.departamento ?? "",
        municipio: profile.data.municipio ?? "",
        direccion: profile.data.direccion ?? "",
        descripcion: profile.data.descripcion ?? "",
        descripcion_productos: profile.data.descripcion_productos ?? "",
        logo: profile.data.logo ?? "",
      });
      setDraftOwnerId(profile.data.user_id ?? "");
    }
  }, [profile.data, user?.id]);
  useEffect(() => () => {
    if (logoPreview.startsWith("blob:")) URL.revokeObjectURL(logoPreview);
  }, [logoPreview]);
  /* eslint-enable react-hooks/set-state-in-effect */
  const change = (key: keyof ProfileDraft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    try {
      const logoUrl = logo
        ? await uploadFile(logo, "logos", setProgress)
        : draft.logo || null;
      await api.patch("/exhibitor/profile", { ...draft, logo: logoUrl });
      await queryClient.invalidateQueries({
        queryKey: ["exhibitor", "profile", user?.id],
      });
      await refreshSession();
      setLogo(null);
      setLogoPreview("");
      feedback.success("Empresa actualizada", "Los cambios se guardaron correctamente.");
    } catch (reason) {
      feedback.error("No se pudo guardar la empresa", apiError(reason, "Revise los datos e inténtelo nuevamente."));
    } finally {
      setPending(false);
      setProgress(0);
    }
  };
  if (profile.isLoading || draftOwnerId !== user?.id) return <Loading label="Cargando su empresa…" />;
  if (profile.error) return <ErrorBox message={apiError(profile.error)} />;
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">Mi empresa</span>
          <h1>Perfil del expositor</h1>
          <p>
            Esta información identifica su emprendimiento dentro del catálogo.
          </p>
        </div>
      </div>
      <form className="profile-layout profile-page" onSubmit={submit}>
        <aside className="panel profile-logo-card">
          <button type="button" className="profile-image-frame profile-image-button" onClick={() => setZoomedLogo(logoPreview || assetUrl(draft.logo))} disabled={!logoPreview && !draft.logo}>
          {logoPreview || draft.logo ? (
            <img src={logoPreview || assetUrl(draft.logo)} alt="Logo de la empresa" />
          ) : (
            <div className="avatar large">
              <Store />
            </div>
          )}
          </button>
          <label className="profile-file-button">
            <span>{logo ? "Cambiar imagen seleccionada" : "Seleccionar nuevo logo"}</span>
            <input type="file" accept="image/*" onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              setLogo(selected);
              setLogoPreview(selected ? URL.createObjectURL(selected) : "");
            }}/>
          </label>
          {logo && <small className="selected-file-name">{logo.name}</small>}
          <p className="form-hint">
            Use una imagen cuadrada, clara y con buen contraste.
          </p>
          <UploadProgress value={progress} />
        </aside>
        <section className="panel form-grid profile-form-card">
          <Field label="Nombre comercial">
            <input
              className="input"
              required
              value={draft.nombre_comercial}
              onChange={(e) => change("nombre_comercial", e.target.value)}
            />
          </Field>
          <Field label="WhatsApp">
            <input
              className="input"
              required
              value={draft.telefono_whatsapp}
              onChange={(e) => change("telefono_whatsapp", e.target.value)}
            />
          </Field>
          <Field label="Departamento">
            <SearchableSelect
              value={draft.departamento}
              options={BOLIVIA_DEPARTMENTS.map((value) => ({ value, label: value }))}
              placeholder="Seleccione un departamento"
              searchPlaceholder="Buscar departamento…"
              ariaLabel="Departamento"
              onChange={(value) => {
                change("departamento", value);
                if (!municipalitiesFor(value).includes(draft.municipio)) change("municipio", "");
              }}
            />
          </Field>
          <Field label="Municipio">
            <SearchableSelect
              disabled={!draft.departamento}
              value={draft.municipio}
              options={municipalitiesFor(draft.departamento).map((value) => ({ value, label: value }))}
              placeholder="Seleccione un municipio"
              searchPlaceholder="Buscar municipio…"
              ariaLabel="Municipio"
              onChange={(value) => change("municipio", value)}
            />
          </Field>
          <Field label="Dirección">
            <input
              className="input"
              value={draft.direccion}
              onChange={(e) => change("direccion", e.target.value)}
            />
          </Field>
          <Field label="Descripción del emprendimiento">
            <textarea
              className="input"
              rows={5}
              value={draft.descripcion}
              onChange={(e) => change("descripcion", e.target.value)}
            />
          </Field>
          <Field label="Descripción general de sus productos">
            <textarea
              className="input"
              rows={5}
              value={draft.descripcion_productos}
              onChange={(e) => change("descripcion_productos", e.target.value)}
            />
          </Field>
          <div className="full profile-save-row">
            <button className="btn" disabled={pending}>
              <Save /> {pending ? "Guardando…" : "Guardar cambios"}
            </button>
          </div>
        </section>
      </form>
      <ProfilePasswordCard/>
      {zoomedLogo && <Modal title="Logo de la empresa" onClose={() => setZoomedLogo("")}><div className="image-preview-dialog"><img src={zoomedLogo} alt="Logo ampliado de la empresa"/><div className="modal-actions"><button type="button" className="btn" onClick={() => setZoomedLogo("")} autoFocus>OK</button></div></div></Modal>}
    </>
  );
}
