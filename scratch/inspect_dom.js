const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function inspectDom() {
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
              expression: `(() => {
                const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                  placeholder: i.placeholder,
                  className: i.className,
                  value: i.value,
                  rect: i.getBoundingClientRect()
                }));
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                  text: b.innerText,
                  className: b.className,
                  rect: b.getBoundingClientRect()
                })).filter(b => b.text && b.text.trim().length > 0);
                return { inputs, buttons: buttons.slice(0, 15) };
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

inspectDom().then(console.log).catch(console.error);
