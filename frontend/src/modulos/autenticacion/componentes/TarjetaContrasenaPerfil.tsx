import { Eye, EyeOff, KeyRound, Save } from "lucide-react";
import { useState } from "react";
import { api, errorApi } from "../../../compartido";
import { useAutenticacion } from "../contexto/ContextoAutenticacion";
import { esContrasenaSegura } from "../../../compartido/validaciones/contrasena";
import { Campo, useRetroalimentacion } from "../../../compartido/componentes";

function SecureInput({
  label,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password";
}) {
  const [visible, setVisible] = useState(false);
  return <Campo label={label}>
    <span className="password-input">
      <input
        className="input"
        type={visible ? "text" : "password"}
        value={value}
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}>
        {visible ? <EyeOff/> : <Eye/>}
      </button>
    </span>
  </Campo>;
}

export function TarjetaContrasenaPerfil() {
  const feedback = useRetroalimentacion();
  const { refresh } = useAutenticacion();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!currentPassword) {
      feedback.error("Falta la contraseña actual", "Ingrese su contraseña actual para confirmar el cambio.");
      return;
    }
    if (newPassword !== confirmation) {
      feedback.error("Las contraseñas no coinciden", "Vuelva a escribir la misma contraseña nueva en ambos campos.");
      return;
    }
    if (!esContrasenaSegura(newPassword)) {
      feedback.error("Contraseña poco segura", "Use al menos 10 caracteres, mayúscula, minúscula, número y símbolo.");
      return;
    }
    setPending(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      await refresh();
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      feedback.success("Contraseña actualizada", "Su nueva contraseña fue guardada correctamente.");
    } catch (reason) {
      feedback.error("No se pudo cambiar la contraseña", errorApi(reason, "Revise la contraseña actual e inténtelo nuevamente."));
    } finally {
      setPending(false);
    }
  };

  return <section className="panel profile-password-panel">
    <div className="profile-security-heading">
      <span><KeyRound/></span>
      <div><h2>Seguridad de la cuenta</h2><p>Cambie su contraseña confirmando primero la contraseña actual.</p></div>
    </div>
    <form className="profile-password-form" onSubmit={submit} noValidate>
      <SecureInput label="Contraseña actual" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password"/>
      <SecureInput label="Nueva contraseña" value={newPassword} onChange={setNewPassword} autoComplete="new-password"/>
      <SecureInput label="Confirmar nueva contraseña" value={confirmation} onChange={setConfirmation} autoComplete="new-password"/>
      <p className="form-hint full">Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo. No puede reutilizar la contraseña actual.</p>
      <div className="profile-password-action full"><button className="admin-unit-action-button admin-profile-primary-button" disabled={pending}><Save/>{pending ? "Guardando…" : "Guardar nueva contraseña"}</button></div>
    </form>
  </section>;
}
