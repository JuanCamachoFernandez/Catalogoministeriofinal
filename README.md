# Sistema de Catálogo Digital de Ferias del Viceministerio

Sistema local Flask/PostgreSQL y React/TypeScript para administrar ferias, expositores, categorías y productos, además de publicar un catálogo ciudadano. Los correos usan Brevo Transactional Email API por HTTPS; no se utiliza Gmail API ni SMTP. La consulta de WhatsApp obtiene exclusivamente `telefono_whatsapp` del expositor propietario de los productos.

## Requisitos

- Python 3.11 o superior.
- Node.js 20 LTS o superior y npm.
- PostgreSQL 16 o superior.
- Git y Visual Studio Code recomendados.

## Inicio rápido local

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask db upgrade
flask seed-catalogs
flask seed-admin
flask run --host=0.0.0.0 --port=5000
```

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Enlaces

- Gestión: http://localhost:5173/gestion/login
- Catálogo público: http://localhost:5173/catalogo
- Estado de API: http://localhost:5000/api/health

## Documentación

- [Primera instalación](docs/INSTALACION_PRIMERA_VEZ.md)
- [Uso diario](docs/EJECUCION_DIARIA.md)
- [PostgreSQL](docs/CONFIGURACION_POSTGRESQL.md)
- [Brevo](docs/CONFIGURACION_BREVO.md)
- [API](docs/API.md)
- [Seguridad](docs/SEGURIDAD.md)
- [Archivos configurables](docs/ARCHIVOS_CONFIGURABLES.md)
