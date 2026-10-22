const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function listComponents() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const target = targets.find(t => t.type === 'page' || (t.title && t.title.includes('EasyEDA')));
        if (!target) return reject('No target');
        const ws = new WebSocket(target.webSocketDebuggerUrl);
        ws.on('open', () => {
          ws.send(JSON.stringify({
            id: 1,
            method: 'Runtime.evaluate',
            params: {
              expression: `(() => {
                const docs = Array.from(SCH.docMemoryManager.docMap.values());
                const doc = docs.find(d => d.docManager && d.docManager.docType === 'SCHEMATIC');
                if (!doc) return 'No sch doc';
                const models = Array.from(doc.docManager.shapeManager.modelMap.values());
                return models.map(m => {
                  return {
                    id: m.id,
                    type: m.type,
                    designator: m.displayDesignator || m.designator || m.attrs?.Designator?.value,
                    title: m.displayTitle || m.title || m.attrs?.Name?.value,
                    modelType: m.constructor?.name
                  };
                }).filter(m => m.designator || m.title);
              })()`,
              returnByValue: true
            }
          }));
        });
        ws.on('message', (msgStr) => {
          const resp = JSON.parse(msgStr);
          ws.close();
          resolve(resp.result?.result?.value);
        });
        ws.on('error', reject);
      });
    }).on('error', reject);
  });
}

listComponents().then(res => console.log(JSON.stringify(res, null, 2))).catch(console.error);
