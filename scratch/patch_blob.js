const fs = require('fs');

const p = 'C:/Users/Usuario/AppData/Local/EasyEDA-Pro/cache.x64.3/IndexedDB/https_client_0.indexeddb.blob/1/00/7';
let code = fs.readFileSync(p, 'utf8');

// 1. Aumentar el timeout de registro de 600ms a 10s
code = code.replace(
  'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 600;',
  'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 10000;'
);

// 2. Asignar el extensionUuid al llamar a getWsApi()
code = code.replace(
  'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {',
  'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (sysWs && !sysWs.extensionUuid) sysWs.extensionUuid = "e7b9fb543e9a4c2898e30d33e5c9b68a";\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {'
);

fs.writeFileSync(p, code, 'utf8');
console.log('SUCCESSFULLY PATCHED BLOB 7');
