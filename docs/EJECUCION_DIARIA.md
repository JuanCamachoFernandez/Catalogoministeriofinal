# Ejecución diaria local

Compruebe primero que el servicio PostgreSQL esté iniciado.

## Terminal 1 — backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
flask run --host=0.0.0.0 --port=5000
```

## Terminal 2 — frontend

```powershell
cd frontend
npm run dev
```

Detenga cada servidor con `Ctrl+C`; cierre el entorno Python con `deactivate`.

No repita diariamente la creación del entorno, base, seeds, `seed-admin`, `pip install` o `npm install`. Repita instalaciones solo cuando cambien `requirements.txt` o `package.json`.

## Mantenimiento

```powershell
# backend
flask db upgrade
flask db migrate -m "Descripción del cambio"
pytest

# frontend
npm run test
npm run lint
npm run build
```
