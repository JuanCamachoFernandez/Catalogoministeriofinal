# Respaldo y restauración

```powershell
pg_dump -U catalogo -d catalogo_ferias -F c -f respaldo_catalogo_ferias.backup
pg_restore -U catalogo -d catalogo_ferias --clean respaldo_catalogo_ferias.backup
```

Compruebe el archivo con `Get-Item`. Respalde además `backend/uploads`. No publique `.env`, tokens, respaldos ni imágenes privadas en un repositorio público.
