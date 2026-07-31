from ..modelos import Role

ROLES_ADMINISTRACION_INSTITUCIONAL = (Role.ADMIN,)
ROLES_ADMINISTRACION_CUENTAS = (Role.ADMIN,)
ROLES_ADMINISTRACION_COMPLETA = (Role.ADMIN,)
ROLES_RESPONSABLES_UNIDAD = (Role.PRODUCTIVE_UNIT_RESPONSIBLE,)
ROLES_GESTION_COMPARTIDA = (
    Role.ADMIN,
    Role.PRODUCTIVE_UNIT_RESPONSIBLE,
)


def tiene_permiso(usuario, politica) -> bool:
    return bool(usuario and usuario.role in politica)
