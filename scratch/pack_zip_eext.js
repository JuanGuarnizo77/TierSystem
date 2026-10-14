const fs = require('fs');
const cp = require('child_process');
const path = require('path');

const eext = 'C:/Users/Usuario/Downloads/easyeda-bridge-extension.eext';
const tempDir = 'C:/Users/Usuario/Downloads/temp_eext';

if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
fs.mkdirSync(tempDir);

// Extract current files
cp.execSync(`tar -xf "${eext}" -C "${tempDir}"`);

// Verify index.js has our patch
const indexJs = path.join(tempDir, 'dist', 'index.js');
let code = fs.readFileSync(indexJs, 'utf8');
if (!code.includes('REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 10000')) {
  code = code.replace(
    'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 600;',
    'var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 10000;'
  );
}
if (!code.includes('sysWs.extensionUuid')) {
  code = code.replace(
    'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {',
    'function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {\n    const sysWs = getWsApi();\n    if (sysWs && !sysWs.extensionUuid) sysWs.extensionUuid = "e7b9fb543e9a4c2898e30d33e5c9b68a";\n    if (!options.skipRegister && sysWs?.register && sysWs.send) {'
  );
}
fs.writeFileSync(indexJs, code, 'utf8');

// Delete old .eext
if (fs.existsSync(eext)) fs.unlinkSync(eext);

// Use PowerShell Compress-Archive to create standard ZIP
const zipPath = 'C:/Users/Usuario/Downloads/easyeda-bridge-extension.zip';
if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);

cp.execSync(`powershell -Command "Compress-Archive -Path '${tempDir}\\*' -DestinationPath '${zipPath}' -Force"`);

// Rename .zip to .eext
fs.renameSync(zipPath, eext);
fs.rmSync(tempDir, { recursive: true, force: true });

// Copy to npm-cache too
const cacheEext1 = 'C:/Users/Usuario/AppData/Local/npm-cache/_npx/fc00c14b50ef4c23/node_modules/easyeda-mcp-pro/easyeda-bridge-extension.eext';
const cacheEext2 = 'C:/Users/Usuario/AppData/Local/npm-cache/_npx/74b694bca372916a/node_modules/easyeda-mcp-pro/easyeda-bridge-extension.eext';
if (fs.existsSync(path.dirname(cacheEext1))) fs.copyFileSync(eext, cacheEext1);
if (fs.existsSync(path.dirname(cacheEext2))) fs.copyFileSync(eext, cacheEext2);

console.log('ZIP PACKING COMPLETED SUCCESSFULLY');
