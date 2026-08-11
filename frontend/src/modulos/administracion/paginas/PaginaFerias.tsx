import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownUp,
  Ban,
  CalendarCheck2,
  Pencil,
  Plus,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  api,
  urlRecurso,
  type CanonicalFair,
  type EventAnimation,
  type FairKind,
  type Paged,
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
  SelectorBuscable,
  useRetroalimentacion,
} from "../../../compartido/componentes";
import { mensaje, datosPagina } from "../utilidades/administracionCompartida";
import "../../../compartido/estilos/ferias.css";

type HelpPanelId =
  | "publish-kind-general"
  | "publish-kind-fair"
  | "publish-kind-event"
  | "palette"
  | "palette-recommendation"
  | "color-primary"
  | "color-secondary"
  | "color-tertiary"
  | "animation-aurora"
  | "animation-shimmer"
  | "animation-float"
  | "animation-glow";

type EventPalette = {
  color_primario: string;
  color_secundario: string;
  color_terciario: string;
};

type EventThemePreset = {
  id: "INSTITUTIONAL" | "MOTHERS_DAY";
  label: string;
  teaser: string;
  description: string;
  palette: EventPalette;
  animations: EventAnimation[];
};

type FairDraft = {
  tipo: FairKind;
  nombre: string;
  descripcion: string;
  ubicacion: string;
  departamento: string;
  departamentos: string[];
  fecha_inicio: string;
  fecha_fin: string;
  color_primario: string;
  color_secundario: string;
  color_terciario: string;
  animaciones_tema: EventAnimation[];
};

const FAIR_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "DRAFT", label: "Preparación" },
  { value: "PUBLISHED", label: "Publicada" },
  { value: "FINISHED", label: "Finalizada" },
  { value: "DISABLED", label: "Cancelada" },
];

const FAIR_TYPE_OPTIONS: Array<{
  value: FairKind;
  label: string;
  teaser: string;
  helpId: HelpPanelId;
  helpText: string;
}> = [
  {
    value: "FAIR",
    label: "Feria",
    teaser: "Presentación institucional",
    helpId: "publish-kind-fair",
    helpText:
      "Usa la apariencia institucional normal, ideal para ferias tradicionales sin ambientación temática.",
  },
  {
    value: "EVENT",
    label: "Evento",
    teaser: "Tema visual curado",
    helpId: "publish-kind-event",
    helpText:
      "Activa fondo temático, colores personalizados, botones con más estilo y una experiencia pública más visual.",
  },
];

const EVENT_ANIMATION_OPTIONS: Array<{
  value: EventAnimation;
  label: string;
  teaser: string;
  helpId: HelpPanelId;
  helpText: string;
}> = [
  {
    value: "AURORA",
    label: "Movimiento suave",
    teaser: "Gradiente suave y continuo",
    helpId: "animation-aurora",
    helpText:
      "Mueve el fondo lentamente para dar una sensacion mas elegante y dinamica.",
  },
  {
    value: "SHIMMER",
    label: "Brillo sutil",
    teaser: "Reflejo sutil sobre superficies",
    helpId: "animation-shimmer",
    helpText:
      "Agrega un reflejo ligero que hace que la interfaz se vea mas moderna.",
  },
  {
    value: "FLOAT",
    label: "Flotacion suave",
    teaser: "Capas con desplazamiento leve",
    helpId: "animation-float",
    helpText:
      "Desplaza suavemente las formas del fondo para dar mas profundidad visual.",
  },
  {
    value: "GLOW",
    label: "Resplandor suave",
    teaser: "Realce suave en bordes y CTA",
    helpId: "animation-glow",
    helpText:
      "Realza botones y bloques con un brillo fino y mas presencia visual.",
  },
];

const DEFAULT_EVENT_PRIMARY = "#1d872e";

const FAIR_FIELD_LABELS: Record<string, string> = {
  tipo: "Tipo de publicación",
  nombre: "Nombre",
  descripcion: "Descripción",
  ubicacion: "Lugar o dirección",
  departamento: "Departamento",
  fecha_inicio: "Fecha de inicio",
  fecha_fin: "Fecha de finalización",
  cover: "Imagen de portada",
  color_primario: "Color principal",
  color_secundario: "Segundo color",
  color_terciario: "Tercer color",
  animaciones_tema: "Animaciones del evento",
};

