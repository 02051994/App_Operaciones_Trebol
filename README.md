# App Operaciones Trebol (Python + KivyMD)

Base **offline-first** para Android con formularios dinámicos, SQLite local y sincronización con Google Apps Script + Google Sheets.

## Estructura

- `main.py`: navegación, UI, login, formulario dinámico, guardado local.
- `db.py`: esquema SQLite y operaciones locales.
- `sync.py`: pull/push por lotes con Apps Script.
- `utils.py`: helpers de fechas, JSON, defaults.
- `kv/main.kv`: diseño moderno y simple de pantallas.
- `config.json`: configuración central (URL Apps Script, batch, etc.).
- `buildozer.spec`: empaquetado Android.

## Cómo ejecutar local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Usuario inicial (si `seed_demo_data=true`):
- usuario: `admin`
- password: `1234`

## Flujo operativo

1. Login local contra SQLite (`users`).
2. Selección de formato (`forms`).
3. Construcción dinámica del formulario (`form_fields`).
4. Guardado inmediato local en `records` con `status=pending`.
5. Sincronización por lotes por POST a Apps Script.
6. Si servidor responde OK: `status=synced`, se programa `delete_after = +24h`.
7. Purga automática elimina sincronizados vencidos.

## Contrato recomendado de Apps Script

### GET catálogos
- `?action=users` -> `{ users: [{id,usuario,password,activo,updated_at}, ...] }`
- `?action=forms` -> `{ forms: [{form_id,nombre,sheet_destino,activo,updated_at}, ...] }`
- `?action=fields` -> `{ fields: [{form_id,campo,tipo,calculo,opciones,orden,obligatorio,editable}, ...] }`

### POST registros
Body:

```json
{
  "action": "push_records",
  "records": [
    {
      "local_id": "uuid",
      "form_id": "declaracion_jurada",
      "usuario": "admin",
      "created_at": "2026-04-01T00:00:00Z",
      "data": {
        "FECHA": "2026-04-01",
        "DNI": "...",
        "FIRMA": "signatures/firma_...png"
      }
    }
  ]
}
```

Respuesta:

```json
{
  "results": [
    {"local_id":"uuid", "ok": true, "remote_id": "row_123"}
  ]
}
```

## Apps Script base (referencia rápida)

```javascript
function doGet(e) {
  const action = e.parameter.action;
  if (action === 'users') return jsonOut({ users: getUsers_() });
  if (action === 'forms') return jsonOut({ forms: getForms_() });
  if (action === 'fields') return jsonOut({ fields: getFields_() });
  return jsonOut({ error: 'action inválida' });
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents || '{}');
  if (body.action !== 'push_records') return jsonOut({ results: [] });

  const results = [];
  body.records.forEach(r => {
    try {
      appendRecord_(r.form_id, r); // escribir respetando cabeceras
      results.push({ local_id: r.local_id, ok: true, remote_id: String(new Date().getTime()) });
    } catch (err) {
      results.push({ local_id: r.local_id, ok: false, error: String(err) });
    }
  });
  return jsonOut({ results: results });
}

function jsonOut(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
```

## Agregar nuevos formularios (sin reescribir app)

1. Crear hoja destino de registros en Google Sheets.
2. Agregar una fila en catálogo `forms` (`form_id`, `nombre`, `sheet_destino`).
3. Agregar filas en catálogo `fields` para cada campo (orden, tipo, obligatorio, opciones, etc.).
4. Ejecutar sincronización desde la app.

No se requiere tocar `main.py` para nuevos formatos si usas tipos soportados:
- TEXTO, NUMERO ENTERO, DECIMAL, FECHA, HORA, LISTA, FIRMA, AUTOCOMPLETADO, BOOLEANO/SI-NO, no editables.

## Build Android

```bash
buildozer android debug
```

Luego instalar APK generado en `bin/`.

## Script listo para tu hoja

Se agregó `google_apps_script.gs` con el backend completo para la hoja:
`1TzJY1eySEA2F_yR19-PZL_3qmMzGL8Wn8VDup4F-IVE`.

Pasos rápidos:
1. Abre Apps Script desde tu Google Sheet.
2. Pega el contenido de `google_apps_script.gs`.
3. Implementa como *Web app* con acceso para quien tenga el link.
4. Copia la URL de despliegue en `config.json` (`apps_script_url`).

## Solución de problemas de sincronización

Si al sincronizar ves en logs redirecciones a `accounts.google.com` (`302`), tu Web App de Apps Script no está pública para la app.

> Importante: compartir el **Google Sheet** no es suficiente. Lo que debe estar accesible es el **despliegue Web App** de Apps Script.

Revisar en **Deploy > Manage deployments > Web app**:
- **Execute as**: tu cuenta.
- **Who has access**: `Anyone with the link` (o equivalente en tu dominio).
- En `config.json`, usar la URL del despliegue que termina en `/exec` (no la URL del editor ni `/dev`).

Luego vuelve a desplegar, actualiza `apps_script_url` en `config.json` y reintenta sincronización.
