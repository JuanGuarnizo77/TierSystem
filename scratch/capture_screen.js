const http = require('http');
const fs = require('fs');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function capture(outputPath) {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const target = targets.find(t => t.type === 'page' || (t.title && t.title.includes('EasyEDA')));
        if (!target) return reject('No target found');
        const ws = new WebSocket(target.webSocketDebuggerUrl);
        ws.on('open', () => {
          ws.send(JSON.stringify({
            id: 1,
            method: 'Page.captureScreenshot',
            params: { format: 'png' }
          }));
        });
        ws.on('message', (msgStr) => {
          const resp = JSON.parse(msgStr);
          ws.close();
          if (resp.result && resp.result.data) {
            fs.writeFileSync(outputPath, Buffer.from(resp.result.data, 'base64'));
            resolve(outputPath);
          } else {
            reject('No screenshot data: ' + JSON.stringify(resp));
          }
        });
        ws.on('error', reject);
      });
    }).on('error', reject);
  });
}

(async () => {
  const outPath = process.argv[2] || 'C:/Users/Usuario/.gemini/antigravity-ide/brain/a9f62f59-8e48-4de6-8c2f-8e99b00ce299/easyeda_screen.png';
  try {
    await capture(outPath);
    console.log('Saved to', outPath);
  } catch (err) {
    console.error(err);
  }
})();
