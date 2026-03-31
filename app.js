const DB_NAME = 'trebol_offline_db';
const DB_VERSION = 1;
const STORE = 'records';
const APPS_SCRIPT_URL_KEY = 'apps_script_url';
const APPS_SCRIPT_URL_DEFAULT = 'https://script.google.com/macros/s/REEMPLAZAR_CON_URL_WEBAPP/exec';

const form = document.getElementById('recordForm');
const recordsList = document.getElementById('recordsList');
const templateSelect = document.getElementById('templateSelect');
const syncButton = document.getElementById('syncButton');
const pendingCount = document.getElementById('pendingCount');
const connectionStatus = document.getElementById('connectionStatus');
const appsScriptUrlInput = document.getElementById('appsScriptUrl');
const syncMessage = document.getElementById('syncMessage');

function getAppsScriptUrl() {
  const configured = localStorage.getItem(APPS_SCRIPT_URL_KEY)?.trim();
  return configured || APPS_SCRIPT_URL_DEFAULT;
}

function setAppsScriptUrl(url) {
  localStorage.setItem(APPS_SCRIPT_URL_KEY, url.trim());
}

function showSyncMessage(message, type = 'neutral') {
  syncMessage.textContent = message;
  syncMessage.className = `sync-message ${type}`;
}

function isValidAppsScriptUrl(url) {
  return /^https:\/\/script\.google\.com\/macros\/s\/.+\/exec(\?.*)?$/i.test(url);
}

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'id' });
        store.createIndex('status', 'status');
        store.createIndex('createdAt', 'createdAt');
      }
    };

    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveRecord(record) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(record);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function getAllRecords() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function getPendingRecords() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).index('status').getAll('pending');
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

function collectFormData() {
  const data = new FormData(form);
  return {
    id: crypto.randomUUID(),
    template: templateSelect.value,
    fields: {
      fecha: data.get('fecha'),
      nombresApellidos: data.get('nombresApellidos')?.trim(),
      dni: data.get('dni')?.trim(),
      empresa: data.get('empresa')?.trim(),
      areaVisitar: data.get('areaVisitar')?.trim(),
      motivoVisita: data.get('motivoVisita')?.trim(),
      firmaNombre: data.get('firmaNombre')?.trim(),
    },
    status: 'pending',
    createdAt: new Date().toISOString(),
    syncedAt: null,
  };
}

function renderStatus() {
  if (navigator.onLine) {
    connectionStatus.textContent = 'En línea';
    connectionStatus.className = 'badge online';
  } else {
    connectionStatus.textContent = 'Sin conexión';
    connectionStatus.className = 'badge offline';
  }
}

async function renderRecords() {
  const records = (await getAllRecords()).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  recordsList.innerHTML = '';

  const pending = records.filter((r) => r.status === 'pending').length;
  pendingCount.textContent = `Pendientes: ${pending}`;

  const template = document.getElementById('recordItemTemplate');

  for (const record of records) {
    const item = template.content.cloneNode(true);
    item.querySelector('.record-title').textContent = `${record.fields.nombresApellidos} (${record.template})`;
    item.querySelector('.record-meta').textContent = `${record.fields.fecha} • DNI: ${record.fields.dni}`;

    const state = item.querySelector('.record-state');
    state.textContent = record.status === 'synced' ? 'Sincronizado' : 'Pendiente';
    state.className = `record-state ${record.status}`;

    recordsList.appendChild(item);
  }
}

async function syncPendingRecords() {
  const pendingRecords = await getPendingRecords();
  if (!pendingRecords.length || !navigator.onLine) {
    if (!navigator.onLine) {
      showSyncMessage('Sin conexión: cuando vuelva el internet se reintentará la sincronización.', 'warn');
    }
    return;
  }

  const appsScriptUrl = getAppsScriptUrl();
  if (!isValidAppsScriptUrl(appsScriptUrl)) {
    showSyncMessage('Configura una URL válida de Apps Script (termina en /exec).', 'warn');
    return;
  }

  let syncedCount = 0;
  let failedCount = 0;
  let lastFailureReason = '';

  for (const record of pendingRecords) {
    try {
      const result = await sendRecordToAppsScript(appsScriptUrl, record);
      if (result.synced) {
        record.status = 'synced';
        record.syncedAt = new Date().toISOString();
        await saveRecord(record);
        syncedCount += 1;
      } else {
        failedCount += 1;
        if (result.reason) {
          lastFailureReason = result.reason;
        }
      }
    } catch (error) {
      // Si falla la red, se mantiene pendiente para reintentar luego.
      failedCount += 1;
      showSyncMessage(`Error de sincronización: ${error?.message || 'sin detalle'}.`, 'warn');
    }
  }

  await renderRecords();
  if (syncedCount > 0) {
    showSyncMessage(`Sincronización completada: ${syncedCount} registro(s) enviado(s).`, 'ok');
  } else {
    showSyncMessage(
      `No se sincronizó ningún registro${
        failedCount ? ` (${failedCount} fallido/s)` : ''
      }. Revisa la URL /exec, el ID de la hoja y el despliegue de Apps Script.${
        lastFailureReason ? ` Detalle: ${lastFailureReason}` : ''
      }`,
      'warn',
    );
  }
}

async function sendRecordToAppsScript(appsScriptUrl, record) {
  const payload = JSON.stringify(record);

  try {
    const response = await fetch(appsScriptUrl, {
      method: 'POST',
      // Evita preflight CORS (Apps Script no responde OPTIONS por defecto).
      // Enviamos el JSON como text/plain para que sea una "simple request".
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: payload,
    });

    if (!response.ok) {
      return { synced: false, reason: `HTTP ${response.status}` };
    }

    const result = await response.json().catch(() => ({}));
    if (result?.ok || result?.status === 'ok') {
      return { synced: true };
    }

    return { synced: false, reason: result?.message || 'Apps Script no confirmó el guardado.' };
  } catch (_error) {
    // Fallback para despliegues de Apps Script sin CORS:
    // mode:no-cors permite intentar el envío, pero NO confirma guardado.
    const opaqueResponse = await fetch(appsScriptUrl, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: payload,
    });

    if (opaqueResponse.type === 'opaque') {
      return {
        synced: false,
        reason: 'No se pudo confirmar respuesta del Apps Script (modo no-cors).',
      };
    }

    return { synced: false, reason: 'No se pudo completar el envío al Apps Script.' };
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const record = collectFormData();
  await saveRecord(record);
  form.reset();
  await renderRecords();
});

syncButton.addEventListener('click', async () => {
  showSyncMessage('Sincronizando...', 'neutral');
  await syncPendingRecords();
});

window.addEventListener('online', async () => {
  renderStatus();
  await syncPendingRecords();
});

window.addEventListener('offline', renderStatus);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js');
}

(async function init() {
  appsScriptUrlInput.value = getAppsScriptUrl();
  appsScriptUrlInput.addEventListener('change', () => {
    const url = appsScriptUrlInput.value.trim();
    setAppsScriptUrl(url);
    if (!isValidAppsScriptUrl(url)) {
      showSyncMessage('La URL parece inválida. Debe ser del tipo https://script.google.com/macros/s/.../exec', 'warn');
      return;
    }
    showSyncMessage('URL guardada. Ya puedes sincronizar.', 'ok');
  });

  renderStatus();
  await renderRecords();
  await syncPendingRecords();
})();
