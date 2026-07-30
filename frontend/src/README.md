# Arquitectura del frontend

## Estructura

- `aplicacion/`: composición global, diseños, proveedores y rutas.
- `modulos/`: páginas, componentes, servicios, tipos y estilos de cada dominio.
- `compartido/`: elementos utilizados realmente por dos o más módulos.

Los módulos vigentes son `administracion`, `autenticacion`, `catalogo-publico`,
`registro`, `reportes` y `unidad-productiva`. No existen implementaciones activas
en las antiguas carpetas `admin`, `portal_publico`, `unidad_productiva`, `modules`
o `shared`.

## Reglas de ubicación

- Páginas navegables: `modulos/<dominio>/paginas`.
- Componentes exclusivos: `modulos/<dominio>/componentes`.
- Servicios HTTP de dominio: `modulos/<dominio>/servicios`.
- Componentes genéricos: `compartido/componentes`.
- Cliente Axios y servicios transversales: `compartido/servicios`.
- Contratos HTTP globales: `compartido/tipos/contratos.ts`.
- Estilos de dominio: `modulos/<dominio>/estilos`.
- Tema y base compatible: `compartido/estilos`.

`api.ts` y `ui.tsx` son las únicas fachadas históricas conservadas. Se mantienen
como API pública para pruebas y posibles consumidores externos; el código interno
usa directamente `compartido` y `compartido/componentes`.

## Rutas y roles

`aplicacion/rutas/EnrutadorAplicacion.tsx` compone las rutas públicas, de
autenticación, administración, Unidad Productiva y redirecciones anteriores.
Las políticas del frontend viven en `compartido/autenticacion/roles.ts`. Los
valores `SUPERADMIN`, `ADMIN_VICEMINISTERIO`, `ADMIN`,
`PRODUCTIVE_UNIT_RESPONSIBLE` y `EXPOSITOR` no se traducen porque forman parte
del contrato.

Para añadir un módulo, crear `modulos/<dominio>` y solo las subcarpetas que
necesite. Para añadir un rol, actualizar la matriz, la ruta inicial y sus pruebas.
El backend sigue siendo la autoridad final de permisos.

## Ejecutar el frontend

Desde `frontend/`:

```powershell
npm.cmd install
npm.cmd run dev
```

El backend compatible se inicia desde `backend/` con:

```powershell
.\.venv\Scripts\flask.exe --app app:create_app run
```

La conexión PostgreSQL, las migraciones y las semillas se documentan en
`backend/README.md`. El frontend no crea tablas ni sustituye a SQLAlchemy y debe
conservar los contratos JSON y endpoints actuales.

## Validación

```powershell
npm.cmd run lint
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e -- --project=chromium-desktop
```

`compartido/estilos/estilos-base.css` conserva selectores históricos de alcance
global para mantener el orden de cascada y el aspecto actual. Su extracción visual
debe hacerse con comparación de capturas, no mediante movimientos masivos.
