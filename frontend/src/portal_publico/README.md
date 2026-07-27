# Portal público

Este módulo contiene la interfaz pública activa del catálogo de ferias.

- `pages/`: páginas asociadas a las rutas públicas.
- `components/`: estructura visual e imágenes exclusivas del catálogo.
- `services/`: acceso a los endpoints públicos.
- `types.ts`: contratos exclusivos del portal.
- `utils.ts`: formato y utilidades de presentación.
- `index.ts`: única entrada consumida por el enrutador principal.

Se mantienen fuera del módulo las dependencias compartidas por otras áreas:
`api.ts`, `ui.tsx`, `boliviaLocations.ts`, `Layouts.tsx` y `PublicHeader.tsx`. El
encabezado está fuera porque también se utiliza en el registro público y en la página de
ruta no encontrada. Los estilos permanecen en `src/styles/public.css`, junto con las
demás hojas de estilo organizadas por área.

Las rutas de producción utilizan exclusivamente las exportaciones de `index.ts`; la
implementación pública antigua y sin rutas fue retirada para evitar duplicidad.
