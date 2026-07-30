const ACTION_LABELS: Record<string, string> = {
  CREAR: "Crear",
  EDITAR: "Editar",
  ELIMINAR: "Eliminar",
  RESTAURAR: "Restaurar",
  CAMBIAR_ESTADO: "Cambiar estado",
  SINCRONIZAR_ESTADO: "Sincronizar estado",
  AGREGAR_IMAGEN: "Agregar imagen",
  EDITAR_IMAGEN: "Editar imagen",
  ELIMINAR_IMAGEN: "Eliminar imagen",
  ASIGNAR: "Asignar",
  AUTORIZAR: "Autorizar",
  REVOCAR: "Revocar",
  BLOQUEAR: "Bloquear cuenta",
  DESBLOQUEAR: "Desbloquear cuenta",
  INICIAR_SESION: "Iniciar sesión",
  CERRAR_SESION: "Cerrar sesión",
  REAUTENTICAR: "Desbloquear sesión",
  RENOVAR_SESION: "Renovar sesión",
  SESION_CADUCADA: "Sesión caducada",
  INTENTO_FALLIDO: "Intento de acceso fallido",
  CAMBIAR_CONTRASENA: "Cambiar contraseña",
  RESTABLECER_CONTRASENA: "Restablecer contraseña",
  ENVIAR_RECUPERACION: "Enviar recuperación de contraseña",
  INTENTO_RECUPERACION_FALLIDO: "Intento de recuperación fallido",
  CREAR_SOLICITUD: "Crear solicitud",
  APROBAR_SOLICITUD: "Aprobar solicitud",
  RECHAZAR_SOLICITUD: "Rechazar solicitud",
  ENVIAR_CREDENCIALES: "Enviar credenciales",
  REENVIAR_CREDENCIALES: "Reenviar credenciales",
  ENVIAR_RECHAZO: "Enviar notificación de rechazo",
  GENERAR_REPORTE: "Generar reporte",
};

const ENTITY_LABELS: Record<string, string> = {
  RegistrationRequest: "Solicitud de registro",
  ProductiveUnit: "Unidad Productiva",
  ProductiveSector: "Sector Productivo",
  FairParticipation: "Participación en feria",
  FeriaExpositor: "Participación de expositor",
  Fair: "Feria",
  Product: "Producto",
  Usuario: "Usuario",
  Perfil: "Perfil",
  Unidad: "Unidad administrativa",
  Categoria: "Categoría",
  Producto: "Producto",
  Feria: "Feria",
  Expositor: "Expositor",
  Reporte: "Reporte",
};

function readableFallback(value: string) {
  const text = value.replaceAll("_", " ").trim().toLocaleLowerCase("es");
  return text ? text.charAt(0).toLocaleUpperCase("es") + text.slice(1) : value;
}

export function etiquetaAccionAuditoria(value: string) {
  return ACTION_LABELS[value] ?? readableFallback(value);
}

export function etiquetaEntidadAuditoria(value: string) {
  return ENTITY_LABELS[value] ?? readableFallback(value);
}

export function etiquetaDescripcionAuditoria(value?: string | null) {
  if (!value) return "Operación registrada";
  let description = value
    .replace(/\bregistrationrequest\b/gi, "solicitud de registro")
    .replace(/\bproductiveunit\b/gi, "Unidad Productiva")
    .replace(/\bproductivesector\b/gi, "Sector Productivo")
    .replace(/\bfairparticipation\b/gi, "participación en feria")
    .replace(/\bferiaexpositor\b/gi, "participación de expositor");
  description = description
    .replace(/^Restaurar de /i, "Restauración de ")
    .replace(/^Crear solicitud de solicitud de registro$/i, "Creación de solicitud de registro")
    .replace(/^Aprobar solicitud de solicitud de registro$/i, "Aprobación de solicitud de registro")
    .replace(/^Rechazar solicitud de solicitud de registro$/i, "Rechazo de solicitud de registro")
    .replace(/^Intento recuperacion fallido de usuario$/i, "Intento de recuperación fallido de usuario")
    .replace(/^Enviar recuperacion de usuario$/i, "Envío de recuperación de contraseña de usuario")
    .replace(/\brecuperacion\b/gi, "recuperación")
    .replace(/\bpassword\b/gi, "contraseña")
    .replace(/\bsesion\b/gi, "sesión")
    .replace(/\bcreacion\b/gi, "creación")
    .replace(/\bedicion\b/gi, "edición")
    .replace(/\beliminacion\b/gi, "eliminación")
    .replace(/\brestauracion\b/gi, "restauración")
    .replace(/\bnotificacion\b/gi, "notificación");
  return description;
}

export const accionesAuditoriaPositivas = new Set([
  "CREAR",
  "RESTAURAR",
  "AGREGAR_IMAGEN",
  "AUTORIZAR",
  "DESBLOQUEAR",
  "APROBAR_SOLICITUD",
  "CREAR_SOLICITUD",
]);

export const accionesAuditoriaAdvertencia = new Set([
  "EDITAR",
  "CAMBIAR_ESTADO",
  "SINCRONIZAR_ESTADO",
  "EDITAR_IMAGEN",
  "ASIGNAR",
  "CAMBIAR_CONTRASENA",
  "RESTABLECER_CONTRASENA",
  "ENVIAR_RECUPERACION",
  "ENVIAR_CREDENCIALES",
  "REENVIAR_CREDENCIALES",
  "GENERAR_REPORTE",
]);

export const accionesAuditoriaNegativas = new Set([
  "ELIMINAR",
  "ELIMINAR_IMAGEN",
  "REVOCAR",
  "BLOQUEAR",
  "INTENTO_FALLIDO",
  "INTENTO_RECUPERACION_FALLIDO",
  "RECHAZAR_SOLICITUD",
  "ENVIAR_RECHAZO",
]);
