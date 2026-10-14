const WebSocket = require('C:/Users/Usuario/AppData/Roaming/npm/node_modules/easyeda-mcp-pro/node_modules/ws');

async function main() {
  const res = await fetch('http://127.0.0.1:9222/json/list');
  const targets = await res.json();
  const page = targets.find(t => t.type === 'page' && /EasyEDA|JLCEDA/i.test(t.title));
  if (!page) return;

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.on('open', () => {
    const expr = `
      (() => {
        let out = {};
        out.SCH = typeof SCH !== 'undefined' ? Object.keys(SCH).slice(0, 30) : null;
        
        // Find if there are frames or editor windows
        out.iframesCount = document.querySelectorAll('iframe').length;
        
        // Check canvas element and canvas context
        const canvases = Array.from(document.querySelectorAll('canvas'));
        out.canvases = canvases.map(c => ({ width: c.width, height: c.height, id: c.id, className: c.className }));

        // Check project design tree
        const treeItems = Array.from(document.querySelectorAll('.tree-node, .tree-item, .el-tree-node__label, [class*="tree"]'))
          .map(el => el.textContent.trim())
          .filter(t => t.length > 0 && t.length < 40);
        out.tree = [...new Set(treeItems)].slice(0, 15);

        return out;
      })()
    `;

    ws.send(JSON.stringify({
      id: 1,
      method: 'Runtime.evaluate',
      params: { expression: expr, returnByValue: true }
    }));
  });

  ws.on('message', data => {
    const msg = JSON.parse(data.toString());
    if (msg.id === 1) {
      console.log('TREE & CANVAS:', JSON.stringify(msg.result?.result?.value, null, 2));
      ws.close();
    }
  });
}

main().catch(console.error);
