const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function placePart(searchQuery, canvasX, canvasY) {
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
          try {
            // Click Library tab at bottom left if not open (x=45, y=985)
            await send('Runtime.evaluate', {
              expression: `(() => {
                const libTab = Array.from(document.querySelectorAll('*')).find(e => e.textContent && e.textContent.trim() === 'Library');
                if (libTab) libTab.click();
              })()`
            });
            await new Promise(r => setTimeout(r, 200));

            // Focus and click search input box
            const inputPos = await send('Runtime.evaluate', {
              expression: `(() => {
                const inp = Array.from(document.querySelectorAll('input')).find(i => i.placeholder && i.placeholder.includes('Search'));
                if (!inp) return null;
                const r = inp.getBoundingClientRect();
                return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
              })()`,
              returnByValue: true
            });
            const searchX = inputPos.result.value?.x || 716;
            const searchY = inputPos.result.value?.y || 731;

            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: searchX, y: searchY, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: searchX, y: searchY, button: 'left', clickCount: 1 });

            // Select all & delete
            await send('Input.dispatchKeyEvent', { type: 'keyDown', commands: ['selectAll'], key: 'a', modifiers: 2 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a' });
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Backspace', windowsVirtualKeyCode: 8 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', windowsVirtualKeyCode: 8 });

            // Type query
            for (const c of searchQuery) {
              await send('Input.dispatchKeyEvent', { type: 'keyDown', text: c, unmodifiedText: c });
              await send('Input.dispatchKeyEvent', { type: 'keyUp', key: c });
            }

            // Enter
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', windowsVirtualKeyCode: 13 });
            await send('Input.dispatchKeyEvent', { type: 'char', text: '\r' });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', windowsVirtualKeyCode: 13 });

            // Wait for results to load
            await new Promise(r => setTimeout(r, 1200));

            // Click first row in search results
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 500, y: 820, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 500, y: 820, button: 'left', clickCount: 1 });
            await new Promise(r => setTimeout(r, 400));

            // Click Place button (x=1340, y=731)
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 1340, y: 731, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 1340, y: 731, button: 'left', clickCount: 1 });
            await new Promise(r => setTimeout(r, 300));

            // Drop at canvas (canvasX, canvasY)
            await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: canvasX, y: canvasY });
            await new Promise(r => setTimeout(r, 150));
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: canvasX, y: canvasY, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: canvasX, y: canvasY, button: 'left', clickCount: 1 });
            await new Promise(r => setTimeout(r, 200));

            // Cancel place mode (Escape)
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Escape', windowsVirtualKeyCode: 27 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', windowsVirtualKeyCode: 27 });

            ws.close();
            resolve(`Placed ${searchQuery} at (${canvasX}, ${canvasY})`);
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

const query = process.argv[2] || 'ESP32';
const cx = parseInt(process.argv[3] || '600', 10);
const cy = parseInt(process.argv[4] || '380', 10);

placePart(query, cx, cy).then(console.log).catch(console.error);
