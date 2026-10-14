const cp = require('child_process');
const fs = require('fs');

const shortcutPath = 'C:/Users/Usuario/OneDrive/Desktop/EasyEDA Pro.lnk';
const psScript = `
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('${shortcutPath}')
$s.Arguments = '--remote-debugging-port=9222'
$s.Save()
Write-Output "DONE"
`;

fs.writeFileSync('C:/Users/Usuario/OneDrive/Desktop/update_shortcut.ps1', psScript, 'utf8');
const out = cp.execSync('powershell -ExecutionPolicy Bypass -File "C:/Users/Usuario/OneDrive/Desktop/update_shortcut.ps1"').toString();
console.log('Result:', out);
fs.unlinkSync('C:/Users/Usuario/OneDrive/Desktop/update_shortcut.ps1');
