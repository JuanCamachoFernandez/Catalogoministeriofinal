export const ROLES_USUARIO = {
  SUPERADMIN: "SUPERADMIN",
  ADMIN_VICEMINISTERIO: "ADMIN_VICEMINISTERIO",
  ADMIN: "ADMIN",
  PRODUCTIVE_UNIT_RESPONSIBLE: "PRODUCTIVE_UNIT_RESPONSIBLE",
  EXPOSITOR: "EXPOSITOR",
} as const;

export type UserRole = (typeof ROLES_USUARIO)[keyof typeof ROLES_USUARIO];

export const ROLES_ADMINISTRACION = [
  ROLES_USUARIO.SUPERADMIN,
  ROLES_USUARIO.ADMIN_VICEMINISTERIO,
  ROLES_USUARIO.ADMIN,
] as const satisfies readonly UserRole[];

export const ROLES_UNIDAD_PRODUCTIVA = [
  ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE,
  ROLES_USUARIO.EXPOSITOR,
] as const satisfies readonly UserRole[];

export type FuncionAdministracion =
  | "dashboard"
  | "registration-requests"
  | "productive-units"
  | "productive-sectors"
  | "products"
  | "fairs"
  | "audit"
  | "administrator-accounts"
  | "reports";

const ROLES_POR_FUNCION_ADMINISTRACION: Record<
  FuncionAdministracion,
  readonly UserRole[]
> = {
  dashboard: ROLES_ADMINISTRACION,
  "registration-requests": ROLES_ADMINISTRACION,
  "productive-units": ROLES_ADMINISTRACION,
  "productive-sectors": ROLES_ADMINISTRACION,
  products: ROLES_ADMINISTRACION,
  fairs: ROLES_ADMINISTRACION,
  audit: ROLES_ADMINISTRACION,
  "administrator-accounts": [
    ROLES_USUARIO.SUPERADMIN,
    ROLES_USUARIO.ADMIN,
  ],
  reports: [ROLES_USUARIO.SUPERADMIN, ROLES_USUARIO.ADMIN_VICEMINISTERIO],
};

export function tieneRol(
  role: UserRole | null | undefined,
  allowed: readonly UserRole[],
) {
  return Boolean(role && allowed.includes(role));
}

export function esRolAdministracion(role: UserRole | null | undefined) {
  return tieneRol(role, ROLES_ADMINISTRACION);
}

export function esRolUnidadProductiva(role: UserRole | null | undefined) {
  return tieneRol(role, ROLES_UNIDAD_PRODUCTIVA);
}

export function puedeAccederFuncionAdministracion(
  role: UserRole | null | undefined,
  funcion: FuncionAdministracion,
) {
  return tieneRol(role, ROLES_POR_FUNCION_ADMINISTRACION[funcion]);
}

export function rolesParaFuncionAdministracion(funcion: FuncionAdministracion) {
  return ROLES_POR_FUNCION_ADMINISTRACION[funcion];
}

export function inicioParaRol(role: UserRole) {
  return esRolUnidadProductiva(role)
    ? "/unidad-productiva/productos"
    : "/admin";
}

export function rolCanonicoPara(role: UserRole) {
  if (role === ROLES_USUARIO.EXPOSITOR) {
    return ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE;
  }
  if (
    role === ROLES_USUARIO.SUPERADMIN ||
    role === ROLES_USUARIO.ADMIN_VICEMINISTERIO
  ) {
    return ROLES_USUARIO.ADMIN;
  }
  return role;
}
