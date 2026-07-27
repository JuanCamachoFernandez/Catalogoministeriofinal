# Unidad Productiva

Este módulo contiene únicamente las pantallas y servicios exclusivos del portal de la
Unidad Productiva.

- `pages/ProductiveUnitProfilePage.tsx`: consulta y edición del perfil.
- `pages/UnitSectorsPage.tsx`: selección de sectores productivos.
- `services/productiveUnitApi.ts`: endpoints exclusivos de perfil, logotipo y sectores.
- `UnitRoute.tsx`: protección de las rutas del responsable de una Unidad Productiva.
- `index.ts`: entrada de las páginas cargadas de forma diferida.

La gestión de productos permanece fuera porque también la utiliza administración. El
layout, la autenticación, los componentes UI y los tipos de API también permanecen fuera
por ser compartidos.

Los estilos exclusivos están en `src/styles/productive-unit.css`. Los estilos base
compartidos por administración y otros módulos permanecen en `src/index.css`.
