const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function switchAndSearch(query) {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const target = targets.find(t => t.type === 'page' || (t.title && t.title.includes('EasyEDA')));
        if (!target) return reject('No target');
        const ws = new WebSocket(target.webSocketDebuggerUrl);
        let id = 1;
        function send(method, params) {
          return new Promise(r => {
            const currentId = id++;
            function handler(msgStr) {
              const resp = JSON.parse(msgStr);
              if (resp.id === currentId) {
                ws.removeListener('message', handler);
                r(resp);
              }
            }
            ws.on('message', handler);
            ws.send(JSON.stringify({ id: currentId, method, params }));
          });
        }

        ws.on('open', async () => {
          // Switch to LCSC tab
          await send('Runtime.evaluate', {
            expression: '(() => { const t = Array.from(document.querySelectorAll("*")).find(el => el.textContent && el.textContent.trim() === "LCSC Electronics"); if(t) t.click(); })()'
          });
          await new Promise(r => setTimeout(r, 400));

          // Focus search, type query
          await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 716, y: 731, button: 'left', clickCount: 1 });
          await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 716, y: 731, button: 'left', clickCount: 1 });
          await send('Input.dispatchKeyEvent', { type: 'keyDown', commands: ['selectAll'], key: 'a', modifiers: 2 });
          await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a' });
          await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Backspace', windowsVirtualKeyCode: 8 });
          await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', windowsVirtualKeyCode: 8 });

          for (const c of query) {
            await send('Input.dispatchKeyEvent', { type: 'keyDown', text: c, unmodifiedText: c });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: c });
          }

          await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', windowsVirtualKeyCode: 13 });
          await send('Input.dispatchKeyEvent', { type: 'char', text: '\\r' });
          await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', windowsVirtualKeyCode: 13 });

          await new Promise(r => setTimeout(r, 1500));
          ws.close();
          resolve('Searched LCSC for ' + query);
        });
      });
    });
  });
}

switchAndSearch(process.argv[2] || 'KF301').then(console.log).catch(console.error);