function clampChannel(value: number) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function hexToRgb(hex: string) {
  const clean = hex.replace("#", "");
  const parsed = Number.parseInt(clean, 16);
  return {
    r: clampChannel((parsed >> 16) & 255),
    g: clampChannel((parsed >> 8) & 255),
    b: clampChannel(parsed & 255),
  };
}

function rgbToHsl(r: number, g: number, b: number) {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (delta === 0) return { h: 0, s: 0, l: lightness };
  const saturation =
    lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
  let hue: number;
  if (max === red) hue = (green - blue) / delta + (green < blue ? 6 : 0);
  else if (max === green) hue = (blue - red) / delta + 2;
  else hue = (red - green) / delta + 4;
  return { h: hue / 6, s: saturation, l: lightness };
}

function hslToHex(h: number, s: number, l: number) {
  const hueToRgb = (p: number, q: number, t: number) => {
    let next = t;
    if (next < 0) next += 1;
    if (next > 1) next -= 1;
    if (next < 1 / 6) return p + (q - p) * 6 * next;
    if (next < 1 / 2) return q;
    if (next < 2 / 3) return p + (q - p) * (2 / 3 - next) * 6;
    return p;
  };
  let r = l;
  let g = l;
  let b = l;
  if (s !== 0) {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hueToRgb(p, q, h + 1 / 3);
    g = hueToRgb(p, q, h);
    b = hueToRgb(p, q, h - 1 / 3);
  }
  return `#${[r, g, b]
    .map((channel) =>
      clampChannel(channel * 255).toString(16).padStart(2, "0"),
    )
    .join("")}`;
}

function recommendGradientPalette(primary: string): EventPalette {
  const { r, g, b } = hexToRgb(primary);
  const base = rgbToHsl(r, g, b);
  const hue = base.s < 0.12 ? 0.56 : base.h;
  const saturation = Math.min(0.84, Math.max(0.5, base.s));
  return {
    color_primario: primary,
    color_secundario: hslToHex(
      (hue + 0.08) % 1,
      saturation,
      Math.max(0.38, Math.min(0.62, base.l + 0.07)),
    ),
    color_terciario: hslToHex(
      (hue + 0.17) % 1,
      Math.min(0.88, saturation + 0.04),
      Math.max(0.34, Math.min(0.56, base.l + 0.02)),
    ),
  };
}

const defaultEventPalette = recommendGradientPalette(DEFAULT_EVENT_PRIMARY);

const emptyFair: FairDraft = {
  tipo: "FAIR",
  nombre: "",
  descripcion: "",
  ubicacion: "",
  departamento: "",
  departamentos: [],
  fecha_inicio: "",
  fecha_fin: "",
  ...defaultEventPalette,
  animaciones_tema: ["FLOAT"],
};

function badgeLabel(kind: FairKind) {
  return kind === "EVENT" ? "Evento" : "Feria";
}

function animationLabel(value: EventAnimation) {
  return EVENT_ANIMATION_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function animationPreviewClass(value?: EventAnimation) {
  if (!value) return "";
  return `event-preview-animation-${value.toLowerCase()}`;
}

function departmentSummary(departments: string[]) {
  if (departments.length === BOLIVIA_DEPARTMENTS.length) return "Todos los departamentos";
  if (departments.length === 1) return departments[0];
  return `${departments.length} departamentos`;
}

function AyudaContextual({
  id,
  activeId,
  title,
  content,
  onToggle,
}: {
  id: HelpPanelId;
  activeId: HelpPanelId | null;
  title: string;
  content: string;
  onToggle: (id: HelpPanelId) => void;
}) {
  const open = activeId === id;
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [panelPosition, setPanelPosition] = useState({ left: 16, top: 16, width: 320 });
  const updatePanelPosition = () => {
    const triggerRect = triggerRef.current?.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 32);
    setPanelPosition({
      width,
      left: triggerRect
        ? Math.min(Math.max(16, triggerRect.right - width), window.innerWidth - width - 16)
        : 16,
      top: triggerRect
        ? Math.min(Math.max(16, triggerRect.top), window.innerHeight - 180)
        : 16,
    });
  };
  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", updatePanelPosition);
    return () => window.removeEventListener("resize", updatePanelPosition);
  }, [open]);
  return (
    <div className="admin-inline-help">
      <button
        ref={triggerRef}
        type="button"
        className="admin-inline-help-button"
        aria-label={`Mostrar ayuda para ${title}`}
        aria-expanded={open}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          updatePanelPosition();
          onToggle(id);
        }}
      >
        ?
      </button>
      {open &&
        createPortal(
          <>
            <button
              type="button"
              className="admin-inline-help-backdrop"
              aria-label="Cerrar ayuda"
              onClick={() => onToggle(id)}
            />
            <div
              className="admin-inline-help-card"
              role="dialog"
              aria-modal="true"
              aria-label={`Ayuda para ${title}`}
              style={panelPosition}
            >
              <div className="admin-inline-help-card-header">
                <strong>{title}</strong>
                <button
                  type="button"
                  aria-label="Cerrar ayuda"
                  onClick={() => onToggle(id)}
                >
                  <X size={16} />
                </button>
              </div>
              <p>{content}</p>
            </div>
          </>,
          document.body,
        )}
    </div>
  );
}

