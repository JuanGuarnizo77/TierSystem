import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import puppeteer from "file:///C:/Users/Usuario/AppData/Local/npm-cache/_npx/110f701c48e68d66/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js";

const ROOT = "c:/laragon/www/TierSystem-Django";
const OUT_DIR = path.join(ROOT, "video", "assets", "capturas");
const PYTHON = path.join(ROOT, "venv", "Scripts", "python.exe");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const FFMPEG = "C:/Users/Usuario/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe";
const BASE_URL = "http://127.0.0.1:8000";

fs.mkdirSync(OUT_DIR, { recursive: true });

// 1. Crear sesiones válidas de Django para agricultor, lab y admin
const pyScript = `
import django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')
django.setup()
from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore

User = get_user_model()
out = {}
for uname in ['agricultor', 'lab', 'admin']:
    u = User.objects.get(username=uname)
    s = SessionStore()
    s[SESSION_KEY] = str(u.pk)
    s[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    s[HASH_SESSION_KEY] = u.get_session_auth_hash()
    s.create()
    out[uname] = s.session_key
print(json.dumps(out))
`;

console.log("[1/3] Generando sesiones autenticadas en Django...");
const sessionsJson = execFileSync(PYTHON, ["-c", pyScript], { encoding: "utf8" }).trim().split("\n").pop();
const SESSIONS = JSON.parse(sessionsJson);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Inyectar modo claro forzado + cursor visual realista con onda de clic
async function attachLightModeAndCursor(page) {
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("color-theme", "light");
      localStorage.setItem("theme", "light");
    } catch {}
    document.addEventListener("DOMContentLoaded", () => {
      document.documentElement.classList.remove("dark");
      if (document.getElementById("__demo_cursor")) return;
      const cur = document.createElement("div");
      cur.id = "__demo_cursor";
      cur.innerHTML = `<svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M4 3L22 13.5L13.5 15.8L9.5 24L4 3Z" fill="#0F172A" stroke="#FFFFFF" stroke-width="2.2" stroke-linejoin="round"/>
      </svg>`;
      Object.assign(cur.style, {
        position: "fixed",
        left: "720px",
        top: "380px",
        width: "28px",
        height: "28px",
        pointerEvents: "none",
        zIndex: "999999",
        transform: "translate(-3px, -3px)",
        filter: "drop-shadow(0 3px 6px rgba(15,23,42,0.35))",
        transition: "transform 0.08s ease",
      });
      document.body.appendChild(cur);

      const ripple = document.createElement("div");
      ripple.id = "__demo_ripple";
      Object.assign(ripple.style, {
        position: "fixed",
        left: "720px",
        top: "380px",
        width: "36px",
        height: "36px",
        borderRadius: "50%",
        border: "3px solid #16A34A",
        background: "rgba(22, 163, 74, 0.22)",
        pointerEvents: "none",
        zIndex: "999998",
        transform: "translate(-50%, -50%) scale(0)",
        opacity: "0",
      });
      document.body.appendChild(ripple);

      window.__moveDemoCursor = (x, y) => {
        cur.style.left = `${x}px`;
        cur.style.top = `${y}px`;
      };
      window.__clickDemoCursor = (x, y) => {
        cur.style.left = `${x}px`;
        cur.style.top = `${y}px`;
        cur.style.transform = "translate(-3px, -3px) scale(0.84)";
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        ripple.style.transition = "none";
        ripple.style.transform = "translate(-50%, -50%) scale(0.2)";
        ripple.style.opacity = "0.95";
        requestAnimationFrame(() => {
          ripple.style.transition = "transform 0.42s ease-out, opacity 0.42s ease-out";
          ripple.style.transform = "translate(-50%, -50%) scale(1.65)";
          ripple.style.opacity = "0";
        });
        setTimeout(() => {
          cur.style.transform = "translate(-3px, -3px) scale(1)";
        }, 120);
      };
    });
  });
}

