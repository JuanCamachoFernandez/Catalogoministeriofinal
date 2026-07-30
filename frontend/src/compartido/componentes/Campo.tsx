import { X } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

const FIELD_HELP_OPEN_EVENT = "catalog:field-help-open";

export function Campo({
  label,
  children,
  hint,
  hintAsHelp = false,
  required = false,
  optional = false,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  hintAsHelp?: boolean;
  required?: boolean;
  optional?: boolean;
}) {
  const [helpOpen, setHelpOpen] = useState(false);
  const helpId = useId();
  const helpContainer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeWhenAnotherHelpOpens = (event: Event) => {
      if ((event as CustomEvent<string>).detail !== helpId) {
        setHelpOpen(false);
      }
    };
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (
        helpOpen &&
        event.target instanceof Node &&
        !helpContainer.current?.contains(event.target)
      ) {
        setHelpOpen(false);
      }
    };

    window.addEventListener(FIELD_HELP_OPEN_EVENT, closeWhenAnotherHelpOpens);
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => {
      window.removeEventListener(
        FIELD_HELP_OPEN_EVENT,
        closeWhenAnotherHelpOpens,
      );
      document.removeEventListener("pointerdown", closeOnOutsideClick);
    };
  }, [helpId, helpOpen]);

  const toggleHelp = () => {
    if (!helpOpen) {
      window.dispatchEvent(
        new CustomEvent<string>(FIELD_HELP_OPEN_EVENT, { detail: helpId }),
      );
    }
    setHelpOpen((current) => !current);
  };

  const labelContent = (
    <>
      {label}
      {required && (
        <>
          <b className="field-required" aria-hidden="true">
            *
          </b>
          <span className="sr-only"> (obligatorio)</span>
        </>
      )}
      {optional && (
        <small className="field-optional">Dejar vacío si no se tiene</small>
      )}
    </>
  );

  if (hint && hintAsHelp) {
    return (
      <div ref={helpContainer} className="field field-with-help">
        <span className="field-label-row">{labelContent}</span>
        {children}
        <div className="field-help-control">
          <button
            type="button"
            className="field-help-button"
            aria-label="Mostrar ayuda"
            title={`Ayuda para ${label}`}
            aria-expanded={helpOpen}
            onClick={toggleHelp}
          >
            <span aria-hidden="true">?</span>
            Ayuda
          </button>
        </div>
        {helpOpen && (
          <div
            className="field-help-card"
            role="dialog"
            aria-label={`Ayuda para ${label}`}
          >
            <div className="field-help-card-header">
              <strong>{label}</strong>
              <button
                type="button"
                aria-label="Cerrar ayuda"
                onClick={() => setHelpOpen(false)}
              >
                <X size={16} />
              </button>
            </div>
            <p>{hint}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <label className="field">
      <span className="field-label-row">{labelContent}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

