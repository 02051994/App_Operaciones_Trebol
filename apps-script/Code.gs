/**
 * Web App endpoint para recibir registros desde la app offline.
 * Desplegar como: Ejecutar como tú, acceso: cualquiera con el enlace (o restringido según tu cuenta).
 */
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.openById('REEMPLAZAR_SHEET_ID');
    var sheet = ss.getSheetByName('Registros') || ss.insertSheet('Registros');

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
