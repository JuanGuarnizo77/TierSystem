const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function evaluate(code) {
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
            method: 'Runtime.evaluate',
            params: {
              expression: code,
              returnByValue: true
            }
          }));
        });
        ws.on('message', (msgStr) => {
          const resp = JSON.parse(msgStr);
          ws.close();
          if (resp.result && resp.result.result) {
            resolve(resp.result.result.value);
          } else {
            resolve(resp);
          }
        });
        ws.on('error', reject);
      });
    }).on('error', reject);
  });
}

(async () => {
  const code = process.argv[2] || 'Object.keys(window).filter(k => k.toLowerCase().includes("sch") || k.toLowerCase().includes("eda"))';
  try {
    const res = await evaluate(code);
    console.log(JSON.stringify(res, null, 2));
  } catch (err) {
    console.error(err);
  }
})();
