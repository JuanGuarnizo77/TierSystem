const http = require('http');
const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function placeFromCommon(componentText, canvasX, canvasY) {
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
          try {
            // Find component element in Common Library by text or class
            const elPos = await send('Runtime.evaluate', {
              expression: `(() => {
                const el = Array.from(document.querySelectorAll('*')).find(e => e.textContent && e.textContent.includes('${componentText}'));
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
              })()`,
              returnByValue: true
            });

            if (!elPos.result.value) {
              ws.close();
              return reject('Element ' + componentText + ' not found in Common Library');
            }

            const { x, y } = elPos.result.value;
            // Click component in Common Library to start placing
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
            await new Promise(r => setTimeout(r, 300));

            // Move to canvas target
            await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: canvasX, y: canvasY });
            await new Promise(r => setTimeout(r, 200));

            // Click to place
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: canvasX, y: canvasY, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: canvasX, y: canvasY, button: 'left', clickCount: 1 });
            await new Promise(r => setTimeout(r, 200));

            // Escape to cancel placement
            await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Escape', windowsVirtualKeyCode: 27 });
            await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', windowsVirtualKeyCode: 27 });

            ws.close();
            resolve('Placed ' + componentText + ' at (' + canvasX + ', ' + canvasY + ')');
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

const comp = process.argv[2] || 'Res_AXIAL';
const cx = parseInt(process.argv[3] || '600', 10);
const cy = parseInt(process.argv[4] || '400', 10);

placeFromCommon(comp, cx, cy).then(console.log).catch(console.error);
