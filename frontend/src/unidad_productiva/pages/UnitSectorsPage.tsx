import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Check,
  Factory,
  Footprints,
  Gem,
  Hammer,
  Layers3,
  Save,
  Shapes,
  Shirt,
  Sparkles,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import { apiError, type ProductiveSector } from "../../api";
import { ErrorBox, Loading, useFeedback } from "../../ui";
import { productiveUnitApi } from "../services/productiveUnitApi";

const clean = (value: string) => value.trim() || null;

function sectorIcon(name: string): LucideIcon {
  const normalized = name.toLowerCase();
  if (normalized.includes("alimento")) return Utensils;
  if (normalized.includes("artesanía")) return Shapes;
  if (normalized.includes("cosmética")) return Sparkles;
  if (normalized.includes("cuero") || normalized.includes("calzado"))
    return Footprints;
  if (normalized.includes("madera") || normalized.includes("carpintería"))
    return Hammer;
  if (normalized.includes("orfebrería") || normalized.includes("joyería"))
    return Gem;
  if (normalized.includes("textil") || normalized.includes("confecciones"))
    return Shirt;
  return Factory;
}

export function UnitSectorsPage() {
  const queryClient = useQueryClient();
  const feedback = useFeedback();
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const available = useQuery({
    queryKey: ["productive-sectors", "active"],
    queryFn: productiveUnitApi.getAvailableSectors,
  });
  const own = useQuery({
    queryKey: ["productive-unit-sectors"],
    queryFn: productiveUnitApi.getOwnSectors,
  });

  const effective = Object.keys(selected).length
    ? selected
    : Object.fromEntries(
        (own.data ?? []).map((sector) => [
          sector.id,
          sector.detalle_otro ?? "",
        ]),
      );

  const toggle = (sector: ProductiveSector) => {
    setSelected((current) => {
      const next = Object.keys(current).length
        ? { ...current }
        : Object.fromEntries(
            (own.data ?? []).map((item) => [item.id, item.detalle_otro ?? ""]),
          );
      if (sector.id in next) delete next[sector.id];
      else next[sector.id] = "";
      return next;
    });
  };

  const save = async () => {
    const selectedOther = available.data?.find(
      (sector) => sector.es_otro && sector.id in effective,
    );
    if (selectedOther && !effective[selectedOther.id]?.trim()) {
      feedback.error(
        "Detalle requerido",
        "Describa su actividad productiva en el sector Otros.",
      );
      return;
    }
    setSaving(true);
    try {
      await productiveUnitApi.updateSectors(
        Object.entries(effective).map(
          ([productive_sector_id, detalle_otro]) => ({
            productive_sector_id,
            detalle_otro: clean(detalle_otro),
          }),
        ),
      );
      setSelected({});
      await queryClient.invalidateQueries({
        queryKey: ["productive-unit-sectors"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["productive-unit-profile"],
      });
      feedback.success(
        "Sectores actualizados",
        "La clasificación de la Unidad Productiva fue guardada.",
      );
    } catch (error) {
      feedback.error("No se pudieron guardar", apiError(error));
    } finally {
      setSaving(false);
    }
  };

  if (available.isLoading || own.isLoading) return <Loading />;
  if (available.error || own.error) {
    return <ErrorBox message={apiError(available.error ?? own.error)} />;
  }

  const selectedCount = Object.keys(effective).length;
  const selectedOther = available.data?.find(
    (sector) => sector.es_otro && sector.id in effective,
  );
  const otherNeedsDetail = Boolean(
    selectedOther && !effective[selectedOther.id]?.trim(),
  );

  return (
    <section className="unit-sectors-page">
      <header className="unit-sectors-hero">
        <div className="unit-sectors-hero-copy">
          <span className="unit-sectors-hero-icon">
            <Layers3 size={28} />
          </span>
          <div>
            <span className="unit-sectors-kicker">CLASIFICACIÓN</span>
            <h1>Mis Sectores Productivos</h1>
            <p>
              Seleccione las actividades que representan el trabajo de su unidad
              productiva.
            </p>
          </div>
        </div>
      </header>

      <section className="unit-sectors-panel">
        <div className="unit-sectors-panel-heading">
          <div>
            <span>ACTIVIDADES PRODUCTIVAS</span>
            <h2>Seleccione uno o varios sectores</h2>
          </div>
          <small>Debe elegir al menos uno</small>
        </div>
        <div className="unit-sectors-grid">
          {available.data?.map((sector) => (
            <div
              key={sector.id}
              className={`unit-sector-option ${sector.id in effective ? "is-selected" : ""} ${sector.es_otro ? "is-other" : ""}`}
            >
              <label className="unit-sector-option-main">
                <input
                  type="checkbox"
                  checked={sector.id in effective}
                  onChange={() => toggle(sector)}
                />
                <span className="unit-sector-option-icon">
                  {(() => {
                    const Icon = sectorIcon(sector.nombre);
                    return <Icon size={23} />;
                  })()}
                </span>
                <span className="unit-sector-option-copy">
                  <strong>{sector.nombre}</strong>
                  <small>
                    {sector.id in effective
                      ? "Sector seleccionado"
                      : "Presione para seleccionar"}
                  </small>
                </span>
                <span className="unit-sector-check">
                  {sector.id in effective && (
                    <Check size={16} strokeWidth={3} />
                  )}
                </span>
              </label>
              {sector.es_otro && sector.id in effective && (
                <div className="unit-sector-other-detail">
                  <label htmlFor={`sector-detail-${sector.id}`}>
                    Describa su actividad productiva <strong>*</strong>
                  </label>
                  <textarea
                    id={`sector-detail-${sector.id}`}
                    className={`input ${otherNeedsDetail ? "input-error" : ""}`}
                    required
                    rows={3}
                    maxLength={255}
                    placeholder="Ej.: Elaboración de instrumentos musicales artesanales"
                    value={effective[sector.id]}
                    onChange={(event) =>
                      setSelected((current) => ({
                        ...effective,
                        ...current,
                        [sector.id]: event.target.value,
                      }))
                    }
                  />
                  <small>
                    Explique brevemente la actividad que no aparece en la lista.
                  </small>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <footer className="unit-sectors-footer">
        <div>
          <span className="unit-sectors-footer-icon">
            <Check size={18} />
          </span>
          <p>
            <strong>
              {selectedCount || "Ningún"}{" "}
              {selectedCount === 1
                ? "sector seleccionado"
                : "sectores seleccionados"}
            </strong>
            <small>Esta clasificación se mostrará en su perfil público.</small>
          </p>
        </div>
        <button
          className="unit-sectors-save-button"
          disabled={!selectedCount || otherNeedsDetail || saving}
          onClick={() => void save()}
        >
          <Save size={18} />
          {saving ? "Guardando…" : "Guardar sectores"}
        </button>
      </footer>
    </section>
  );
}
