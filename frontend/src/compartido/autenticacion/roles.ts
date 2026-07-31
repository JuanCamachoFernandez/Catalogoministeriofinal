export const ROLES_USUARIO = {
  ADMIN: "ADMIN",
  PRODUCTIVE_UNIT_RESPONSIBLE: "PRODUCTIVE_UNIT_RESPONSIBLE",
} as const;

export type UserRole = (typeof ROLES_USUARIO)[keyof typeof ROLES_USUARIO];

export const ROLES_ADMINISTRACION = [
  ROLES_USUARIO.ADMIN,
] as const satisfies readonly UserRole[];

export const ROLES_UNIDAD_PRODUCTIVA = [
  ROLES_USUARIO.PRODUCTIVE_UNIT_RESPONSIBLE,
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
  "administrator-accounts": ROLES_ADMINISTRACION,
  reports: ROLES_ADMINISTRACION,
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