async function moveCursorSmooth(page, from, to, durationMs = 700) {
  const steps = Math.max(18, Math.round(durationMs / 25));
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const x = from.x + (to.x - from.x) * ease;
    const y = from.y + (to.y - from.y) * ease;
    await page.mouse.move(x, y);
    await page.evaluate((cx, cy) => window.__moveDemoCursor && window.__moveDemoCursor(cx, cy), x, y);
    await sleep(Math.round(durationMs / steps));
  }
  return to;
}

async function demoClickAt(page, pos) {
  await page.evaluate((cx, cy) => window.__clickDemoCursor && window.__clickDemoCursor(cx, cy), pos.x, pos.y);
  await sleep(160);
}

// Scroll sobre el contenedor scrolleable real (TierSystem usa overflow-y-auto en <main> o window!)
async function smoothScrollContainer(page, targetRatio, durationMs = 3000) {
  await page.evaluate(
    async (ratio, dur) => {
      const candidates = [
        document.querySelector("main"),
        document.querySelector(".overflow-y-auto"),
        document.scrollingElement,
        document.documentElement,
      ].filter(Boolean);
      let el = candidates.find((c) => c.scrollHeight - c.clientHeight > 30) || document.scrollingElement;
      const maxScroll = Math.max(0, el.scrollHeight - el.clientHeight);
      const startY = el.scrollTop;
      const targetY = Math.round(maxScroll * ratio);
      const dist = targetY - startY;
      const t0 = performance.now();
      return new Promise((resolve) => {
        function tick(now) {
          const p = Math.min(1, (now - t0) / dur);
          const ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
          el.scrollTop = startY + dist * ease;
          if (p < 1) requestAnimationFrame(tick);
          else resolve();
        }
        requestAnimationFrame(tick);
      });
    },
    targetRatio,
    durationMs
  );
}

async function ensureLightModeNow(page) {
  await page.evaluate(() => {
    localStorage.setItem("color-theme", "light");
    document.documentElement.classList.remove("dark");
  });
}

async function recordClip(browser, { name, role, steps }) {
  const rawPath = path.join(OUT_DIR, `${name}.raw.mp4`);
  const finalPath = path.join(OUT_DIR, `${name}.mp4`);
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 820, deviceScaleFactor: 1 });
  await attachLightModeAndCursor(page);

  await page.setCookie({
    name: "sessionid",
    value: SESSIONS[role],
    domain: "127.0.0.1",
    path: "/",
    httpOnly: true,
  });

  const first = steps[0];
  console.log(`\n[REC-LIGHT] ${name} (${role}) -> ${first.url}`);
  const resp = await page.goto(`${BASE_URL}${first.url}`, { waitUntil: "networkidle2", timeout: 20000 });
  await ensureLightModeNow(page);
  console.log(`            HTTP ${resp?.status()} | Final URL: ${page.url()}`);
  await sleep(500);

  let curPos = { x: 720, y: 380 };
  const recorder = await page.screencast({
    path: rawPath,
    ffmpegPath: FFMPEG,
    fps: 30,
    format: "mp4",
  });

  try {
    for (let i = 0; i < steps.length; i++) {
      const st = steps[i];
      if (i > 0 && st.url) {
        console.log(`            -> ${st.url}`);
        const r = await page.goto(`${BASE_URL}${st.url}`, { waitUntil: "networkidle2", timeout: 20000 });
        await ensureLightModeNow(page);
        console.log(`               HTTP ${r?.status()} | Final URL: ${page.url()}`);
        await sleep(350);
      }

      if (st.moves) {
        for (const m of st.moves) {
          curPos = await moveCursorSmooth(page, curPos, { x: m.x, y: m.y }, m.ms || 900);
          if (m.click) await demoClickAt(page, curPos);
          if (m.pause) await sleep(m.pause);
        }
      }

      if (st.scrollRatio !== undefined) {
        await smoothScrollContainer(page, st.scrollRatio, st.scrollMs || 3200);
      }

      if (st.movesAfter) {
        for (const m of st.movesAfter) {
          curPos = await moveCursorSmooth(page, curPos, { x: m.x, y: m.y }, m.ms || 900);
          if (m.click) await demoClickAt(page, curPos);
          if (m.pause) await sleep(m.pause);
        }
      }
    }
  } finally {
    await recorder.stop();
    await page.close();
  }

  execFileSync(
    FFMPEG,
    [
      "-y",
      "-i",
      rawPath,
      "-vf",
      "fps=30,scale=1440:820:flags=lanczos",
      "-c:v",
      "libx264",
      "-preset",
      "fast",
      "-crf",
      "19",
      "-pix_fmt",
      "yuv420p",
      "-an",
      "-movflags",
      "+faststart",
      finalPath,
    ],
    { stdio: "pipe" }
  );
  fs.unlinkSync(rawPath);
  const sz = (fs.statSync(finalPath).size / 1024 / 1024).toFixed(2);
  console.log(`[OK]        ${name}.mp4 (${sz} MB)`);
}

