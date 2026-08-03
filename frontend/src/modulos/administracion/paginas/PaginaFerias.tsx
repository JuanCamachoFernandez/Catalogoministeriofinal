import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import {
  api,
  urlRecurso,
  type CanonicalFair,
  type FairParticipation,
  type Paged,
  type ProductiveUnit,
} from "../../../compartido";
import { BOLIVIA_DEPARTMENTS } from "../../../compartido/constantes/ubicacionesBolivia";
import {
  BotonConfirmacion,
  EstadoVacio,
  CajaError,
  Campo,
  EstadoCarga,
  Modal,
  BarraPaginacion,
  CampoBusqueda,
  InsigniaEstado,
  ProgresoCarga,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { mensaje, datosPagina } from "../utilidades/administracionCompartida";
import "../../../compartido/estilos/ferias.css";

type FairDraft = {
  nombre: string;
  descripcion: string;
  ubicacion: string;
  departamento: string;
  fecha_inicio: string;
  fecha_fin: string;
};
const emptyFair: FairDraft = {
  nombre: "",
  descripcion: "",
  ubicacion: "",
  departamento: "",
  fecha_inicio: "",
  fecha_fin: "",
};

const FAIR_FIELD_LABELS: Record<string, string> = {
  nombre: "Nombre de la feria",
  descripcion: "Descripción",
  ubicacion: "Lugar o dirección",
  departamento: "Departamento",
  fecha_inicio: "Fecha de inicio",
  fecha_fin: "Fecha de finalización",
  cover: "Imagen de portada",
};

export default function PaginaFerias() {
  const formRef = useRef<HTMLFormElement | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [editing, setEditing] = useState<CanonicalFair | null>(null),
    [creating, setCreating] = useState(false),
    [draft, setDraft] = useState(emptyFair),
    [participants, setParticipants] = useState<CanonicalFair | null>(null),
    [saving, setSaving] = useState(false),
    [cover, setCover] = useState<File | null>(null),
    [coverPreview, setCoverPreview] = useState(""),
    [showCoverPreview, setShowCoverPreview] = useState(false),
    [uploadProgress, setUploadProgress] = useState(0);
  const qc = useQueryClient(),
    feedback = useRetroalimentacion();
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
  const messageForInvalidControl = (
    control: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement,
  ) => {
    const fieldName = control.name || "";
    const label = FAIR_FIELD_LABELS[fieldName] ?? "este campo";
    if (control.validity.valueMissing)
      return `Complete el campo ${label}.`;
    if (control.validity.typeMismatch || control.validity.patternMismatch)
      return `Revise el formato del campo ${label}.`;
    if (control.validity.rangeUnderflow && fieldName === "fecha_fin")
      return "La fecha de finalización no puede ser anterior a la fecha de inicio.";
    return control.validationMessage || `Revise el campo ${label}.`;
  };
  const list = useQuery({
      queryKey: ["canonical-fairs", page, q, dateFrom, dateTo],
      queryFn: () =>
        api
          .get<Paged<CanonicalFair>>("/admin/fairs", {
            params: {
              page,
              q: q || undefined,
              date_from: dateFrom || undefined,
              date_to: dateTo || undefined,
            },
          })
          .then((r) => r.data),
    }),
    data = datosPagina(list.data);
  useEffect(
    () => () => {
      if (coverPreview.startsWith("blob:")) URL.revokeObjectURL(coverPreview);
    },
    [coverPreview],
  );
  useEffect(() => {
    if (creating) {
      document.body.classList.remove("modal-open");
    }
  }, [creating]);
  const open = (f?: CanonicalFair) => {
    setEditing(f ?? null);
    setCreating(!f);
    setDraft(
      f
        ? {
            nombre: f.nombre,
            descripcion: f.descripcion ?? "",
            ubicacion: f.ubicacion,
            departamento: f.departamento ?? "",
            fecha_inicio: f.fecha_inicio,
            fecha_fin: f.fecha_fin,
          }
        : emptyFair,
    );
    setCover(null);
    setCoverPreview(urlRecurso(f?.imagen_portada));
    setShowCoverPreview(false);
    setUploadProgress(0);
  };
  const validateAndSave = (form: HTMLFormElement) => {
    const controls = Array.from(form.elements).filter(
      (
        element,
      ): element is
        | HTMLInputElement
        | HTMLSelectElement
        | HTMLTextAreaElement =>
        element instanceof HTMLInputElement ||
        element instanceof HTMLSelectElement ||
        element instanceof HTMLTextAreaElement,
    );
    const firstInvalid = controls.find((control) => !control.checkValidity());
    if (firstInvalid) {
      focusInvalidControl(firstInvalid, messageForInvalidControl(firstInvalid));
      return false;
    }
    if (draft.fecha_fin < draft.fecha_inicio) {
      const dateEndControl = form.querySelector<HTMLInputElement>(
        '[name="fecha_fin"]',
      );
      if (dateEndControl) {
        focusInvalidControl(
          dateEndControl,
          "La fecha de finalización no puede ser anterior a la fecha de inicio.",
        );
      }
      return false;
    }
    if (!editing && !cover) {
      const coverControl = form.querySelector<HTMLInputElement>('[name="cover"]');
      if (coverControl) {
        focusInvalidControl(
          coverControl,
          "Seleccione una imagen de portada para crear la feria.",
        );
      }
      return false;
    }
    void save();
    return true;
  };
  const save = async () => {
    if (draft.fecha_fin < draft.fecha_inicio) {
      feedback.notify({
        title: "Revise las fechas",
        mensaje:
          "La fecha de finalización no puede ser anterior a la fecha de inicio.",
        tone: "warning",
      });
      return;
    }
    if (!editing && !cover) {
      feedback.error(
        "Falta la portada",
        "Seleccione una imagen de portada para crear la feria.",
      );
      return;
    }
    const wasEditing = Boolean(editing);
    let createdNow = false;
    setSaving(true);
    try {
      const response = editing
        ? await api.patch<CanonicalFair>(`/admin/fairs/${editing.id}`, draft)
        : await api.post<CanonicalFair>("/admin/fairs", draft);
      if (!editing) {
        createdNow = true;
        setEditing(response.data);
        setCreating(false);
      }
      if (cover) {
        const form = new FormData();
        form.append("file", cover);
        await api.post(`/admin/fairs/${response.data.id}/cover`, form, {
          onUploadProgress: (event) => {
            if (event.total)
              setUploadProgress(
                Math.min(100, Math.round((event.loaded * 100) / event.total)),
              );
          },
        });
      }
      await qc.invalidateQueries({ queryKey: ["canonical-fairs"] });
      setEditing(null);
      setCreating(false);
      setCover(null);
      setCoverPreview("");
      feedback.success(
        wasEditing ? "Feria actualizada" : "Feria creada",
        cover
          ? "Los datos y la imagen de portada se guardaron correctamente."
          : "Los cambios se guardaron conservando la portada actual.",
      );
    } catch (e) {
      feedback.error(
        createdNow ? "Feria creada, portada pendiente" : "No se pudo guardar",
        createdNow
          ? `La feria se creó, pero la portada no pudo subirse. Vuelva a guardar para reintentar. ${mensaje(e)}`
          : mensaje(e),
      );
    } finally {
      setSaving(false);
      setUploadProgress(0);
    }
  };
  const closeForm = () => {
    if (saving) return;
    document.body.classList.remove("modal-open");
    setEditing(null);
    setCreating(false);
    setCover(null);
    setCoverPreview("");
    setShowCoverPreview(false);
    setUploadProgress(0);
  };
  const fairForm = (
    <form
      ref={formRef}
      className="registration-form fair-registration-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        validateAndSave(event.currentTarget);
      }}
      onInput={(event) =>
        (event.target as HTMLElement).removeAttribute("aria-invalid")
      }
    >
      <div className="fair-registration-layout">
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>01</span>
          <div>
            <h2>Identidad de la feria</h2>
            <p>Información principal que se mostrará en el catálogo.</p>
          </div>
        </div>
        <div className="registration-grid fair-registration-grid-single">
          <Campo label="Nombre de la feria" required>
            <input
              className="input"
              name="nombre"
              required
              placeholder="Ej.: Feria Productiva Nacional"
              value={draft.nombre}
              onChange={(e) =>
                setDraft((d) => ({ ...d, nombre: e.target.value }))
              }
            />
          </Campo>
          <Campo label="Descripción">
            <textarea
              className="input"
              name="descripcion"
              rows={4}
              placeholder="Cuente brevemente qué encontrarán los visitantes"
              value={draft.descripcion}
              onChange={(e) =>
                setDraft((d) => ({ ...d, descripcion: e.target.value }))
              }
            />
          </Campo>
        </div>
      </section>
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>02</span>
          <div>
            <h2>Portada</h2>
            <p>Seleccione la imagen principal de presentación de la feria.</p>
          </div>
        </div>
        <div className="registration-grid fair-registration-grid-single">
          <div className="fair-cover-upload-row">
            {coverPreview ? (
              <button
                type="button"
                className="fair-cover-preview-card fair-cover-preview-card-small"
                onClick={() => setShowCoverPreview(true)}
                aria-label="Ampliar imagen de portada"
                title="Haga clic para ampliar"
              >
                <img
                  src={coverPreview}
                  alt="Vista previa completa de la portada"
                />
              </button>
            ) : (
              <div className="fair-cover-preview-card fair-cover-preview-card-small fair-cover-preview-empty">
                <span>Sin imagen</span>
              </div>
            )}
            <Campo
              label="Imagen de portada"
              required
              hint="Formatos permitidos: PNG, JPG, JPEG y WebP. Tamaño máximo: 10 MB."
            >
              <input
                className="input registration-file"
                name="cover"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  if (!file) return;
                  if (
                    !["image/png", "image/jpeg", "image/webp"].includes(
                      file.type,
                    )
                  ) {
                    event.target.value = "";
                    feedback.error(
                      "Archivo no válido",
                      "Seleccione una imagen JPG, PNG o WebP.",
                    );
                    return;
                  }
                  if (file.size > 10 * 1024 * 1024) {
                    event.target.value = "";
                    feedback.error(
                      "Imagen demasiado grande",
                      "La portada no puede superar los 10 MB.",
                    );
                    return;
                  }
                  setCover(file);
                  setCoverPreview(URL.createObjectURL(file));
                }}
              />
            </Campo>
          </div>
          <ProgresoCarga value={uploadProgress} />
        </div>
      </section>
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>03</span>
          <div>
            <h2>Ubicación</h2>
            <p>Lugar físico y localización administrativa de la feria.</p>
          </div>
        </div>
        <div className="registration-grid fair-registration-grid-single">
          <Campo label="Lugar o dirección" required>
            <input
              className="input"
              name="ubicacion"
              required
              placeholder="Ej.: Campo Ferial, pabellón central"
              value={draft.ubicacion}
              onChange={(e) =>
                setDraft((d) => ({ ...d, ubicacion: e.target.value }))
              }
            />
          </Campo>
          <Campo label="Departamento" required>
            <select
              className="input"
              name="departamento"
              required
              value={draft.departamento}
              onChange={(e) =>
                setDraft((d) => ({ ...d, departamento: e.target.value }))
              }
            >
              <option value="">Seleccione un departamento</option>
              {BOLIVIA_DEPARTMENTS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </Campo>
        </div>
      </section>
      <section className="registration-section">
        <div className="registration-section-heading">
          <span>04</span>
          <div>
            <h2>Fechas</h2>
            <p>Defina el período en el que la feria estará vigente.</p>
          </div>
        </div>
        <div className="registration-grid">
          <Campo label="Fecha de inicio" required>
            <input
              className="input"
              name="fecha_inicio"
              required
              type="date"
              value={draft.fecha_inicio}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  fecha_inicio: e.target.value,
                }))
              }
            />
          </Campo>
          <Campo label="Fecha de finalización" required>
            <input
              className="input"
              name="fecha_fin"
              required
              type="date"
              min={draft.fecha_inicio || undefined}
              value={draft.fecha_fin}
              onChange={(e) =>
                setDraft((d) => ({ ...d, fecha_fin: e.target.value }))
              }
            />
          </Campo>
        </div>
      </section>
      </div>
      <footer className="registration-actions">
        <span>
          Revise los datos antes de guardar la feria.
        </span>
        <div className="modal-actions">
          <button
            type="button"
            className="admin-unit-action-button admin-unit-action-button-danger"
            disabled={saving}
            onClick={closeForm}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="admin-unit-action-button registration-submit"
            disabled={saving}
          >
            {saving
              ? uploadProgress > 0
                ? `Subiendo imagen ${uploadProgress}%`
                : "Guardando…"
              : editing
                ? "Guardar cambios"
                : "Crear feria"}
          </button>
        </div>
      </footer>
    </form>
  );

  if (creating) {
    return (
      <section className="admin-unit-registration-page">
        <button
          type="button"
          className="back-navigation"
          onClick={closeForm}
        >
          ← Volver al listado
        </button>
        <div className="registration-intro">
          <div>
            <span className="eyebrow">Registrar Feria</span>
            <h1>Nueva Feria</h1>
          </div>
        </div>
        {fairForm}
      </section>
    );
  }

  return (
    <section className="admin-page">
      {" "}
      <div className="page-heading">
        <div>
          <span className="eyebrow">Programación</span>
          <h1>Ferias</h1>
        </div>
        <button
          className="admin-units-create-button"
          onClick={() => open()}
        >
          <Plus aria-hidden="true" />
          Nueva feria
        </button>
      </div>{" "}
      <div className="toolbar admin-requests-toolbar admin-fairs-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar nombre o lugar de feria..."
        />
        <Campo label="Desde">
          <input
            className="input"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
          />
        </Campo>
        <Campo label="Hasta">
          <input
            className="input"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
          />
        </Campo>
      </div>{" "}
      {list.isLoading ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : !data.items.length ? (
        <EstadoVacio title="No hay ferias" />
      ) : (
        <>
          <div className="table-wrap admin-requests-table">
            <table>
              <thead>
                <tr>
                  <th>Feria</th>
                  <th>Lugar</th>
                  <th>Fechas</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((f) => (
                  <tr key={f.id}>
                    <td>
                      <strong>{f.nombre}</strong>
                      <small>{f.departamento}</small>
                    </td>
                    <td>{f.ubicacion}</td>
                    <td>
                      {f.fecha_inicio} — {f.fecha_fin}
                    </td>
                    <td>
                      <InsigniaEstado value={f.estado} />
                    </td>
                    <td>
                      <button
                        className="btn-small"
                        disabled={["FINISHED", "DISABLED"].includes(f.estado)}
                        onClick={() => open(f)}
                      >
                        Editar
                      </button>
                      <button
                        className="btn-small"
                        onClick={() => setParticipants(f)}
                      >
                        Participaciones
                      </button>
                      {!["FINISHED", "DISABLED"].includes(f.estado) && (
                        <>
                          <BotonConfirmacion
                            question="¿Finalizar esta feria?"
                            onConfirm={async () => {
                              await api.post(`/admin/fairs/${f.id}/finish`);
                              await qc.invalidateQueries({
                                queryKey: ["canonical-fairs"],
                              });
                            }}
                          >
                            Finalizar
                          </BotonConfirmacion>
                          <BotonConfirmacion
                            question="¿Deshabilitar esta feria?"
                            onConfirm={async () => {
                              await api.post(`/admin/fairs/${f.id}/disable`);
                              await qc.invalidateQueries({
                                queryKey: ["canonical-fairs"],
                              });
                            }}
                          >
                            Deshabilitar
                          </BotonConfirmacion>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <BarraPaginacion pagination={data.pagination} onPageChange={setPage} />
        </>
      )}{" "}
      {editing && (
        <Modal
          title="Editar feria"
          onClose={closeForm}
          wide
          className="fair-form-modal"
        >
          {fairForm}
        </Modal>
      )}{" "}
      {showCoverPreview && coverPreview && (
        <Modal
          title="Vista previa de la portada"
          onClose={() => setShowCoverPreview(false)}
          wide
          className="image-preview-dialog fair-cover-preview-dialog"
        >
          <img src={coverPreview} alt="Imagen de portada completa" />
          <div className="modal-actions">
            <button
              type="button"
              className="btn"
              onClick={() => setShowCoverPreview(false)}
            >
              OK
            </button>
          </div>
        </Modal>
      )}{" "}
      {participants && (
        <ParticipationsModal
          fair={participants}
          onClose={() => setParticipants(null)}
        />
      )}{" "}
    </section>
  );
}
function ParticipationsModal({
  fair,
  onClose,
}: {
  fair: CanonicalFair;
  onClose: () => void;
}) {
  const [unitId, setUnitId] = useState(""),
    qc = useQueryClient(),
    feedback = useRetroalimentacion();
  const list = useQuery({
    queryKey: ["fair-participations", fair.id],
    queryFn: () =>
      api
        .get<Paged<FairParticipation>>(
          `/admin/fairs/${fair.id}/participations`,
          { params: { per_page: 100 } },
        )
        .then((r) => r.data.items),
  });
  const units = useQuery({
    queryKey: ["productive-units", "options"],
    queryFn: () =>
      api
        .get<Paged<ProductiveUnit>>("/admin/productive-units", {
          params: { per_page: 100, estado: "ACTIVE" },
        })
        .then((r) => r.data.items),
  });
  const act = async (path: string) => {
    try {
      await api.post(path);
      await qc.invalidateQueries({
        queryKey: ["fair-participations", fair.id],
      });
    } catch (e) {
      feedback.error("No se pudo actualizar", mensaje(e));
    }
  };
  return (
    <Modal title={`Participaciones: ${fair.nombre}`} onClose={onClose}>
      <p>
        Se asigna la Unidad Productiva completa; sus productos publicables se
        incorporan automáticamente.
      </p>
      <div className="toolbar">
        <select
          className="input"
          value={unitId}
          onChange={(e) => setUnitId(e.target.value)}
        >
          <option value="">Seleccione Unidad Productiva</option>
          {units.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.nombre_comercial}
            </option>
          ))}
        </select>
        <button
          className="btn"
          disabled={!unitId}
          onClick={async () => {
            await api.post(`/admin/fairs/${fair.id}/participations`, {
              productive_unit_id: unitId,
              observaciones: null,
            });
            setUnitId("");
            await qc.invalidateQueries({
              queryKey: ["fair-participations", fair.id],
            });
          }}
        >
          Asignar unidad
        </button>
      </div>
      {list.isLoading ? (
        <EstadoCarga />
      ) : list.data?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Unidad Productiva</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((p) => (
                <tr key={p.id}>
                  <td>{p.nombre_comercial}</td>
                  <td>
                    <InsigniaEstado value={p.estado} />
                  </td>
                  <td>
                    <button
                      className="btn-small"
                      onClick={() =>
                        void act(
                          `/admin/fairs/${fair.id}/participations/${p.id}/authorize`,
                        )
                      }
                    >
                      Autorizar
                    </button>
                    <button
                      className="btn-small"
                      onClick={() =>
                        void act(
                          `/admin/fairs/${fair.id}/participations/${p.id}/revoke`,
                        )
                      }
                    >
                      Revocar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EstadoVacio title="Sin participaciones" />
      )}
    </Modal>
  );
}
