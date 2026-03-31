# App Operaciones Trébol (Offline + Sync Google Sheets)

Aplicación web offline-first para registrar múltiples formatos (ejemplo: declaración jurada de salud) desde celular o PC, guardar localmente y sincronizar cuando hay internet hacia Google Sheets mediante Google Apps Script.

## Características

- 100% usable sin internet (PWA con Service Worker).
- Almacenamiento local con IndexedDB.
- Cola de sincronización automática/manual al detectar conexión.
- Soporte para varios formatos en una sola app.
- Exportable a Android APK usando Capacitor.

## Estructura

- `index.html`: interfaz principal.
- `styles.css`: estilos.
- `app.js`: lógica de formularios, almacenamiento offline y sincronización.
- `sw.js`: service worker para cache offline.
- `manifest.json`: manifiesto PWA.
- `apps-script/Code.gs`: endpoint Apps Script para recibir datos y escribir en Sheets.

## Configuración rápida

1. Publica tu Apps Script como Web App y copia el URL.
2. En `app.js`, reemplaza `REEMPLAZAR_CON_URL_WEBAPP` por la URL real.
3. Sirve los archivos con un servidor local:

```bash
python3 -m http.server 8080
```

4. Abre `http://localhost:8080`.

## Campos del formato ejemplo

Formato `declaracion_salud`:

- fecha
- nombresApellidos
- dni
- empresa
- areaVisitar
- motivoVisita
- firmaNombre

## Convertir a APK (Android)

### Opción recomendada: Capacitor

```bash
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init trebol.offline.app "App Operaciones Trebol" --web-dir=.
npx cap add android
npx cap copy
npx cap open android
```

Luego en Android Studio: **Build > Build Bundle(s) / APK(s) > Build APK(s)**.

> Nota: para producción conviene usar una carpeta `dist/` como `webDir` y excluir archivos no necesarios.

## Diseño de sincronización

1. Usuario llena formulario sin internet.
2. Registro queda en IndexedDB con estado `pending`.
3. Al tener internet o pulsar "Sincronizar pendientes", la app envía registros al Apps Script.
4. Si Apps Script responde OK, el registro pasa a `synced`.

## Seguridad recomendada

- Añadir API key o token por dispositivo para validar en Apps Script.
- Implementar validaciones de DNI y longitud de campos.
- Evitar datos sensibles sin cifrado si el dispositivo es compartido.