const CLIPS = [
  {
    name: "escena_05_terrenos",
    role: "agricultor",
    steps: [
      {
        url: "/agricultor/fincas/",
        moves: [
          { x: 520, y: 260, ms: 900, pause: 350 },
          { x: 880, y: 310, ms: 950, click: true, pause: 400 },
          { x: 1180, y: 170, ms: 900, pause: 300 },
        ],
        scrollRatio: 0.65,
        scrollMs: 2600,
        movesAfter: [{ x: 150, y: 330, ms: 950, click: true, pause: 300 }],
      },
      {
        url: "/agricultor/solicitudes/mis-solicitudes/",
        moves: [
          { x: 640, y: 240, ms: 950, pause: 400 },
          { x: 1210, y: 175, ms: 950, click: true, pause: 450 },
          { x: 760, y: 370, ms: 950, pause: 400 },
        ],
        scrollRatio: 0.8,
        scrollMs: 2800,
        movesAfter: [
          { x: 1080, y: 420, ms: 950, click: true, pause: 400 },
          { x: 620, y: 310, ms: 1000, pause: 500 },
        ],
      },
    ],
  },
  {
    name: "escena_06_solicitudes",
    role: "lab",
    steps: [
      {
        url: "/laboratorista/solicitudes/pendientes/",
        moves: [
          { x: 600, y: 270, ms: 900, pause: 350 },
          { x: 960, y: 320, ms: 950, click: true, pause: 350 },
        ],
        scrollRatio: 0.5,
        scrollMs: 2000,
      },
      {
        url: "/laboratorista/solicitudes/mis-tareas/",
        moves: [
          { x: 540, y: 340, ms: 900, pause: 350 },
          { x: 540, y: 495, ms: 950, click: true, pause: 400 },
        ],
        scrollRatio: 0.6,
        scrollMs: 2000,
        movesAfter: [{ x: 780, y: 320, ms: 950, pause: 450 }],
      },
    ],
  },
  {
    name: "escena_08_muestreo",
    role: "lab",
    steps: [
      {
        url: "/laboratorista/toma-muestras/?solicitud_id=6",
        moves: [
          { x: 760, y: 440, ms: 950, pause: 400 },
          { x: 920, y: 510, ms: 950, click: true, pause: 450 },
          { x: 840, y: 580, ms: 950, click: true, pause: 450 },
        ],
        scrollRatio: 0.55,
        scrollMs: 3600,
        movesAfter: [
          { x: 650, y: 400, ms: 950, pause: 450 },
          { x: 1020, y: 430, ms: 950, click: true, pause: 450 },
        ],
      },
      {
        scrollRatio: 1.0,
        scrollMs: 3500,
        movesAfter: [
          { x: 740, y: 480, ms: 950, pause: 450 },
          { x: 980, y: 520, ms: 950, click: true, pause: 500 },
        ],
      },
    ],
  },
  {
    name: "escena_09_resultado_ia",
    role: "agricultor",
    steps: [
      {
        url: "/agricultor/solicitudes/resultado/7/",
        moves: [
          { x: 520, y: 390, ms: 950, pause: 450 },
          { x: 920, y: 340, ms: 950, pause: 450 },
          { x: 920, y: 470, ms: 950, pause: 450 },
        ],
        scrollRatio: 0.45,
        scrollMs: 3800,
        movesAfter: [
          { x: 640, y: 410, ms: 950, click: true, pause: 450 },
          { x: 1060, y: 430, ms: 950, pause: 450 },
        ],
      },
      {
        scrollRatio: 0.85,
        scrollMs: 3800,
        movesAfter: [
          { x: 590, y: 460, ms: 950, pause: 450 },
          { x: 1080, y: 520, ms: 950, click: true, pause: 500 },
        ],
      },
      {
        scrollRatio: 1.0,
        scrollMs: 3000,
        movesAfter: [
          { x: 840, y: 500, ms: 1000, pause: 500 },
          { x: 640, y: 420, ms: 1000, pause: 600 },
        ],
      },
    ],
  },
  {
    name: "escena_12_historial",
    role: "agricultor",
    steps: [
      {
        url: "/agricultor/solicitudes/historial/",
        moves: [
          { x: 680, y: 290, ms: 850, pause: 350 },
          { x: 1120, y: 205, ms: 900, click: true, pause: 350 },
        ],
        scrollRatio: 0.55,
        scrollMs: 2000,
      },
      {
        url: "/agricultor/solicitudes/comparar/",
        moves: [
          { x: 600, y: 380, ms: 900, pause: 350 },
          { x: 1020, y: 380, ms: 900, click: true, pause: 350 },
        ],
        scrollRatio: 0.8,
        scrollMs: 2400,
        movesAfter: [{ x: 820, y: 460, ms: 900, pause: 400 }],
      },
    ],
  },
  {
    name: "escena_13_mercado",
    role: "agricultor",
    steps: [
      {
        url: "/mercado/",
        moves: [
          { x: 640, y: 310, ms: 950, pause: 400 },
          { x: 960, y: 410, ms: 950, click: true, pause: 400 },
        ],
        scrollRatio: 0.5,
        scrollMs: 3200,
        movesAfter: [
          { x: 760, y: 380, ms: 950, pause: 400 },
          { x: 1080, y: 460, ms: 950, click: true, pause: 400 },
        ],
      },
      {
        scrollRatio: 1.0,
        scrollMs: 3200,
        movesAfter: [{ x: 700, y: 460, ms: 950, pause: 450 }],
      },
    ],
  },
  {
    name: "escena_14_admin",
    role: "admin",
    steps: [
      {
        url: "/administrador/dashboard/",
        moves: [
          { x: 560, y: 250, ms: 850, pause: 300 },
          { x: 1040, y: 250, ms: 850, pause: 300 },
        ],
        scrollRatio: 0.5,
        scrollMs: 1800,
      },
      {
        url: "/administrador/hardware/",
        moves: [
          { x: 640, y: 340, ms: 850, pause: 300 },
          { x: 960, y: 340, ms: 850, click: true, pause: 300 },
        ],
        scrollRatio: 0.5,
        scrollMs: 1800,
      },
      {
        url: "/administrador/configuracion/",
        moves: [
          { x: 720, y: 320, ms: 850, pause: 300 },
          { x: 940, y: 460, ms: 850, click: true, pause: 350 },
        ],
        scrollRatio: 0.75,
        scrollMs: 2200,
      },
    ],
  },
];

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--window-size=1440,820"],
});

const onlyArg = process.argv[2];
const toRun = onlyArg ? CLIPS.filter((c) => c.name === onlyArg) : CLIPS;

try {
  console.log(`[2/3] Grabando ${toRun.length} pantalla(s) en MODO CLARO con cursor animado...`);
  for (const clip of toRun) {
    await recordClip(browser, clip);
  }
  console.log("\n[3/3] Grabaciones en modo claro completadas en:", OUT_DIR);
} finally {
  await browser.close();
}
