# Relaciones de la base de datos

- Uno a uno: Usuario–PerfilAdministrador y Usuario–Expositor.
- Uno a muchos: Expositor–Producto, Categoría–Producto, Producto–ImagenProducto, Feria–ImagenFeria, Usuario–Auditoría y Usuario–Recuperación.
- Muchos a muchos: Expositor–Tipo mediante `exhibitor_type_links`; Feria–Expositor mediante `fair_exhibitors`.

Inhabilitar conserva relaciones pero las excluye de la publicación. La eliminación lógica asigna `deleted_at`; reactivar restaura el estado y restaurar limpia `deleted_at`. Las composiciones de imágenes usan borrado físico en cascada únicamente cuando se elimina físicamente el padre.
