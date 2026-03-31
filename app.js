const DB_NAME = 'trebol_offline_db';
const DB_VERSION = 1;
const STORE = 'records';
const DEFAULT_APPS_SCRIPT_URL = 'REEMPLAZAR_CON_URL_WEBAPP';
const STORAGE_KEYS = {
  webAppUrl: 'trebol_webapp_url',
};

const form = document.getElementById('recordForm');
const recordsList = document.getElementById('recordsList');
const templateSelect = document.getElementById('templateSelect');
const syncButton = document.getElementById('syncButton');
const pendingCount = document.getElementById('pendingCount');
const connectionStatus = document.getElementById('connectionStatus');
const webAppUrlInput = document.getElementById('webAppUrl');
const saveConfigButton = document.getElementById('saveConfigButton');

function getWebAppUrl() {
  return localStorage.getItem(STORAGE_KEYS.webAppUrl) || DEFAULT_APPS_SCRIPT_URL;
}

function saveWebAppUrl(url) {
  localStorage.setItem(STORAGE_KEYS.webAppUrl, url.trim());
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
  const appsScriptUrl = getWebAppUrl();

  if (!pendingRecords.length || !navigator.onLine) {
    return;
  }

  if (!appsScriptUrl || appsScriptUrl === DEFAULT_APPS_SCRIPT_URL) {
    alert('Configura la URL de Web App antes de sincronizar.');
    return;
  }

  for (const record of pendingRecords) {
    try {
      const response = await fetch(appsScriptUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record),
      });

      if (!response.ok) {
        continue;
      }

      const result = await response.json().catch(() => ({}));
      if (result?.ok || result?.status === 'ok') {
        record.status = 'synced';
        record.syncedAt = new Date().toISOString();
        await saveRecord(record);
      }
    } catch {
      // Si falla la red, se mantiene pendiente para reintentar luego.
    }
  }

  await renderRecords();
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const record = collectFormData();
  await saveRecord(record);
  form.reset();
  await renderRecords();
});

saveConfigButton.addEventListener('click', () => {
  const url = webAppUrlInput.value.trim();
  if (!url) {
    alert('Ingresa una URL válida de Web App.');
    return;
  }
  saveWebAppUrl(url);
  alert('Configuración guardada en este dispositivo.');
});

syncButton.addEventListener('click', async () => {
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

(function initConfigUI() {
  webAppUrlInput.value = getWebAppUrl() === DEFAULT_APPS_SCRIPT_URL ? '' : getWebAppUrl();
})();

(async function init() {
  renderStatus();
  await renderRecords();
  await syncPendingRecords();
})();