export default function PaginaFerias() {
  const formRef = useRef<HTMLFormElement | null>(null);
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [editing, setEditing] = useState<CanonicalFair | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<FairDraft>(emptyFair);
  const [activeHelpPanel, setActiveHelpPanel] = useState<HelpPanelId | null>(null);
  const [saving, setSaving] = useState(false);
  const [cover, setCover] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState("");
  const [showCoverPreview, setShowCoverPreview] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const qc = useQueryClient();
  const feedback = useRetroalimentacion();
  const entityLabel = draft.tipo === "EVENT" ? "evento" : "feria";

  const list = useQuery({
    queryKey: ["canonical-fairs", page, q, estado, sortDir, dateFrom, dateTo],
    queryFn: () =>
      api
        .get<Paged<CanonicalFair>>("/admin/fairs", {
          params: {
            page,
            per_page: 10,
            q: q || undefined,
            estado: estado || undefined,
            sort_dir: sortDir,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
          },
        })
        .then((r) => r.data),
  });
  const data = datosPagina(list.data);

  useEffect(
    () => () => {
      if (coverPreview.startsWith("blob:")) URL.revokeObjectURL(coverPreview);
    },
    [coverPreview],
  );

  useEffect(() => {
    if (creating || editing) document.body.classList.remove("modal-open");
  }, [creating, editing]);

  useEffect(() => {
    if (!activeHelpPanel) return;
    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveHelpPanel(null);
    };
    document.addEventListener("keydown", closeWithEscape);
    return () => document.removeEventListener("keydown", closeWithEscape);
  }, [activeHelpPanel]);

  const toggleHelpPanel = (id: HelpPanelId) => {
    setActiveHelpPanel((current) => (current === id ? null : id));
  };

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
    if (control.validity.valueMissing) return `Complete el campo ${label}.`;
    if (control.validity.typeMismatch || control.validity.patternMismatch)
      return `Revise el formato del campo ${label}.`;
    if (control.validity.rangeUnderflow && fieldName === "fecha_fin")
      return "La fecha de finalización no puede ser anterior a la fecha de inicio.";
    return control.validationMessage || `Revise el campo ${label}.`;
  };

  const handlePrimaryColorChange = (value: string) => {
    const next = recommendGradientPalette(value);
    setDraft((current) => ({
      ...current,
      color_primario: value,
      color_secundario: next.color_secundario,
      color_terciario: next.color_terciario,
    }));
  };

  const toggleAnimation = (animation: EventAnimation) => {
    setDraft((current) => ({
      ...current,
      animaciones_tema: [animation],
    }));
  };

  const open = (fair?: CanonicalFair) => {
    setEditing(fair ?? null);
    setCreating(!fair);
    setActiveHelpPanel(null);
    setDraft(
      fair
        ? {
            tipo: fair.tipo ?? "FAIR",
            nombre: fair.nombre,
            descripcion: fair.descripcion ?? "",
            ubicacion: fair.ubicacion,
            departamento: fair.departamento ?? "",
            departamentos:
              fair.departamentos?.length
                ? fair.departamentos
                : fair.tipo === "EVENT" && fair.departamento && BOLIVIA_DEPARTMENTS.includes(fair.departamento)
                  ? [fair.departamento]
                  : [],
            fecha_inicio: fair.fecha_inicio,
            fecha_fin: fair.fecha_fin,
            color_primario: fair.color_primario ?? defaultEventPalette.color_primario,
            color_secundario: fair.color_secundario ?? defaultEventPalette.color_secundario,
            color_terciario: fair.color_terciario ?? defaultEventPalette.color_terciario,
            animaciones_tema: fair.animaciones_tema?.length
              ? fair.animaciones_tema
              : ["FLOAT"],
          }
        : { ...emptyFair },
    );
    setCover(null);
    setCoverPreview(urlRecurso(fair?.imagen_portada));
    setShowCoverPreview(false);
    setUploadProgress(0);
  };

  const validateEventTheme = (form: HTMLFormElement) => {
    if (draft.tipo !== "EVENT") return true;
    if (!draft.departamentos.length) {
      const control = form.querySelector<HTMLInputElement>('[name="departamentos"]');
      if (control) {
        focusInvalidControl(control, "Seleccione al menos un departamento para el evento.");
      }
      return false;
    }
    if (!draft.animaciones_tema.length) {
      const control = form.querySelector<HTMLInputElement>('[name="animaciones_tema"]');
      if (control) {
        focusInvalidControl(control, "Seleccione al menos una animación para el evento.");
      }
      return false;
    }
    return true;
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
      const dateEndControl = form.querySelector<HTMLInputElement>('[name="fecha_fin"]');
      if (dateEndControl) {
        focusInvalidControl(
          dateEndControl,
          "La fecha de finalización no puede ser anterior a la fecha de inicio.",
        );
      }
      return false;
    }
    if (!validateEventTheme(form)) return false;
    if (!editing && !cover) {
      const coverControl = form.querySelector<HTMLInputElement>('[name="cover"]');
      if (coverControl) {
        focusInvalidControl(
          coverControl,
          `Seleccione una imagen de portada para crear el ${entityLabel}.`,
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
        mensaje: "La fecha de finalización no puede ser anterior a la fecha de inicio.",
        tone: "warning",
      });
      return;
    }
    const payload = {
      ...draft,
      departamento:
        draft.tipo === "EVENT"
          ? departmentSummary(draft.departamentos)
          : draft.departamento,
      departamentos: draft.tipo === "EVENT" ? draft.departamentos : [],
      animaciones_tema: draft.tipo === "EVENT" ? draft.animaciones_tema : [],
      color_primario: draft.tipo === "EVENT" ? draft.color_primario : null,
      color_secundario: draft.tipo === "EVENT" ? draft.color_secundario : null,
      color_terciario: draft.tipo === "EVENT" ? draft.color_terciario : null,
    };
    const wasEditing = Boolean(editing);
    let createdNow = false;
    setSaving(true);
    try {
      const response = editing
        ? await api.patch<CanonicalFair>(`/admin/fairs/${editing.id}`, payload)
        : await api.post<CanonicalFair>("/admin/fairs", payload);
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
            if (event.total) {
              setUploadProgress(
                Math.min(100, Math.round((event.loaded * 100) / event.total)),
              );
            }
          },
        });
      }
      await qc.invalidateQueries({ queryKey: ["canonical-fairs"] });
      setEditing(null);
      setCreating(false);
      setCover(null);
      setCoverPreview("");
      setActiveHelpPanel(null);
      feedback.success(
        wasEditing ? `${badgeLabel(draft.tipo)} actualizado` : `${badgeLabel(draft.tipo)} creado`,
        cover
          ? "Los datos y la imagen de portada se guardaron correctamente."
          : "Los cambios se guardaron conservando la portada actual.",
      );
    } catch (error) {
      feedback.error(
        createdNow ? `${badgeLabel(draft.tipo)} creado, portada pendiente` : "No se pudo guardar",
        createdNow
          ? `La publicación se creó, pero la portada no pudo subirse. Vuelva a guardar para reintentar. ${mensaje(error)}`
          : mensaje(error),
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
    setActiveHelpPanel(null);
    setCover(null);
    setCoverPreview("");
    setShowCoverPreview(false);
    setUploadProgress(0);
  };

  const coverStep = draft.tipo === "EVENT" ? "03" : "02";
  const locationStep = draft.tipo === "EVENT" ? "04" : "03";
  const datesStep = draft.tipo === "EVENT" ? "05" : "04";

  const fairForm = (
    <form
      ref={formRef}
      className="registration-form fair-registration-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        validateAndSave(event.currentTarget);
      }}
      onInput={(event) => (event.target as HTMLElement).removeAttribute("aria-invalid")}
    >
      <div className="fair-registration-layout">
        <section className="registration-section">
          <div className="registration-section-heading">
            <span>01</span>
            <div className="admin-section-heading-with-help">
              <h2>Identidad de la publicación</h2>
              <AyudaContextual
                id="publish-kind-general"
                activeId={activeHelpPanel}
                title="Identidad de la publicación"
                content="Elija feria para una presentación clásica o evento para activar una experiencia visual más inmersiva."
                onToggle={toggleHelpPanel}
              />
            </div>
          </div>
          <div className="registration-grid fair-registration-grid-single">
            <div className="fair-type-grid">
              {FAIR_TYPE_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`fair-type-card${draft.tipo === option.value ? " is-selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="tipo"
                    value={option.value}
                    checked={draft.tipo === option.value}
                    onChange={() => {
                      setDraft((current) => ({
                        ...current,
                        tipo: option.value,
                        departamento:
                          option.value === "FAIR"
                            ? current.departamento || current.departamentos[0] || ""
                            : current.departamento,
                        departamentos:
                          option.value === "EVENT" && !current.departamentos.length && current.departamento
                            ? [current.departamento]
                            : current.departamentos,
                        animaciones_tema:
                          option.value === "EVENT"
                            ? current.animaciones_tema.length
                              ? current.animaciones_tema
                              : ["FLOAT"]
                            : current.animaciones_tema,
                        ...(option.value === "EVENT" &&
                        !current.color_primario &&
                        !current.color_secundario &&
                        !current.color_terciario
                          ? defaultEventPalette
                          : {}),
                      }));
                    }}
                  />
                  <div className="admin-option-row">
                    <strong>{option.label}</strong>
                    <AyudaContextual
                      id={option.helpId}
                      activeId={activeHelpPanel}
                      title={option.label}
                      content={option.helpText}
                      onToggle={toggleHelpPanel}
                    />
                  </div>
                  <span>{option.teaser}</span>
                </label>
              ))}
            </div>
            <Campo label={draft.tipo === "EVENT" ? "Nombre del evento" : "Nombre de la feria"} required>
              <input
                className="input"
                name="nombre"
                required
                placeholder={
                  draft.tipo === "EVENT"
                    ? "Ej.: Encuentro Nacional de Innovación Productiva"
                    : "Ej.: Feria Productiva Nacional"
                }
                value={draft.nombre}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, nombre: event.target.value }))
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
                onChange={(event) =>
                  setDraft((current) => ({ ...current, descripcion: event.target.value }))
                }
              />
            </Campo>
          </div>
        </section>

        {draft.tipo === "EVENT" && (
          <section className="registration-section">
            <div className="registration-section-heading">
              <span>02</span>
              <div className="admin-section-heading-with-help">
                <h2>Tema visual del evento</h2>
                <AyudaContextual
                  id="palette-recommendation"
                  activeId={activeHelpPanel}
                  title="Tema visual"
                  content="Ajusta manualmente la paleta y las animaciones del evento para construir una identidad visual propia."
                  onToggle={toggleHelpPanel}
                />
              </div>
            </div>
            <div className="registration-grid fair-registration-grid-single">
              <div
                className={`event-theme-preview ${animationPreviewClass(draft.animaciones_tema[0])}`.trim()}
                style={{
                  background: `linear-gradient(135deg, ${draft.color_primario}, ${draft.color_secundario}, ${draft.color_terciario})`,
                }}
              >
                <div className="event-theme-preview-copy">
                  <span className="event-theme-preview-badge">
                    <Sparkles size={16} />
                    Evento temático
                  </span>
                  <strong>{draft.nombre || "Vista previa del evento"}</strong>
                  <small>
                    Animacion activa:{" "}
                    {draft.animaciones_tema.length ? animationLabel(draft.animaciones_tema[0]) : "ninguna"}
                  </small>
                </div>
              </div>

              <div className="event-recommendation-card">
                <div className="event-recommendation-copy">
                  <strong>Personalizacion del evento</strong>
                  <p>Define tus colores y elige una sola animacion. La vista previa te ayuda a validar el resultado antes de guardar.</p>
                </div>
                <AyudaContextual
                  id="palette"
                  activeId={activeHelpPanel}
                  title="Personalizacion"
                  content="Puedes definir tu propia paleta y elegir una animacion para adaptar el evento a cada ocasion especial."
                  onToggle={toggleHelpPanel}
                />
              </div>

              <div className="event-color-grid">
                <div className="event-color-card">
                  <div className="admin-option-row">
                    <span className="event-color-card-title">Color principal</span>
                    <AyudaContextual
                      id="color-primary"
                      activeId={activeHelpPanel}
                      title="Color principal"
                      content="Es el color base del evento y desde aquí se sugiere el resto de la paleta."
                      onToggle={toggleHelpPanel}
                    />
                  </div>
                  <label
                    className="event-color-swatch"
                    style={{ background: draft.color_primario }}
                    aria-label="Color principal"
                  >
                    <input
                      className="event-color-picker"
                      type="color"
                      name="color_primario"
                      required
                      disabled={false}
                      value={draft.color_primario}
                      onChange={(event) => handlePrimaryColorChange(event.target.value)}
                    />
                  </label>
                  <strong>{draft.color_primario}</strong>
                </div>

                <div className="event-color-card">
                  <div className="admin-option-row">
                    <span className="event-color-card-title">Color de apoyo 1</span>
                    <AyudaContextual
                      id="color-secondary"
                      activeId={activeHelpPanel}
                      title="Color de apoyo 1"
                      content="Refuerza la transición del degradado y aporta variación al fondo."
                      onToggle={toggleHelpPanel}
                    />
                  </div>
                  <label
                    className="event-color-swatch"
                    style={{ background: draft.color_secundario }}
                    aria-label="Color de apoyo 1"
                  >
                    <input
                      className="event-color-picker"
                      type="color"
                      name="color_secundario"
                      required
                      disabled={false}
                      value={draft.color_secundario}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, color_secundario: event.target.value }))
                      }
                    />
                  </label>
                  <strong>{draft.color_secundario}</strong>
                </div>

                <div className="event-color-card">
                  <div className="admin-option-row">
                    <span className="event-color-card-title">Color de apoyo 2</span>
                    <AyudaContextual
                      id="color-tertiary"
                      activeId={activeHelpPanel}
                      title="Color de apoyo 2"
                      content="Cierra la paleta y ayuda a dar profundidad al conjunto visual del evento."
                      onToggle={toggleHelpPanel}
                    />
                  </div>
                  <label
                    className="event-color-swatch"
                    style={{ background: draft.color_terciario }}
                    aria-label="Color de apoyo 2"
                  >
                    <input
                      className="event-color-picker"
                      type="color"
                      name="color_terciario"
                      required
                      disabled={false}
                      value={draft.color_terciario}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, color_terciario: event.target.value }))
                      }
                    />
                  </label>
                  <strong>{draft.color_terciario}</strong>
                </div>
              </div>

              <div className="event-theme-swatches">
                {[draft.color_primario, draft.color_secundario, draft.color_terciario].map((color) => (
                  <span key={color} style={{ background: color }} title={color} />
                ))}
              </div>

              <Campo label="Animacion del evento" required>
                <div className="event-animation-grid">
                  {EVENT_ANIMATION_OPTIONS.map((option) => {
                    const selected = draft.animaciones_tema[0] === option.value;
                    return (
                      <label
                        key={option.value}
                        className={`event-animation-card${selected ? " is-selected" : ""}`}
                      >
                        <input
                          type="radio"
                          name="animaciones_tema"
                          checked={selected}
                          onChange={() => toggleAnimation(option.value)}
                        />
                        <div className="admin-option-row">
                          <strong>{option.label}</strong>
                          <AyudaContextual
                            id={option.helpId}
                            activeId={activeHelpPanel}
                            title={option.label}
                            content={option.helpText}
                            onToggle={toggleHelpPanel}
                          />
                        </div>
                        <span>{option.teaser}</span>
                      </label>
                    );
                  })}
                </div>
              </Campo>
            </div>
          </section>
        )}

        <section className="registration-section">
          <div className="registration-section-heading">
            <span>{coverStep}</span>
            <div>
              <h2>Portada</h2>
              <p>Seleccione la imagen principal de presentación de la {entityLabel}.</p>
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
                  <img src={coverPreview} alt="Vista previa completa de la portada" />
                </button>
              ) : (
                <div className="fair-cover-preview-card fair-cover-preview-card-small fair-cover-preview-empty">
                  <span>Sin imagen</span>
                </div>
              )}
              <Campo
                label="Imagen de portada"
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
                    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
                      event.target.value = "";
                      feedback.error("Archivo no válido", "Seleccione una imagen JPG, PNG o WebP.");
                      return;
                    }
                    if (file.size > 10 * 1024 * 1024) {
                      event.target.value = "";
                      feedback.error("Imagen demasiado grande", "La portada no puede superar los 10 MB.");
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
            <span>{locationStep}</span>
            <div>
              <h2>Ubicación</h2>
              <p>Lugar físico y localización administrativa de la {entityLabel}.</p>
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
                onChange={(event) =>
                  setDraft((current) => ({ ...current, ubicacion: event.target.value }))
                }
              />
            </Campo>
            {draft.tipo === "EVENT" ? (
              <Campo
                label="Departamentos"
                required
                hint="Puede seleccionar uno, varios o todos los departamentos."
              >
                <div className="event-departments-selector">
                  <label className="event-department-option event-department-option-all">
                    <input
                      type="checkbox"
                      name="departamentos"
                      checked={draft.departamentos.length === BOLIVIA_DEPARTMENTS.length}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          departamentos: event.target.checked ? [...BOLIVIA_DEPARTMENTS] : [],
                        }))
                      }
                    />
                    <strong>Todos los departamentos</strong>
                  </label>
                  <div className="event-departments-grid">
                    {BOLIVIA_DEPARTMENTS.map((item) => (
                      <label key={item} className="event-department-option">
                        <input
                          type="checkbox"
                          name="departamentos"
                          checked={draft.departamentos.includes(item)}
                          onChange={() =>
                            setDraft((current) => ({
                              ...current,
                              departamentos: current.departamentos.includes(item)
                                ? current.departamentos.filter((department) => department !== item)
                                : [...current.departamentos, item],
                            }))
                          }
                        />
                        <span>{item}</span>
                      </label>
                    ))}
                  </div>
                  <small className="event-departments-count">
                    {draft.departamentos.length
                      ? `${draft.departamentos.length} de ${BOLIVIA_DEPARTMENTS.length} seleccionados`
                      : "Ningún departamento seleccionado"}
                  </small>
                </div>
              </Campo>
            ) : (
              <Campo label="Departamento" required>
                <select
                  className="input"
                  name="departamento"
                  required
                  value={draft.departamento}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, departamento: event.target.value }))
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
            )}
          </div>
        </section>

        <section className="registration-section">
          <div className="registration-section-heading">
            <span>{datesStep}</span>
            <div>
              <h2>Fechas</h2>
              <p>Defina el período en el que la {entityLabel} estará vigente.</p>
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
                onChange={(event) =>
                  setDraft((current) => ({ ...current, fecha_inicio: event.target.value }))
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
                onChange={(event) =>
                  setDraft((current) => ({ ...current, fecha_fin: event.target.value }))
                }
              />
            </Campo>
          </div>
        </section>
      </div>
      <footer className="registration-actions">
        <span>Revise los datos antes de guardar la {entityLabel}.</span>
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
                : draft.tipo === "EVENT"
                  ? "Crear evento"
                  : "Crear feria"}
          </button>
        </div>
      </footer>
    </form>
  );

  const coverPreviewModal = showCoverPreview && coverPreview && (
    <Modal
      title="Vista previa de la portada"
      onClose={() => setShowCoverPreview(false)}
      wide
      className="image-preview-dialog fair-cover-preview-dialog"
    >
      <img src={coverPreview} alt="Imagen de portada completa" />
      <div className="modal-actions">
        <button type="button" className="btn" onClick={() => setShowCoverPreview(false)}>
          Cerrar
        </button>
      </div>
    </Modal>
  );

  if (creating || editing) {
    return (
      <section className="admin-unit-registration-page">
        <button type="button" className="back-navigation" onClick={closeForm}>
          ← Volver al listado
        </button>
        <div className="registration-intro">
          <div>
            <span className="eyebrow">
              {editing
                ? draft.tipo === "EVENT"
                  ? "Editar Evento"
                  : "Editar Feria"
                : "Registrar Feria o Evento"}
            </span>
            <h1>
              {editing
                ? draft.tipo === "EVENT"
                  ? "Editar Evento"
                  : "Editar Feria"
                : draft.tipo === "EVENT"
                  ? "Nuevo Evento"
                  : "Nueva Feria"}
            </h1>
          </div>
        </div>
        {fairForm}
        {coverPreviewModal}
      </section>
    );
  }

  return (
    <section className="admin-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Programación</span>
          <h1>Ferias y eventos</h1>
        </div>
        <button className="admin-units-create-button" onClick={() => open()}>
          <Plus aria-hidden="true" />
          Nueva feria o evento
        </button>
      </div>
      <div className="toolbar admin-requests-toolbar admin-fairs-toolbar">
        <CampoBusqueda
          value={q}
          onChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          placeholder="Buscar nombre o lugar..."
        />
        <SelectorBuscable
          value={estado}
          options={FAIR_STATUS_OPTIONS}
          onChange={(value) => {
            setEstado(value);
            setPage(1);
          }}
          placeholder="Todos los estados"
          searchPlaceholder="Buscar estado..."
          ariaLabel="Filtrar por estado"
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
      </div>
      {list.isLoading ? (
        <EstadoCarga />
      ) : list.error ? (
        <CajaError mensaje={mensaje(list.error)} />
      ) : !data.items.length ? (
        <EstadoVacio title="No hay ferias ni eventos" />
      ) : (
        <>
          <div className="table-wrap admin-requests-table">
            <table>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Nombre</th>
                  <th>Lugar</th>
                  <th>
                    <button
                      type="button"
                      className="admin-table-sort-button"
                      onClick={() => {
                        setSortDir((current) => (current === "asc" ? "desc" : "asc"));
                        setPage(1);
                      }}
                      aria-label={`Ordenar por fecha de inicio ${sortDir === "asc" ? "descendente" : "ascendente"}`}
                      title={`Ordenar por fecha de inicio ${sortDir === "asc" ? "descendente" : "ascendente"}`}
                    >
                      Fechas
                      <ArrowDownUp size={15} />
                    </button>
                  </th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((fair) => (
                  <tr key={fair.id}>
                    <td>
                      <span className={`admin-kind-badge admin-kind-badge-${fair.tipo.toLowerCase()}`}>
                        {badgeLabel(fair.tipo)}
                      </span>
                    </td>
                    <td>
                      <strong>{fair.nombre}</strong>
                      <small>{fair.departamento}</small>
                    </td>
                    <td>{fair.ubicacion}</td>
                    <td>
                      {fair.fecha_inicio} — {fair.fecha_fin}
                    </td>
                    <td>
                      <InsigniaEstado value={fair.estado} />
                    </td>
                    <td>
                      <div className="admin-admins-actions">
                        <button
                          className="btn-small admin-sector-action-edit"
                          disabled={["FINISHED", "DISABLED"].includes(fair.estado)}
                          onClick={() => open(fair)}
                          aria-label={`Editar ${fair.nombre}`}
                          title="Editar"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="btn-small admin-fair-action-manage"
                          onClick={() => navigate(`/admin/ferias/${fair.id}/participaciones`)}
                          aria-label={`Gestionar participaciones de ${fair.nombre}`}
                          title="Participaciones"
                        >
                          <Users size={16} />
                        </button>
                        {!["FINISHED", "DISABLED"].includes(fair.estado) && (
                          <>
                            <BotonConfirmacion
                              className="btn-small admin-fair-action-manage"
                              question={`¿Finalizar ${fair.tipo === "EVENT" ? "este evento" : "esta feria"}?`}
                              onConfirm={async () => {
                                await api.post(`/admin/fairs/${fair.id}/finish`);
                                await qc.invalidateQueries({ queryKey: ["canonical-fairs"] });
                              }}
                              confirmLabel="Finalizar"
                              title="Finalizar"
                            >
                              <CalendarCheck2 size={16} />
                            </BotonConfirmacion>
                            <BotonConfirmacion
                              question={`¿Deshabilitar ${fair.tipo === "EVENT" ? "este evento" : "esta feria"}?`}
                              onConfirm={async () => {
                                await api.post(`/admin/fairs/${fair.id}/disable`);
                                await qc.invalidateQueries({ queryKey: ["canonical-fairs"] });
                              }}
                              confirmLabel="Deshabilitar"
                              title="Deshabilitar"
                            >
                              <Ban size={16} />
                            </BotonConfirmacion>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <BarraPaginacion pagination={data.pagination} onPageChange={setPage} />
        </>
      )}
      {coverPreviewModal}
    </section>
  );
}
