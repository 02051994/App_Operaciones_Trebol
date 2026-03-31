/**
 * Web App endpoint para recibir registros desde la app offline.
 *
 * PASOS:
 * 1) Pega este código en script.google.com.
 * 2) Deploy > New deployment > Web app.
 * 3) Ejecutar como: tú mismo.
 * 4) Acceso: según tu política (normalmente "Anyone with the link").
 * 5) Copia la URL /exec y colócala en la app (Configuración de sincronización).
 */

var SHEET_ID = '1n13J0V_rqKUWU-6y960H6ODS_leAy9mpImI33n9-gZY';
var SHEET_NAME = 'Registros';

function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, status: 'alive', service: 'trebol-sync' }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents || '{}');
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        'id',
        'template',
        'fecha',
        'nombres_apellidos',
        'dni',
        'empresa',
        'area_visitar',
        'motivo_visita',
        'firma_nombre',
        'created_at',
        'synced_at_servidor',
      ]);
    }

    sheet.appendRow([
      payload.id || '',
      payload.template || '',
      payload.fields?.fecha || '',
      payload.fields?.nombresApellidos || '',
      payload.fields?.dni || '',
      payload.fields?.empresa || '',
      payload.fields?.areaVisitar || '',
      payload.fields?.motivoVisita || '',
      payload.fields?.firmaNombre || '',
      payload.createdAt || '',
      new Date().toISOString(),
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok', ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', ok: false, message: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
