const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function typeIntoSearch(text) {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const target = targets.find(t => t.type === 'page' || (t.title && t.title.includes('EasyEDA')));
        if (!target) return reject('No target found');
        const ws = new WebSocket(target.webSocketDebuggerUrl);
        let id = 1;
        function send(method, params) {
          return new Promise(res => {
            const currentId = id++;
            function handler(msgStr) {
              const resp = JSON.parse(msgStr);
              if (resp.id === currentId) {
                ws.removeListener('message', handler);
                res(resp);
              }
            }
            ws.on('message', handler);
            ws.send(JSON.stringify({ id: currentId, method, params }));
          });
        }

        ws.on('open', async () => {
          try {
            // Click on the search input box (x=716, y=731)
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 716, y: 731, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 716, y: 731, button: 'left', clickCount: 1 });

            // Select all existing text (Ctrl+A then Backspace)
            await send('Input.dispatchKeyEvent', { type: 'keyDown', commands: ['selectAll'], key: 'a', modifiers: 2 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a' });
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Backspace', windowsVirtualKeyCode: 8 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', windowsVirtualKeyCode: 8 });

            // Type each character of text
            for (const char of text) {
              await send('Input.dispatchKeyEvent', { type: 'keyDown', text: char, unmodifiedText: char });
              await send('Input.dispatchKeyEvent', { type: 'keyUp', key: char });
            }

            // Press Enter
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', windowsVirtualKeyCode: 13 });
            await send('Input.dispatchKeyEvent', { type: 'char', text: '\r' });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', windowsVirtualKeyCode: 13 });

            ws.close();
            resolve('Typed ' + text);
          } catch (e) {
            ws.close();
            reject(e);
          }
        });
        ws.on('error', reject);
      });
    }).on('error', reject);
  });
}

typeIntoSearch(process.argv[2] || 'LM7805').then(console.log).catch(console.error);
