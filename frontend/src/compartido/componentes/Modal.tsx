import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import type { CSSProperties, ReactNode } from "react";

const openModalStack: HTMLElement[] = [];

export function Modal({
  title,
  children,
  onClose,
  wide = false,
  className = "",
  hideHeader = false,
  style,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  className?: string;
  hideHeader?: boolean;
  style?: CSSProperties;
}) {
  const dialog = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  const titleId = useId();
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialogElement = dialog.current;
    dialogElement?.focus();
    if (dialogElement) openModalStack.push(dialogElement);
    document.body.classList.add("modal-open");
    const handleKeyboard = (event: KeyboardEvent) => {
      if (openModalStack.at(-1) !== dialogElement) return;
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogElement) return;
      const focusable = [
        ...dialogElement.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ].filter((element) => !element.hasAttribute("hidden"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyboard);
    return () => {
      document.removeEventListener("keydown", handleKeyboard);
      const index = dialogElement
        ? openModalStack.lastIndexOf(dialogElement)
        : -1;
      if (index >= 0) openModalStack.splice(index, 1);
      if (!openModalStack.length) document.body.classList.remove("modal-open");
      previous?.focus();
    };
  }, []);
  return createPortal(
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        ref={dialog}
        tabIndex={-1}
        className={`modal ${wide ? "modal-wide" : ""} ${hideHeader ? "modal-headerless" : ""} ${className}`.trim()}
        style={style}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        {hideHeader ? (
          <>
            <h2 id={titleId} className="sr-only">
              {title}
            </h2>
            <button
              className="modal-floating-close"
              onClick={onClose}
              aria-label="Cerrar"
            >
              <X />
            </button>
          </>
        ) : (
          <header className="modal-header">
            <h2 id={titleId}>{title}</h2>
            <button onClick={onClose} aria-label="Cerrar">
              <X />
            </button>
          </header>
        )}
        {children}
      </section>
    </div>,
    document.body,
  );
}


