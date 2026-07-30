import type { ReactNode } from "react";
import { useRetroalimentacion } from "./Retroalimentacion";

export function BotonConfirmacion({
  children,
  question,
  onConfirm,
  className = "btn-danger",
  disabled = false,
  title,
  confirmDialogTitle = "Confirmar acción",
  confirmLabel = "Sí, continuar",
}: {
  children: ReactNode;
  question: string;
  onConfirm: () => void;
  className?: string;
  disabled?: boolean;
  title?: string;
  confirmDialogTitle?: string;
  confirmLabel?: string;
}) {
  const feedback = useRetroalimentacion();
  return (
    <button
      type="button"
      disabled={disabled}
      title={title}
      className={className}
      onClick={async () => {
        const confirmed = await feedback.confirm({
          title: confirmDialogTitle,
          mensaje: question,
          confirmLabel,
          danger: className.includes("danger"),
        });
        if (confirmed) onConfirm();
      }}
    >
      {children}
    </button>
  );
}


