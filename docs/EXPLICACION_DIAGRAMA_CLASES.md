# Explicación del diagrama de clases

`User` concentra identidad, autenticación y rol. `AdminProfile` añade datos laborales y `Exhibitor` añade identidad comercial, sin mezclar credenciales con información pública. Microempresa, Productor y Artesano son clasificaciones combinables mediante `ExhibitorTypeLink`, no identidades distintas.

`FairExhibitor` resuelve la relación muchos a muchos y conserva autorización, stand y sector. Solo `AUTHORIZED` se publica. `Product` pertenece exactamente a un expositor y una categoría; sus imágenes son composición. Las recuperaciones guardan hashes de tokens y `Audit` registra acciones.

## WhatsApp y propiedad

El destinatario se deriva en servidor recorriendo `Product.exhibitor_id → Exhibitor.telefono_whatsapp`. El cliente no puede enviar un teléfono. Todos los productos se validan como disponibles, del mismo expositor y con una asignación autorizada en la feria.

## Cambios realizados respecto al diagrama inicial

Se conservan conceptualmente Usuario, Administrador, Empresa, Producto, Categoría e ImagenProducto. Emprendedor y Empresa se unificaron en `Exhibitor`; Administrador pasó a ser un perfil uno a uno de Usuario. Se agregaron Feria, asignaciones, tipos combinables, imágenes de feria, recuperación y auditoría para cubrir los flujos escritos.
