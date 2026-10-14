const fs = require('fs');
const cp = require('child_process');
const path = require('path');

const eextPaths = [
  'C:/Users/Usuario/AppData/Local/npm-cache/_npx/fc00c14b50ef4c23/node_modules/easyeda-mcp-pro/easyeda-bridge-extension.eext',
  'C:/Users/Usuario/AppData/Local/npm-cache/_npx/74b694bca372916a/node_modules/easyeda-mcp-pro/easyeda-bridge-extension.eext'
];

for (const eext of eextPaths) {
  if (!fs.existsSync(eext)) continue;
  console.log('Patching', eext);
  const dir = path.dirname(eext);
  const tempDir = path.join(dir, 'temp_eext');
  if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
  fs.mkdirSync(tempDir);

  cp.execSync(`tar -xf "${eext}" -C "${tempDir}"`);

  const indexJs = path.join(tempDir, 'dist', 'index.js');
  let code = fs.readFileSync(indexJs, 'utf8');

  code = code.replace(
    'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 600;',
    'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 10000;'
  );

  code = code.replace(
    'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {',
    'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (sysWs && !sysWs.extensionUuid) sysWs.extensionUuid = "e7b9fb543e9a4c2898e30d33e5c9b68a";\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {'
  );

  fs.writeFileSync(indexJs, code, 'utf8');

  // Repack with tar/zip
  fs.unlinkSync(eext);
  cp.execSync(`tar -acf "${eext}" *`, { cwd: tempDir });
  fs.rmSync(tempDir, { recursive: true, force: true });
  console.log('Successfully repacked', eext);
}
