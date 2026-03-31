# Guía paso a paso (rápida)

Esta guía responde: **"¿cómo hago eso?"**

## 1) Crear y pegar el script en Google Apps Script

1. Entra a: https://script.google.com/
2. Crea un proyecto nuevo.
3. Copia y pega el contenido de `apps-script/Code.gs` en el editor.
4. Guarda.

## 2) Verificar que el ID de tu hoja esté correcto

En `apps-script/Code.gs` debe verse tu ID:

```js
var SHEET_ID = '1n13J0V_rqKUWU-6y960H6ODS_leAy9mpImI33n9-gZY';
```

Si cambias de hoja, reemplaza ese valor.

## 3) Desplegar como Web App

1. Click en **Deploy** (arriba derecha).
2. **New deployment**.
3. Tipo: **Web app**.
4. **Execute as**: tu cuenta.
5. **Who has access**: "Anyone with the link" (o según tu política).
6. Click **Deploy**.
7. Copia la URL que termina en `/exec`.

## 4) Probar que el endpoint está vivo (GET)

Pega la URL `/exec` en el navegador.
Debe responder algo como:

```json
{"ok":true,"status":"alive","service":"trebol-sync"}
```

Si eso sale, el script está publicado correctamente.

## 5) Configurar la app

1. Levanta la app localmente:

```bash
python3 -m http.server 8080
```

2. Abre: `http://localhost:8080`
3. En "Configuración de sincronización", pega tu URL `/exec`.
4. Click en **Guardar configuración**.

## 6) Probar envío real (POST)

1. Llena el formulario en la app.
2. Pulsa **Guardar offline**.
3. Pulsa **Sincronizar pendientes** (con internet).
4. Revisa tu Google Sheet (pestaña `Registros`), debe aparecer una fila nueva.

## 7) Problemas comunes

- **No llega nada al Sheet**:
  - Revisa que la URL sea `/exec`, no `/dev`.
  - Revisa permisos del deployment.
  - Revisa que `SHEET_ID` sea correcto.
- **Error de permisos**:
  - Vuelve a desplegar y autoriza el script.
- **Se queda en pendiente**:
  - Verifica conexión y que el endpoint responda `ok: true`.

## 8) ¿`doGet` es obligatorio?

- Para guardar datos: **No** (con `doPost` basta).
- Para diagnóstico rápido en navegador: **Sí conviene**.
