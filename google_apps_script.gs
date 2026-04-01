/**
 * App Operaciones Trebol - Google Apps Script backend
 *
 * Hoja objetivo:
 * https://docs.google.com/spreadsheets/d/1TzJY1eySEA2F_yR19-PZL_3qmMzGL8Wn8VDup4F-IVE
 *
 * Requisitos de pestañas:
 * - users  : id | usuario | password | activo | updated_at
 * - forms  : form_id | nombre | sheet_destino | activo | updated_at
 * - fields : form_id | campo | tipo | calculo | opciones | orden | obligatorio | editable
 *
 * Cada sheet_destino indicado en forms debe existir y tener encabezados.
 */

const SPREADSHEET_ID = '1TzJY1eySEA2F_yR19-PZL_3qmMzGL8Wn8VDup4F-IVE';
const TAB_USERS = ['users', 'usuarios'];
const TAB_FORMS = ['forms', 'tipodeformato'];
const TAB_FIELDS = ['fields', 'campos'];

function doGet(e) {
  try {
    const action = (e && e.parameter && e.parameter.action) || '';

    if (action === 'users') return jsonOut({ users: getUsers_() });
    if (action === 'forms') return jsonOut({ forms: getForms_() });
    if (action === 'fields') return jsonOut({ fields: getFields_() });

    return jsonOut({
      error: 'action inválida',
      allowed: ['users', 'forms', 'fields'],
    });
  } catch (err) {
    return jsonOut({ error: String(err) });
  }
}

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (body.action !== 'push_records') {
      return jsonOut({ results: [], error: 'action inválida para POST' });
    }

    const records = Array.isArray(body.records) ? body.records : [];
    const results = records.map(pushOneRecord_);
    return jsonOut({ results: results });
  } catch (err) {
    return jsonOut({ results: [], error: String(err) });
  }
}

function pushOneRecord_(record) {
  const localId = safeString_(record && record.local_id);

  try {
    if (!record || !record.form_id) {
      throw new Error('record.form_id es obligatorio');
    }

    const formMap = indexBy_(getForms_(), 'form_id');
    const form = formMap[record.form_id];

    if (!form) {
      throw new Error('form_id no encontrado en forms: ' + record.form_id);
    }

    const targetSheetName = safeString_(form.sheet_destino);
    if (!targetSheetName) {
      throw new Error('sheet_destino vacío en forms para form_id: ' + record.form_id);
    }

    const sheet = getSheetByNameOrThrow_(targetSheetName);

    // Asegura cabeceras mínimas de control.
    ensureHeaders_(sheet, ['remote_id', 'local_id', 'form_id', 'usuario', 'created_at']);

    const rowObj = Object.assign(
      {
        remote_id: Utilities.getUuid(),
        local_id: localId,
        form_id: safeString_(record.form_id),
        usuario: safeString_(record.usuario),
        created_at: safeString_(record.created_at) || new Date().toISOString(),
      },
      normalizeDataObject_(record.data)
    );

    appendObjectRowByHeaders_(sheet, rowObj);

    return {
      local_id: localId,
      ok: true,
      remote_id: rowObj.remote_id,
    };
  } catch (err) {
    return {
      local_id: localId,
      ok: false,
      error: String(err),
    };
  }
}

function getUsers_() {
  return readSheetAsObjects_(TAB_USERS).map(function (row) {
    return {
      id: safeString_(row.id),
      usuario: safeString_(row.usuario),
      password: safeString_(row.password),
      activo: toIntOrDefault_(row.activo, 1),
      updated_at: safeString_(row.updated_at),
    };
  });
}

function getForms_() {
  return readSheetAsObjects_(TAB_FORMS).map(function (row) {
    return {
      form_id: safeString_(row.form_id),
      nombre: safeString_(row.nombre),
      sheet_destino: safeString_(row.sheet_destino),
      activo: toIntOrDefault_(row.activo, 1),
      updated_at: safeString_(row.updated_at),
    };
  });
}

function getFields_() {
  return readSheetAsObjects_(TAB_FIELDS).map(function (row) {
    return {
      form_id: safeString_(row.form_id),
      campo: safeString_(row.campo),
      tipo: safeString_(row.tipo),
      calculo: safeString_(row.calculo),
      opciones: safeString_(row.opciones),
      orden: toIntOrDefault_(row.orden, 0),
      obligatorio: toIntOrDefault_(row.obligatorio, 0),
      editable: toIntOrDefault_(row.editable, 1),
    };
  });
}

function getSpreadsheet_() {
  return SpreadsheetApp.openById(SPREADSHEET_ID);
}

function getSheetByNameOrThrow_(sheetNameOrCandidates) {
  const ss = getSpreadsheet_();
  const candidates = Array.isArray(sheetNameOrCandidates)
    ? sheetNameOrCandidates
    : [sheetNameOrCandidates];

  for (var i = 0; i < candidates.length; i += 1) {
    var candidate = safeString_(candidates[i]).trim();
    if (!candidate) continue;
    var sheet = ss.getSheetByName(candidate);
    if (sheet) return sheet;
  }

  throw new Error('No existe ninguna pestaña esperada: ' + JSON.stringify(candidates));
}

function readSheetAsObjects_(sheetName) {
  const sheet = getSheetByNameOrThrow_(sheetName);
  const values = sheet.getDataRange().getValues();
  if (!values || values.length < 2) return [];

  const headers = values[0].map(normalizeHeader_);
  const rows = [];

  for (var i = 1; i < values.length; i += 1) {
    const row = {};
    for (var j = 0; j < headers.length; j += 1) {
      if (!headers[j]) continue;
      row[headers[j]] = values[i][j];
    }
    rows.push(row);
  }

  return rows;
}

function ensureHeaders_(sheet, requiredHeaders) {
  const lastCol = Math.max(sheet.getLastColumn(), 1);
  const rawHeaders = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const existingHeaders = rawHeaders.map(normalizeHeader_);
  const missing = requiredHeaders.filter(function (h) {
    return existingHeaders.indexOf(h) === -1;
  });

  if (missing.length === 0) return;

  const finalHeaders = existingHeaders.concat(missing);
  sheet.getRange(1, 1, 1, finalHeaders.length).setValues([finalHeaders]);
}

function appendObjectRowByHeaders_(sheet, obj) {
  const lastCol = Math.max(sheet.getLastColumn(), 1);
  const headers = sheet
    .getRange(1, 1, 1, lastCol)
    .getValues()[0]
    .map(normalizeHeader_)
    .filter(Boolean);

  if (headers.length === 0) {
    throw new Error('La hoja destino no tiene encabezados en la fila 1');
  }

  const row = headers.map(function (h) {
    const value = obj[h];
    return value === undefined || value === null ? '' : value;
  });

  sheet.appendRow(row);
}

function normalizeDataObject_(data) {
  const out = {};
  if (!data || typeof data !== 'object') return out;

  Object.keys(data).forEach(function (key) {
    const normalizedKey = normalizeHeader_(key);
    if (!normalizedKey) return;
    out[normalizedKey] = data[key];
  });

  return out;
}

function indexBy_(arr, key) {
  return arr.reduce(function (acc, item) {
    const k = safeString_(item[key]);
    if (k) acc[k] = item;
    return acc;
  }, {});
}

function normalizeHeader_(value) {
  return safeString_(value).trim().toLowerCase();
}

function safeString_(value) {
  return value === undefined || value === null ? '' : String(value);
}

function toIntOrDefault_(value, fallback) {
  const n = parseInt(String(value), 10);
  return Number.isNaN(n) ? fallback : n;
}

function jsonOut(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
