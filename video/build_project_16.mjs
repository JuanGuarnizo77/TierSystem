#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const assetsDir = path.join(__dirname, "assets");
const compsDir = path.join(__dirname, "compositions");

fs.mkdirSync(compsDir, { recursive: true });

const DURATIONS = {
  1: 20.167,
  2: 16.515,
  3: 15.642,
  4: 16.591,
  5: 17.968,
  6: 10.246,
  7: 22.319,
  8: 18.911,
  9: 25.296,
  10: 12.495,
  11: 21.151,
  12: 11.279,
  13: 14.760,
  14: 13.600,
  15: 13.354,
  16: 18.404,
};

const PAUSE = 0.4;
const SCENE_META = [];
let cursor = 0;

for (let i = 1; i <= 16; i++) {
  const code = String(i).padStart(2, "0");
  const dur = DURATIONS[i];
  const start = Number(cursor.toFixed(3));
  const end = Number((start + dur).toFixed(3));
  SCENE_META.push({ num: i, code, id: `scene${code}`, start, duration: dur, end });
  cursor = end + (i < 16 ? PAUSE : 0);
}

const TOTAL_DURATION = Number(SCENE_META[15].end.toFixed(3)); // 274.698

const COMMON_STYLE = `
    #root {
      position: absolute;
      inset: 0;
      background: #FFFFFF;
      background-image:
        radial-gradient(circle at 15% 15%, rgba(22, 163, 74, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 85% 80%, rgba(245, 158, 11, 0.06) 0%, transparent 45%),
        linear-gradient(to right, rgba(226, 232, 240, 0.55) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(226, 232, 240, 0.55) 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 64px 64px, 64px 64px;
      font-family: "Inter", sans-serif;
      color: #0F172A;
      overflow: hidden;
    }
    .safe-stage {
      position: absolute;
      inset: 76px 80px 172px 80px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
    }
    .scene-header {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .title-group {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    .step-num {
      background: #ECFDF5;
      border: 2.5px solid #16A34A;
      color: #15803D;
      font-size: 28px;
      font-weight: 900;
      padding: 8px 20px;
      border-radius: 16px;
    }
    .scene-title {
      font-size: 56px;
      font-weight: 900;
      letter-spacing: -0.025em;
      color: #0F172A;
      line-height: 1.1;
    }
    .scene-title .accent-green { color: #16A34A; }
    .scene-title .accent-orange { color: #D97706; }
    .scene-title .accent-pink { color: #E11D48; }
    .badge-pill {
      font-size: 28px;
      font-weight: 800;
      padding: 10px 26px;
      border-radius: 999px;
      background: #FEF3C7;
      border: 2.5px solid #D97706;
      color: #92400E;
      box-shadow: 0 6px 16px rgba(217, 119, 6, 0.12);
    }
    .badge-green {
      font-size: 28px;
      font-weight: 800;
      padding: 10px 26px;
      border-radius: 999px;
      background: #DCFCE7;
      border: 2.5px solid #16A34A;
      color: #166534;
      box-shadow: 0 6px 16px rgba(22, 163, 74, 0.12);
    }
    .illus-card {
      width: 100%;
      height: 700px;
      background: #FFFFFF;
      border: 2.5px solid #CBD5E1;
      box-shadow: 0 20px 50px rgba(15, 23, 42, 0.07);
      border-radius: 32px;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
`;

function wrapScene(meta, headerHtml, bodySvgOrHtml, customScript, hasVideo = false) {
  const { id, num, code, duration } = meta;
  const fadeOutAt = Number((duration - 0.3).toFixed(3));
  const introScript = num === 1
    ? `    tl.fromTo("#${id}-clip", { opacity: 1 }, { opacity: 1, duration: 0.1 }, 0);
    tl.fromTo("#${id}-hdr", { opacity: 1, y: 0 }, { opacity: 1, y: 0, duration: 0.1 }, 0);`
    : `    tl.fromTo("#${id}-clip", { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out" }, 0);
    tl.fromTo("#${id}-hdr", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 0.12);`;
  const clipAttrs = hasVideo
    ? `style="position:absolute; inset:0;"`
    : `class="clip" data-start="0" data-duration="${duration}" data-track-index="0"`;
  const stageScaleScript = hasVideo
    ? ""
    : `    tl.fromTo("#${id}-stage", { scale: 0.992 }, { scale: 1.008, duration: ${Number((duration - 0.4).toFixed(2))}, ease: "none" }, 0);`;
  return `<template>
  <style>${COMMON_STYLE}</style>
  <div id="root" data-composition-id="${id}" data-width="1920" data-height="1080">
    <div id="${id}-clip" ${clipAttrs}>
      <div class="safe-stage">
        <div id="${id}-hdr" class="scene-header">
          <div class="title-group">
            <span class="step-num">${code}</span>
            ${headerHtml}
          </div>
        </div>
        <div id="${id}-stage" class="illus-card" data-layout-allow-overflow>
          ${bodySvgOrHtml}
        </div>
      </div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
${introScript}
${stageScaleScript}
${customScript}
    tl.to("#${id}-clip", { opacity: 0, duration: 0.3, ease: "power2.inOut" }, ${fadeOutAt});
    window.__timelines["${id}"] = tl;
  </script>
</template>
`;
}

function wrapScreenScene(meta, titleHtml, badgeHtml, videoRelPath, callouts) {
  const { id, duration } = meta;
  const cardsHtml = callouts
    .map(
      (c, idx) => `
      <div id="${id}-c${idx + 1}" style="background:${c.bg}; border:3px solid ${c.border}; border-radius:22px; padding:22px 24px; display:flex; flex-direction:column; gap:8px; box-shadow:0 8px 20px rgba(15,23,42,0.05);">
        <div style="font-size:28px; font-weight:900; color:${c.accent};">${c.kicker}</div>
        <div style="font-size:32px; font-weight:900; color:#0F172A; line-height:1.15;">${c.title}</div>
      </div>`
    )
    .join("");

  const cardsScript = callouts
    .map(
      (c, idx) =>
        `    tl.fromTo("#${id}-c${idx + 1}", { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.55, ease: "power3.out" }, ${c.at});`
    )
    .join("\n");

  const bodyHtml = `<div style="width:100%; height:100%; display:grid; grid-template-columns: 470px 1fr; gap:28px; padding:22px 26px; align-items:stretch; background:#F8FAFC;">
    <div style="display:flex; flex-direction:column; justify-content:space-between; gap:18px;">
      ${cardsHtml}
    </div>
    <div id="${id}-browser" style="background:#FFFFFF; border:3.5px solid #16A34A; border-radius:24px; box-shadow:0 18px 40px rgba(15,23,42,0.10); overflow:hidden; display:flex; flex-direction:column;">
      <div style="height:44px; background:#F1F5F9; border-bottom:2px solid #E2E8F0; padding:0 20px; display:flex; align-items:center; justify-content:space-between; flex-shrink:0;">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="width:14px; height:14px; border-radius:50%; background:#EF4444; display:inline-block;"></span>
          <span style="width:14px; height:14px; border-radius:50%; background:#F59E0B; display:inline-block;"></span>
          <span style="width:14px; height:14px; border-radius:50%; background:#22C55E; display:inline-block;"></span>
        </div>
        <div style="width:320px; height:16px; border-radius:999px; background:#E2E8F0;"></div>
        <div style="width:42px; height:14px; border-radius:999px; background:#86EFAC;"></div>
      </div>
      <div style="flex:1; position:relative; background:#FFFFFF; overflow:hidden;">
        <video id="${id}-vid" src="${videoRelPath}" muted playsinline data-start="0" data-duration="${duration}" style="width:100%; height:100%; object-fit:contain; display:block; background:#FFFFFF;"></video>
      </div>
    </div>
  </div>`;

  const headerCombined = badgeHtml
    ? `${titleHtml}</div><div class="badge-green">${badgeHtml}`
    : titleHtml;

  return wrapScene(
    meta,
    headerCombined,
    bodyHtml,
    `
    tl.fromTo("#${id}-browser", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
${cardsScript}
    `,
    true
  );
}

// ---------------------------------------------------------
// ESCENA 01: Infografía moderna AgTech del Huila — Tradición (Arroz & Café) vs Incertidumbre al diversificar
// ---------------------------------------------------------
const s01 = wrapScene(
  SCENE_META[0],
  `<div class="scene-title">¿Sirve mi <span class="accent-green">suelo</span>?</div></div><div class="badge-green">Huila · Agricultura`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: 1fr 1.18fr 1fr; gap:30px; padding:34px 42px; align-items:stretch; background:linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 55%, #F0FDF4 100%);">
    <!-- Tarjeta Izquierda: Arroz (Tradición conocida) -->
    <div id="s01-rice" style="background:#FFFFFF; border:3px solid #86EFAC; border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 16px 36px rgba(22,163,74,0.08);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:68px; height:68px; border-radius:18px; background:#DCFCE7; display:flex; align-items:center; justify-content:center;">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22V8"/><path d="M12 12c-3.5 0-6-2.5-6-6 3.5 0 6 2.5 6 6Z"/><path d="M12 16c3.5 0 6-2.5 6-6-3.5 0-6 2.5-6 6Z"/>
          </svg>
        </div>
        <span style="background:#DCFCE7; color:#166534; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Tradición</span>
      </div>
      <div>
        <div style="font-size:44px; font-weight:900; color:#0F172A; letter-spacing:-0.02em;">Arroz</div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">Cultivo conocido en el valle</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="display:flex; justify-content:space-between; font-size:28px; font-weight:800; color:#166534;"><span>Confianza</span><span>Alta</span></div>
        <div style="width:100%; height:16px; background:#E2E8F0; border-radius:999px; overflow:hidden;">
          <div id="s01-bar-rice" style="width:88%; height:100%; background:linear-gradient(90deg,#16A34A,#22C55E); border-radius:999px;"></div>
        </div>
      </div>
    </div>

    <!-- Tarjeta Central: El Dilema al Probar un Nuevo Cultivo -->
    <div id="s01-question" style="background:#FFFFFF; border:3.5px solid #D97706; border-radius:28px; padding:32px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 22px 48px rgba(217,119,6,0.14); position:relative;">
      <div style="display:flex; align-items:center; gap:18px;">
        <div id="s01-qbadge" style="width:76px; height:76px; border-radius:22px; background:#FEF3C7; border:3px solid #D97706; display:flex; align-items:center; justify-content:center; font-size:44px; font-weight:900; color:#92400E;">?</div>
        <div>
          <div style="font-size:28px; font-weight:900; color:#B45309;">Al diversificar</div>
          <div style="font-size:40px; font-weight:900; color:#0F172A; line-height:1.1;">¿Servirá mi suelo?</div>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:16px;">
        <div id="s01-r1" style="background:#FFF1F2; border:2.5px solid #FDA4AF; border-radius:18px; padding:16px 22px; display:flex; align-items:center; justify-content:space-between;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Inversión y tiempo</span>
          <span style="background:#E11D48; color:#FFFFFF; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Alto riesgo</span>
        </div>
        <div id="s01-r2" style="background:#FFFBEB; border:2.5px solid #FCD34D; border-radius:18px; padding:16px 22px; display:flex; align-items:center; justify-content:space-between;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Respaldo técnico</span>
          <span style="background:#D97706; color:#FFFFFF; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Necesario</span>
        </div>
      </div>

      <div id="s01-foot" style="background:#0F172A; color:#FFFFFF; border-radius:18px; padding:16px 22px; text-align:center; font-size:28px; font-weight:800;">
        Experimentar sin datos cuesta dinero
      </div>
    </div>

    <!-- Tarjeta Derecha: Café (Tradición de ladera) -->
    <div id="s01-coffee" style="background:#FFFFFF; border:3px solid #FCD34D; border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 16px 36px rgba(217,119,6,0.08);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:68px; height:68px; border-radius:18px; background:#FEF3C7; display:flex; align-items:center; justify-content:center;">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#B45309" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
          </svg>
        </div>
        <span style="background:#FEF3C7; color:#92400E; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Tradición</span>
      </div>
      <div>
        <div style="font-size:44px; font-weight:900; color:#0F172A; letter-spacing:-0.02em;">Café</div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">Experiencia heredada en finca</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="display:flex; justify-content:space-between; font-size:28px; font-weight:800; color:#92400E;"><span>Confianza</span><span>Alta</span></div>
        <div style="width:100%; height:16px; background:#E2E8F0; border-radius:999px; overflow:hidden;">
          <div id="s01-bar-coffee" style="width:92%; height:100%; background:linear-gradient(90deg,#D97706,#F59E0B); border-radius:999px;"></div>
        </div>
      </div>
    </div>
  </div>`,
  `
    tl.fromTo("#s01-rice", { opacity: 1, y: 0 }, { opacity: 1, y: 0, duration: 0.2 }, 0);
    tl.fromTo("#s01-bar-rice", { scaleX: 0.2, transformOrigin: "left center" }, { scaleX: 1, duration: 1.2, ease: "power3.out" }, 0.2);
    tl.fromTo("#s01-coffee", { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 1.6);
    tl.fromTo("#s01-bar-coffee", { scaleX: 0.1, transformOrigin: "left center" }, { scaleX: 1, duration: 1.2, ease: "power3.out" }, 2.1);
    tl.fromTo("#s01-question", { opacity: 0, y: 34, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: "power3.out" }, 7.5);
    tl.fromTo("#s01-r1", { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.55, ease: "power3.out" }, 12.2);
    tl.fromTo("#s01-r2", { opacity: 0, x: 24 }, { opacity: 1, x: 0, duration: 0.55, ease: "power3.out" }, 14.5);
    tl.fromTo("#s01-foot", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out" }, 16.0);
  `
);

// ---------------------------------------------------------
// ESCENA 02: Problema actual — 3 barreras modernas con tarjetas editoriales y barras animadas
// ---------------------------------------------------------
const s02 = wrapScene(
  SCENE_META[1],
  `<div class="scene-title">Laboratorio <span class="accent-pink">lejano y costoso</span></div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: repeat(3, 1fr); gap:32px; padding:34px 42px; align-items:stretch; background:linear-gradient(135deg,#FFFFFF 0%,#FFF1F2 100%);">
    <!-- Barrera 1: Distancia Rural -->
    <div id="s02-road" style="background:#FFFFFF; border:3px solid #FDA4AF; border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 16px 36px rgba(225,29,72,0.08);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:72px; height:72px; border-radius:20px; background:#FFE4E6; display:flex; align-items:center; justify-content:center;">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#E11D48" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>
          </svg>
        </div>
        <span style="background:#FFE4E6; color:#BE123C; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Barrera 01</span>
      </div>
      <div>
        <div style="font-size:40px; font-weight:900; color:#0F172A; line-height:1.15;">Laboratorios lejanos</div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:10px;">Difícil acceso desde veredas rurales</div>
      </div>
      <div style="background:#F8FAFC; border:2px solid #E2E8F0; border-radius:18px; padding:18px;">
        <svg width="420" height="46" viewBox="0 0 420 46" fill="none" style="width:100%;">
          <circle cx="24" cy="23" r="10" fill="#16A34A"/>
          <path id="s02-route" d="M40 23 H380" stroke="#E11D48" stroke-width="6" stroke-linecap="round" stroke-dasharray="12 10"/>
          <circle cx="396" cy="23" r="10" fill="#E11D48"/>
        </svg>
        <div style="display:flex; justify-content:space-between; font-size:28px; font-weight:800; color:#334155;"><span>Finca</span><span style="color:#E11D48;">+15 días</span></div>
      </div>
    </div>

    <!-- Barrera 2: Costo y Logística -->
    <div id="s02-cost" style="background:#FFFFFF; border:3px solid #E11D48; border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 18px 40px rgba(225,29,72,0.12);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:72px; height:72px; border-radius:20px; background:#E11D48; display:flex; align-items:center; justify-content:center;">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
        </div>
        <span style="background:#E11D48; color:#FFFFFF; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Barrera 02</span>
      </div>
      <div>
        <div style="font-size:40px; font-weight:900; color:#0F172A; line-height:1.15;">Costo y logística</div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:10px;">Muchos siembran por intuición</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="display:flex; justify-content:space-between; font-size:28px; font-weight:800; color:#BE123C;"><span>Impacto</span><span>Muy alto</span></div>
        <div style="width:100%; height:18px; background:#FFE4E6; border-radius:999px; overflow:hidden;">
          <div id="s02-bar-cost" style="width:92%; height:100%; background:#E11D48; border-radius:999px;"></div>
        </div>
      </div>
    </div>

    <!-- Barrera 3: Sin Historial ni Precios -->
    <div id="s02-notebook" style="background:#FFFFFF; border:3px solid #FCD34D; border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 16px 36px rgba(217,119,6,0.08);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:72px; height:72px; border-radius:20px; background:#FEF3C7; display:flex; align-items:center; justify-content:center;">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#B45309" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <span style="background:#FEF3C7; color:#92400E; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">Barrera 03</span>
      </div>
      <div>
        <div style="font-size:40px; font-weight:900; color:#0F172A; line-height:1.15;">Sin registro ni precios</div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:10px;">Sin evolución ni referencia al vender</div>
      </div>
      <div style="display:flex; gap:12px;">
        <div style="flex:1; background:#FFFBEB; border:2px solid #D97706; color:#92400E; font-size:28px; font-weight:900; padding:12px; border-radius:14px; text-align:center;">Sin historial</div>
        <div style="flex:1; background:#FFF1F2; border:2px solid #E11D48; color:#BE123C; font-size:28px; font-weight:900; padding:12px; border-radius:14px; text-align:center;">Sin precios</div>
      </div>
    </div>
  </div>`,
  `
    tl.fromTo("#s02-road", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 0.3);
    tl.fromTo("#s02-cost", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 4.2);
    tl.fromTo("#s02-bar-cost", { scaleX: 0.1, transformOrigin: "left center" }, { scaleX: 1, duration: 1.0, ease: "power3.out" }, 4.6);
    tl.fromTo("#s02-notebook", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 8.6);
  `
);

// ---------------------------------------------------------
// ESCENA 03: Ecosistema TierSystem — Logo + Sensor IoT + Inteligencia Artificial + 3 Roles
// ---------------------------------------------------------
const s03 = wrapScene(
  SCENE_META[2],
  `<div class="scene-title">Tier<span class="accent-green">System</span> · Sensor + IA</div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: 1fr 1fr 1fr; align-items:stretch; padding: 34px 42px; gap: 30px; background:linear-gradient(135deg,#F0FDF4 0%,#FFFFFF 55%,#FFFBEB 100%);">
    <!-- Panel 1: Plataforma Web PWA -->
    <div id="s03-logo" style="background:#FFFFFF; border:3px solid #16A34A; border-radius:26px; display:flex; flex-direction:column; align-items:center; justify-content:space-between; padding:32px 26px; box-shadow:0 18px 40px rgba(22,163,74,0.10);">
      <span style="background:#DCFCE7; color:#166534; font-size:28px; font-weight:900; padding:6px 20px; border-radius:999px;">Plataforma Web</span>
      <img src="assets/logo_tiersystem.jpg" alt="TierSystem" style="width:190px; height:190px; border-radius:38px; border:4px solid #16A34A; box-shadow:0 16px 34px rgba(22,163,74,0.18); object-fit:cover;" />
      <div style="text-align:center;">
        <div style="font-size:48px; font-weight:900; color:#0F172A; letter-spacing:-0.02em;">Tier<span style="color:#16A34A;">System</span></div>
        <div style="font-size:28px; font-weight:700; color:#475569; margin-top:4px;">Análisis técnico de suelos</div>
      </div>
    </div>

    <!-- Panel 2: Hardware IoT + Motor IA -->
    <div id="s03-sensor" style="background:#FFFFFF; border:3px solid #CBD5E1; border-radius:26px; display:flex; flex-direction:column; justify-content:space-between; padding:32px 26px; box-shadow:0 16px 36px rgba(15,23,42,0.06);">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="width:68px; height:68px; border-radius:18px; background:#EFF6FF; border:2.5px solid #2563EB; display:flex; align-items:center; justify-content:center;">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>
          </svg>
        </div>
        <span style="background:#DBEAFE; color:#1E40AF; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">IoT + IA</span>
      </div>
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div style="background:#F8FAFC; border:2px solid #CBD5E1; border-radius:18px; padding:18px 20px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Sensor ESP32</span>
          <span style="font-size:28px; font-weight:800; color:#16A34A;">7 vars</span>
        </div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:18px; padding:18px 20px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Motor IA</span>
          <span style="font-size:28px; font-weight:800; color:#15803D;">Diagnóstico</span>
        </div>
      </div>
      <div style="background:#0F172A; color:#FFFFFF; font-size:28px; font-weight:800; padding:14px; border-radius:16px; text-align:center;">
        Lectura real + Recomendación
      </div>
    </div>

    <!-- Panel 3: Flujo de 3 Roles -->
    <div id="s03-users" style="background:#FFFFFF; border:3px solid #FCD34D; border-radius:26px; display:flex; flex-direction:column; justify-content:space-between; padding:32px 26px; box-shadow:0 16px 36px rgba(217,119,6,0.08);">
      <span style="align-self:flex-start; background:#FEF3C7; color:#92400E; font-size:28px; font-weight:900; padding:6px 20px; border-radius:999px;">3 Roles Conectados</span>
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div id="s03-r1" style="background:#F0FDF4; border:2.5px solid #16A34A; border-radius:18px; padding:16px 22px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Agricultor</span>
          <span style="font-size:28px; font-weight:900; color:#16A34A;">Solicita</span>
        </div>
        <div id="s03-r2" style="background:#FFFBEB; border:2.5px solid #D97706; border-radius:18px; padding:16px 22px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Laboratorista</span>
          <span style="font-size:28px; font-weight:900; color:#D97706;">Analiza</span>
        </div>
        <div id="s03-r3" style="background:#FFF1F2; border:2.5px solid #E11D48; border-radius:18px; padding:16px 22px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:30px; font-weight:900; color:#0F172A;">Administrador</span>
          <span style="font-size:28px; font-weight:900; color:#E11D48;">Supervisa</span>
        </div>
      </div>
      <div style="font-size:28px; font-weight:800; color:#475569; text-align:center;">Flujo organizado de principio a fin</div>
    </div>
  </div>`,
  `
    tl.fromTo("#s03-logo", { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 0.3);
    tl.fromTo("#s03-sensor", { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 4.6);
    tl.fromTo("#s03-users", { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" }, 8.6);
    tl.fromTo("#s03-r1", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, 10.2);
    tl.fromTo("#s03-r2", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, 11.4);
    tl.fromTo("#s03-r3", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, 12.6);
  `
);

// ---------------------------------------------------------
// ESCENA 04: Tres tarjetas modernas por rol con checklist animado
// ---------------------------------------------------------
const s04 = wrapScene(
  SCENE_META[3],
  `<div class="scene-title">Tres <span class="accent-green">roles</span> conectados</div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: repeat(3, 1fr); gap: 32px; padding: 34px 42px; align-items:stretch; background:#F8FAFC;">
    <!-- Tarjeta 1: Agricultor -->
    <div id="s04-c1" style="background:#FFFFFF; border:3.5px solid #16A34A; box-shadow:0 16px 36px rgba(22,163,74,0.10); border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between;">
      <div style="display:flex; align-items:center; gap:18px;">
        <div style="width:68px; height:68px; border-radius:18px; background:#DCFCE7; display:flex; align-items:center; justify-content:center;">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
        <div style="font-size:40px; font-weight:900; color:#0F172A;">Agricultor</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div style="background:#F0FDF4; border:2px solid #86EFAC; color:#166534; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Autoregistro rápido</div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; color:#166534; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Administra terrenos</div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; color:#166534; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Solicita análisis</div>
      </div>
      <div style="background:#16A34A; color:#FFFFFF; font-size:30px; font-weight:900; padding:14px; border-radius:999px; text-align:center;">Usuario Final</div>
    </div>

    <!-- Tarjeta 2: Laboratorista -->
    <div id="s04-c2" style="background:#FFFFFF; border:3.5px solid #D97706; box-shadow:0 16px 36px rgba(217,119,6,0.10); border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between;">
      <div style="display:flex; align-items:center; gap:18px;">
        <div style="width:68px; height:68px; border-radius:18px; background:#FEF3C7; display:flex; align-items:center; justify-content:center;">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#B45309" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 2v7.31"/><path d="M14 9.3V1.99"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/>
          </svg>
        </div>
        <div style="font-size:40px; font-weight:900; color:#0F172A;">Laboratorista</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div style="background:#FFFBEB; border:2px solid #FCD34D; color:#92400E; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Opera sensor ESP32</div>
        <div style="background:#FFFBEB; border:2px solid #FCD34D; color:#92400E; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Captura en campo</div>
        <div style="background:#FFFBEB; border:2px solid #FCD34D; color:#92400E; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Comparte resultados</div>
      </div>
      <div style="background:#D97706; color:#FFFFFF; font-size:30px; font-weight:900; padding:14px; border-radius:999px; text-align:center;">Operación Técnica</div>
    </div>

    <!-- Tarjeta 3: Administrador -->
    <div id="s04-c3" style="background:#FFFFFF; border:3.5px solid #E11D48; box-shadow:0 16px 36px rgba(225,29,72,0.10); border-radius:26px; padding:30px; display:flex; flex-direction:column; justify-content:space-between;">
      <div style="display:flex; align-items:center; gap:18px;">
        <div style="width:68px; height:68px; border-radius:18px; background:#FFE4E6; display:flex; align-items:center; justify-content:center;">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#BE123C" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </div>
        <div style="font-size:40px; font-weight:900; color:#0F172A;">Administrador</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div style="background:#FFF1F2; border:2px solid #FDA4AF; color:#9F1239; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Gestiona cuentas</div>
        <div style="background:#FFF1F2; border:2px solid #FDA4AF; color:#9F1239; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Configura rangos IA</div>
        <div style="background:#FFF1F2; border:2px solid #FDA4AF; color:#9F1239; font-size:28px; font-weight:800; padding:12px 18px; border-radius:14px;">✓ Supervisa operación</div>
      </div>
      <div style="background:#E11D48; color:#FFFFFF; font-size:30px; font-weight:900; padding:14px; border-radius:999px; text-align:center;">Control Global</div>
    </div>
  </div>`,
  `
    tl.fromTo("#s04-c1", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.3);
    tl.fromTo("#s04-c2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 5.5);
    tl.fromTo("#s04-c3", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 10.0);
  `
);

// ---------------------------------------------------------
// ESCENA 05: Grabación real del sistema — Mis Terrenos y Solicitudes del Agricultor
// ---------------------------------------------------------
const s05 = wrapScreenScene(
  SCENE_META[4],
  `<div class="scene-title">Registro y <span class="accent-green">solicitud</span></div>`,
  "Captura real",
  "assets/capturas/escena_05_terrenos.mp4",
  [
    { kicker: "Paso 1 · Terrenos", title: "Nombre, ubicación y área", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 0.4 },
    { kicker: "Paso 2 · Solicitud", title: "Cultivo y visita o muestra", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 5.5 },
    { kicker: "Control activo", title: "1 solicitud activa · Cancelable", bg: "#FFFFFF", border: "#94A3B8", accent: "#334155", at: 11.5 },
  ]
);

// ---------------------------------------------------------
// ESCENA 06: Grabación real del sistema — Bandeja de Solicitudes del Laboratorista
// ---------------------------------------------------------
const s06 = wrapScreenScene(
  SCENE_META[5],
  `<div class="scene-title">Estados de la <span class="accent-orange">solicitud</span></div>`,
  "Captura real",
  "assets/capturas/escena_06_solicitudes.mp4",
  [
    { kicker: "Bandeja técnica", title: "Revisa solicitudes pendientes", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 0.3 },
    { kicker: "Agenda de atención", title: "Acepta, rechaza y programa", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 3.2 },
    { kicker: "Notificaciones", title: "Aviso en cada cambio", bg: "#FFFFFF", border: "#16A34A", accent: "#15803D", at: 6.4 },
  ]
);

// ---------------------------------------------------------
// ESCENA 07: Sonda clavada en la tierra, esquema ESP32 + sonda y siete contadores: pH, N, P, K, humedad, CE, temperatura
// ---------------------------------------------------------
const s07 = wrapScene(
  SCENE_META[6],
  `<div class="scene-title">ESP32 + Sonda <span class="accent-green">RS485</span></div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: 0.88fr 1.12fr; gap: 40px; padding: 32px 52px; align-items:center;">
    <!-- Esquema ESP32 + Sonda 5 puntas clavada en la tierra -->
    <div style="height:100%; background:#F8FAFC; border:2.5px solid #CBD5E1; border-radius:26px; display:flex; align-items:center; justify-content:center;">
      <svg width="640" height="580" viewBox="0 0 640 580" fill="none">
        <!-- Módulo ESP32 WiFi/BT -->
        <g id="s07-esp">
          <rect x="36" y="48" width="220" height="130" rx="20" fill="#FFFFFF" stroke="#D97706" stroke-width="4" />
          <rect x="58" y="72" width="105" height="82" rx="10" fill="#FEF3C7" stroke="#D97706" stroke-width="2.5" />
          <text x="110" y="122" text-anchor="middle" fill="#92400E" font-size="28" font-weight="900" font-family="Inter">ESP32</text>
          <path d="M185 98 C202 98 212 108 212 125" stroke="#16A34A" stroke-width="5" stroke-linecap="round" />
          <path d="M185 78 C214 78 232 98 232 125" stroke="#16A34A" stroke-width="5" stroke-linecap="round" />
        </g>
        <!-- Cable RS485 -->
        <path d="M256 115 H405 V135" stroke="#D97706" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />

        <!-- Suelo en capas -->
        <rect x="160" y="365" width="445" height="185" rx="22" fill="#DCFCE7" stroke="#16A34A" stroke-width="3.5" />
        <line x1="160" y1="365" x2="605" y2="365" stroke="#15803D" stroke-width="6" />
        <!-- Ondas de pulso en tierra -->
        <circle id="s07-wave" cx="405" cy="450" r="65" stroke="#16A34A" stroke-width="3.5" stroke-dasharray="10 8" fill="none" />

        <!-- Sonda real 5 puntas -->
        <g id="s07-probe">
          <rect x="330" y="135" width="150" height="150" rx="18" fill="#1E293B" stroke="#0F172A" stroke-width="4" />
          <rect x="352" y="155" width="106" height="110" rx="10" fill="#3B82F6" stroke="#60A5FA" stroke-width="2.5" />
          <line x1="350" y1="285" x2="350" y2="445" stroke="#475569" stroke-width="8" stroke-linecap="round" />
          <line x1="377" y1="285" x2="377" y2="445" stroke="#64748B" stroke-width="8" stroke-linecap="round" />
          <line x1="405" y1="285" x2="405" y2="445" stroke="#1E293B" stroke-width="8" stroke-linecap="round" />
          <line x1="433" y1="285" x2="433" y2="445" stroke="#64748B" stroke-width="8" stroke-linecap="round" />
          <line x1="460" y1="285" x2="460" y2="445" stroke="#475569" stroke-width="8" stroke-linecap="round" />
        </g>
      </svg>
    </div>

    <!-- 7 tarjetas detalladas de parámetros con lectura en vivo -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 18px;">
      <div id="s07-p1" style="background:#F0FDF4; border:3px solid #16A34A; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:30px; font-weight:800; color:#166534;">pH</div>
        <div style="font-size:46px; font-weight:900; color:#0F172A;">6.4</div>
      </div>
      <div id="s07-p2" style="background:#F0FDF4; border:3px solid #16A34A; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:30px; font-weight:800; color:#166534;">N</div>
        <div style="font-size:46px; font-weight:900; color:#0F172A;">45</div>
      </div>
      <div id="s07-p3" style="background:#F0FDF4; border:3px solid #16A34A; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:30px; font-weight:800; color:#166534;">P</div>
        <div style="font-size:46px; font-weight:900; color:#0F172A;">32</div>
      </div>
      <div id="s07-p4" style="background:#F0FDF4; border:3px solid #16A34A; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:30px; font-weight:800; color:#166534;">K</div>
        <div style="font-size:46px; font-weight:900; color:#0F172A;">180</div>
      </div>
      <div id="s07-p5" style="background:#FFFBEB; border:3px solid #D97706; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:28px; font-weight:800; color:#92400E;">Humedad</div>
        <div style="font-size:44px; font-weight:900; color:#0F172A;">68%</div>
      </div>
      <div id="s07-p6" style="background:#FFFBEB; border:3px solid #D97706; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:28px; font-weight:800; color:#92400E;">CE</div>
        <div style="font-size:44px; font-weight:900; color:#0F172A;">1.4</div>
      </div>
      <div id="s07-p7" style="grid-column: span 2; background:#FFF1F2; border:3px solid #E11D48; border-radius:22px; padding:24px 16px; text-align:center; display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:28px; font-weight:800; color:#9F1239;">Temperatura</div>
        <div style="font-size:44px; font-weight:900; color:#0F172A;">24 °C</div>
      </div>
    </div>
  </div>`,
  `
    tl.fromTo("#s07-esp", { opacity: 0 }, { opacity: 1, duration: 0.6, ease: "power3.out" }, 0.3);
    tl.fromTo("#s07-probe", { y: -40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.9, ease: "power3.out" }, 3.8);
    tl.fromTo("#s07-wave", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 4.7);
    ["#s07-p1", "#s07-p2", "#s07-p3", "#s07-p4", "#s07-p5", "#s07-p6", "#s07-p7"].forEach((sel, idx) => {
      tl.fromTo(sel, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, 9.2 + idx * 0.8);
    });
  `
);

// ---------------------------------------------------------
// ESCENA 08: Grabación real del sistema — Toma de muestras en campo
// ---------------------------------------------------------
const s08 = wrapScreenScene(
  SCENE_META[7],
  `<div class="scene-title">Muestreo y <span class="accent-green">perfil promedio</span></div>`,
  "Captura real",
  "assets/capturas/escena_08_muestreo.mp4",
  [
    { kicker: "Puntos sugeridos", title: "Según el área del terreno", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 0.4 },
    { kicker: "Validación automática", title: "Verifica rangos por punto", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 6.2 },
    { kicker: "Perfil consolidado", title: "Calcula el promedio real", bg: "#FFFFFF", border: "#16A34A", accent: "#15803D", at: 12.0 },
  ]
);

// ---------------------------------------------------------
// ESCENA 09: Grabación real del sistema — Resultado de Compatibilidad con IA
// ---------------------------------------------------------
const s09 = wrapScreenScene(
  SCENE_META[8],
  `<div class="scene-title">Compatibilidad <span class="accent-green">con IA</span></div>`,
  "Captura real",
  "assets/capturas/escena_09_resultado_ia.mp4",
  [
    { kicker: "Evaluación IA", title: "Porcentaje Alta, Media o Baja", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 0.4 },
    { kicker: "Semáforo técnico", title: "Óptimo, deficiente o excesivo", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 8.5 },
    { kicker: "Guía práctica", title: "Mejoras y cultivos alternativos", bg: "#FFF1F2", border: "#E11D48", accent: "#BE123C", at: 16.5 },
  ]
);

// ---------------------------------------------------------
// ESCENA 10: Celular recibiendo una notificación con el resultado
// ---------------------------------------------------------
const s10 = wrapScene(
  SCENE_META[9],
  `<div class="scene-title">Resultado en <span class="accent-green">tiempo real</span></div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: 1fr 1fr; gap: 44px; padding: 36px 64px; align-items:center;">
    <!-- Vista Laboratorista: Botón Compartir Diagnóstico -->
    <div id="s10-lab" style="background:#F8FAFC; border:3px solid #CBD5E1; border-radius:28px; padding:36px; display:flex; flex-direction:column; gap:24px;">
      <div style="font-size:34px; font-weight:900; color:#0F172A;">Revisión del Laboratorista</div>
      <div style="background:#FFFFFF; border:2px solid #86EFAC; border-radius:20px; padding:24px; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:32px; font-weight:800; color:#166534;">Informe #104 · Café</span>
        <span style="background:#DCFCE7; color:#15803D; font-size:28px; font-weight:900; padding:6px 18px; border-radius:999px;">86%</span>
      </div>
      <div style="background:#16A34A; color:#FFFFFF; font-size:32px; font-weight:900; padding:20px; border-radius:20px; text-align:center; box-shadow:0 10px 24px rgba(22,163,74,0.22);">
        Compartir con Agricultor →
      </div>
    </div>

    <!-- Celular del Agricultor recibiendo la notificación -->
    <div id="s10-phone" style="background:#FFFFFF; border:4px solid #16A34A; box-shadow:0 18px 40px rgba(22,163,74,0.14); border-radius:40px; padding:32px; height:560px; display:flex; flex-direction:column; justify-content:space-between;">
      <div id="s10-notif" style="background:#ECFDF5; border:3px solid #16A34A; border-radius:22px; padding:22px; display:flex; align-items:center; gap:20px;">
        <div style="width:64px; height:64px; border-radius:50%; background:#16A34A; color:#FFFFFF; font-size:32px; font-weight:900; display:flex; align-items:center; justify-content:center;">🔔</div>
        <div>
          <div style="font-size:30px; font-weight:900; color:#0F172A;">¡Resultado Listo!</div>
          <div style="font-size:28px; font-weight:700; color:#15803D;">Finca El Paraíso · 86%</div>
        </div>
      </div>

      <div id="s10-summary" style="background:#F8FAFC; border:2px solid #E2E8F0; border-radius:22px; padding:26px; display:flex; flex-direction:column; gap:16px;">
        <div style="font-size:32px; font-weight:900; color:#0F172A;">Decisión con Datos Técnicos</div>
        <div style="display:flex; gap:14px;">
          <span style="background:#DCFCE7; color:#166534; font-size:28px; font-weight:800; padding:8px 20px; border-radius:999px;">Fertilización</span>
          <span style="background:#FEF3C7; color:#92400E; font-size:28px; font-weight:800; padding:8px 20px; border-radius:999px;">Cultivos</span>
        </div>
      </div>
    </div>
  </div>`,
  `
    tl.fromTo("#s10-lab", { opacity: 0, x: -25 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 0.3);
    tl.fromTo("#s10-phone", { opacity: 0, x: 25 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 2.2);
    tl.fromTo("#s10-notif", { opacity: 0, y: -20 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 4.2);
    tl.fromTo("#s10-summary", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, 6.8);
  `
);

// ---------------------------------------------------------
// ESCENA 11: Ícono de wifi tachado, nube que se reconecta y etiqueta "Modo local"
// ---------------------------------------------------------
const s11 = wrapScene(
  SCENE_META[10],
  `<div class="scene-title">Operación sin <span class="accent-orange">internet</span></div></div><div class="badge-pill">Modo local`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: repeat(3, 1fr); gap: 36px; padding: 42px 52px; align-items:stretch;">
    <!-- 1. Zona rural sin señal (WiFi tachado) -->
    <div id="s11-wifi" style="background:#FFFBEB; border:3.5px solid #D97706; border-radius:28px; padding:36px 24px; display:flex; flex-direction:column; align-items:center; justify-content:space-between; text-align:center;">
      <svg width="160" height="160" viewBox="0 0 160 160" fill="none">
        <path d="M26 64 C58 36 102 36 134 64" stroke="#D97706" stroke-width="9" stroke-linecap="round" />
        <path d="M46 88 C66 70 94 70 114 88" stroke="#D97706" stroke-width="9" stroke-linecap="round" />
        <circle cx="80" cy="122" r="9" fill="#D97706" />
        <line x1="34" y1="34" x2="126" y2="126" stroke="#E11D48" stroke-width="11" stroke-linecap="round" />
      </svg>
      <div style="font-size:38px; font-weight:900; color:#0F172A;">Sin Internet</div>
      <div style="background:#FEF3C7; color:#92400E; font-size:28px; font-weight:800; padding:10px 24px; border-radius:999px;">Captura en Campo</div>
    </div>

    <!-- 2. Motor Agronómico Local -->
    <div id="s11-engine" style="background:#F0FDF4; border:3.5px solid #16A34A; border-radius:28px; padding:36px 24px; display:flex; flex-direction:column; align-items:center; justify-content:space-between; text-align:center;">
      <svg width="160" height="160" viewBox="0 0 160 160" fill="none">
        <rect x="30" y="30" width="100" height="100" rx="22" fill="#FFFFFF" stroke="#16A34A" stroke-width="7" />
        <path d="M56 82 L74 100 L108 62" stroke="#16A34A" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <div style="font-size:38px; font-weight:900; color:#0F172A;">Motor Local</div>
      <div style="background:#DCFCE7; color:#166534; font-size:28px; font-weight:800; padding:10px 24px; border-radius:999px;">Rangos Agronómicos</div>
    </div>

    <!-- 3. Nube que se reconecta y sincroniza -->
    <div id="s11-cloud" style="background:#EFF6FF; border:3.5px solid #2563EB; border-radius:28px; padding:36px 24px; display:flex; flex-direction:column; align-items:center; justify-content:space-between; text-align:center;">
      <svg width="160" height="160" viewBox="0 0 160 160" fill="none">
        <path d="M45 122 H118 C134 122 144 108 140 92 C137 78 125 68 112 70 C104 50 82 40 64 48 C48 54 40 70 40 82 C26 84 18 96 20 108 C22 116 32 122 45 122 Z" fill="#FFFFFF" stroke="#2563EB" stroke-width="7" stroke-linejoin="round" />
        <path d="M82 108 V72 M66 86 L82 70 L98 86" stroke="#16A34A" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <div style="font-size:38px; font-weight:900; color:#0F172A;">Sincronización</div>
      <div style="background:#DBEAFE; color:#1E40AF; font-size:28px; font-weight:800; padding:10px 24px; border-radius:999px;">Automática</div>
    </div>
  </div>`,
  `
    tl.fromTo("#s11-wifi", { opacity: 0, y: 25 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.3);
    tl.fromTo("#s11-engine", { opacity: 0, y: 25 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 6.8);
    tl.fromTo("#s11-cloud", { opacity: 0, y: 25 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 16.0);
  `
);

// ---------------------------------------------------------
// ESCENA 12: Grabación real del sistema — Historial y comparación de análisis
// ---------------------------------------------------------
const s12 = wrapScreenScene(
  SCENE_META[11],
  `<div class="scene-title">Historial y <span class="accent-green">comparación</span></div>`,
  "Captura real",
  "assets/capturas/escena_12_historial.mp4",
  [
    { kicker: "Historial completo", title: "Todos los análisis guardados", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 0.3 },
    { kicker: "Evolución del suelo", title: "Mejoras en verde · Alertas en rojo", bg: "#FFF1F2", border: "#E11D48", accent: "#BE123C", at: 4.0 },
    { kicker: "Exportación", title: "Descarga en PDF y Excel", bg: "#FFFFFF", border: "#16A34A", accent: "#15803D", at: 7.5 },
  ]
);

// ---------------------------------------------------------
// ESCENA 13: Grabación real del sistema — Precios SIPSA DANE y compradores
// ---------------------------------------------------------
const s13 = wrapScreenScene(
  SCENE_META[12],
  `<div class="scene-title">Precios y <span class="accent-green">compradores</span></div>`,
  "Captura real",
  "assets/capturas/escena_13_mercado.mp4",
  [
    { kicker: "Referencia SIPSA · DANE", title: "Precio oficial del cultivo", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 0.4 },
    { kicker: "Últimas 3 semanas", title: "Evolución y tendencia", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 4.6 },
    { kicker: "Comercialización", title: "Compradores activos del Huila", bg: "#FFFFFF", border: "#16A34A", accent: "#15803D", at: 9.2 },
  ]
);

// ---------------------------------------------------------
// ESCENA 14: Grabación real del sistema — Panel de administrador, hardware y configuración
// ---------------------------------------------------------
const s14 = wrapScreenScene(
  SCENE_META[13],
  `<div class="scene-title">Panel del <span class="accent-orange">administrador</span></div>`,
  "Captura real",
  "assets/capturas/escena_14_admin.mp4",
  [
    { kicker: "Gobernanza", title: "Rangos, cultivos y timeout IA", bg: "#FFFBEB", border: "#D97706", accent: "#92400E", at: 0.3 },
    { kicker: "Telemetría IoT", title: "Estado del sensor y batería", bg: "#F0FDF4", border: "#16A34A", accent: "#166534", at: 4.8 },
    { kicker: "Reportes ejecutivos", title: "Exportación PDF y Excel", bg: "#FFF1F2", border: "#E11D48", accent: "#BE123C", at: 9.2 },
  ]
);

// ---------------------------------------------------------
// ESCENA 15: Seguridad (Ley 1581 + Roles + HTTPS) y Diseño PWA Adaptable
// ---------------------------------------------------------
const s15 = wrapScene(
  SCENE_META[14],
  `<div class="scene-title">Seguridad y <span class="accent-green">diseño adaptable</span></div>`,
  `<div style="width:100%; height:100%; display:grid; grid-template-columns: 0.92fr 1.08fr; gap: 36px; padding: 34px 44px; align-items:stretch; background:#F8FAFC;">
    <!-- Protección de datos Ley 1581 -->
    <div id="s15-lock" style="background:#FFFFFF; border:3px solid #16A34A; border-radius:26px; display:flex; flex-direction:column; justify-content:space-between; padding:32px; box-shadow:0 16px 36px rgba(22,163,74,0.08);">
      <div style="display:flex; align-items:center; gap:18px;">
        <div style="width:74px; height:74px; border-radius:20px; background:#DCFCE7; display:flex; align-items:center; justify-content:center;">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#15803D" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>
          </svg>
        </div>
        <div>
          <div style="font-size:28px; font-weight:900; color:#15803D;">Protección Legal</div>
          <div style="font-size:38px; font-weight:900; color:#0F172A;">Ley 1581 de 2012</div>
        </div>
      </div>
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:16px; padding:16px 22px; font-size:28px; font-weight:800; color:#166534;">✓ Control de acceso por roles</div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:16px; padding:16px 22px; font-size:28px; font-weight:800; color:#166534;">✓ Comunicación cifrada HTTPS</div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:16px; padding:16px 22px; font-size:28px; font-weight:800; color:#166534;">✓ Privacidad de fincas y datos</div>
      </div>
    </div>

    <!-- Dispositivos PWA (Tableta + Celular modernos en HTML/CSS) -->
    <div id="s15-devices" style="background:#FFFFFF; border:3px solid #CBD5E1; border-radius:26px; padding:30px 34px; display:flex; align-items:flex-end; justify-content:center; gap:30px; box-shadow:0 16px 36px rgba(15,23,42,0.06);">
      <!-- Tableta -->
      <div style="flex:1; height:490px; background:#F8FAFC; border:4px solid #16A34A; border-radius:28px; padding:24px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 12px 28px rgba(22,163,74,0.10);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:28px; font-weight:900; color:#0F172A;">Tableta · PWA</span>
          <span style="background:#DCFCE7; color:#15803D; font-size:28px; font-weight:900; padding:4px 16px; border-radius:999px;">86%</span>
        </div>
        <div style="background:#FFFFFF; border:2px solid #E2E8F0; border-radius:18px; padding:20px; display:flex; flex-direction:column; gap:14px;">
          <div style="height:18px; width:82%; background:#16A34A; border-radius:999px;"></div>
          <div style="height:18px; width:64%; background:#D97706; border-radius:999px;"></div>
          <div style="height:18px; width:90%; background:#22C55E; border-radius:999px;"></div>
        </div>
        <div style="background:#16A34A; color:#FFFFFF; font-size:28px; font-weight:900; padding:12px; border-radius:16px; text-align:center;">Instalable como App</div>
      </div>

      <!-- Celular -->
      <div style="width:270px; height:410px; background:#FFFFFF; border:4px solid #D97706; border-radius:30px; padding:20px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 12px 28px rgba(217,119,6,0.12);">
        <div style="width:68px; height:8px; background:#CBD5E1; border-radius:999px; align-self:center;"></div>
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:18px; padding:16px; text-align:center;">
          <div style="font-size:40px; font-weight:900; color:#15803D;">86%</div>
          <div style="font-size:28px; font-weight:800; color:#166534;">Óptimo</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div style="height:14px; width:100%; background:#16A34A; border-radius:999px;"></div>
          <div style="height:14px; width:72%; background:#D97706; border-radius:999px;"></div>
        </div>
        <div style="background:#FEF3C7; color:#92400E; font-size:28px; font-weight:900; padding:8px; border-radius:14px; text-align:center;">Móvil</div>
      </div>
    </div>
  </div>`,
  `
    tl.fromTo("#s15-lock", { opacity: 0, x: -28 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 0.3);
    tl.fromTo("#s15-devices", { opacity: 0, x: 28 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 5.6);
  `
);

// ---------------------------------------------------------
// ESCENA 16: Cierre editorial limpio SIN SENA ni tecnólogo + fundido a BLANCO
// ---------------------------------------------------------
const s16 = `<template>
  <style>${COMMON_STYLE}
    #s16-whiteout {
      position: absolute;
      inset: 0;
      background: #FFFFFF;
      opacity: 0;
      pointer-events: none;
      z-index: 30;
    }
  </style>
  <div id="root" data-composition-id="scene16" data-width="1920" data-height="1080">
    <div id="scene16-clip" class="clip" data-start="0" data-duration="${SCENE_META[15].duration}" data-track-index="0">
      <div class="safe-stage">
        <div id="scene16-hdr" class="scene-header">
          <div class="title-group">
            <span class="step-num">16</span>
            <div class="scene-title">Decisiones basadas <span class="accent-green">en datos</span></div>
          </div>
          <div class="badge-green">Agricultura Inteligente</div>
        </div>
        <div id="scene16-stage" class="illus-card" data-layout-allow-overflow style="flex-direction:column; justify-content:space-between; padding: 48px 56px; background:linear-gradient(135deg,#F0FDF4 0%,#FFFFFF 50%,#FFFBEB 100%);">
          <!-- Hero central TierSystem -->
          <div id="s16-logos" style="display:flex; align-items:center; gap:38px; background:#FFFFFF; border:3.5px solid #16A34A; padding:28px 56px; border-radius:34px; box-shadow:0 20px 48px rgba(22,163,74,0.14);">
            <img src="assets/logo_tiersystem.jpg" alt="TierSystem" style="width:152px; height:152px; border-radius:32px; border:4px solid #16A34A; object-fit:cover;" />
            <div>
              <div style="font-size:80px; font-weight:900; color:#0F172A; letter-spacing:-0.03em; line-height:1;">Tier<span style="color:#16A34A;">System</span></div>
              <div style="font-size:30px; font-weight:800; color:#475569; margin-top:8px;">Datos reales para decidir mejor</div>
            </div>
          </div>

          <!-- 4 pilares animados del resumen -->
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:24px; width:100%;">
            <div id="s16-p1" style="background:#FFFFFF; border:3px solid #16A34A; border-radius:22px; padding:24px; text-align:center; box-shadow:0 10px 24px rgba(22,163,74,0.08);">
              <div style="font-size:32px; font-weight:900; color:#166534;">Conocer Suelo</div>
              <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">7 parámetros</div>
            </div>
            <div id="s16-p2" style="background:#FFFFFF; border:3px solid #16A34A; border-radius:22px; padding:24px; text-align:center; box-shadow:0 10px 24px rgba(22,163,74,0.08);">
              <div style="font-size:32px; font-weight:900; color:#166534;">Recomendación</div>
              <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">Asistida con IA</div>
            </div>
            <div id="s16-p3" style="background:#FFFFFF; border:3px solid #D97706; border-radius:22px; padding:24px; text-align:center; box-shadow:0 10px 24px rgba(217,119,6,0.08);">
              <div style="font-size:32px; font-weight:900; color:#92400E;">Seguimiento</div>
              <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">Historial real</div>
            </div>
            <div id="s16-p4" style="background:#FFFFFF; border:3px solid #D97706; border-radius:22px; padding:24px; text-align:center; box-shadow:0 10px 24px rgba(217,119,6,0.08);">
              <div style="font-size:32px; font-weight:900; color:#92400E;">Mercado Real</div>
              <div style="font-size:28px; font-weight:700; color:#475569; margin-top:6px;">SIPSA · DANE</div>
            </div>
          </div>
        </div>
      </div>
      <div id="s16-whiteout" data-layout-allow-occlusion></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#scene16-clip", { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out" }, 0);
    tl.fromTo("#s16-logos", { opacity: 0, y: 24, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: "power3.out" }, 0.3);
    tl.fromTo("#s16-p1", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 4.2);
    tl.fromTo("#s16-p2", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 5.6);
    tl.fromTo("#s16-p3", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 7.0);
    tl.fromTo("#s16-p4", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 8.4);
    tl.fromTo("#s16-whiteout", { opacity: 0 }, { opacity: 1, duration: 1.0, ease: "power2.inOut" }, ${Number((SCENE_META[15].duration - 1.0).toFixed(3))});
    window.__timelines["scene16"] = tl;
  </script>
</template>
`;

const SCENE_CONTENTS = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14, s15, s16];

for (let i = 0; i < 16; i++) {
  const meta = SCENE_META[i];
  const filePath = path.join(compsDir, `${meta.id}.html`);
  fs.writeFileSync(filePath, SCENE_CONTENTS[i], "utf8");
}

// ---------------------------------------------------------
// GENERAR CAPTIONS.HTML (Tema blanco limpio de alto contraste)
// ---------------------------------------------------------
function buildGroupsForScene(meta) {
  const wordsPath = path.join(assetsDir, `escena_${meta.code}.words.json`);
  const words = JSON.parse(fs.readFileSync(wordsPath, "utf8"));
  const groups = [];
  let current = [];

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const absWord = {
      id: `s${meta.code}_${w.id}`,
      text: w.text,
      start: Number((meta.start + w.start).toFixed(3)),
      end: Number((meta.start + w.end).toFixed(3)),
    };
    current.push(absWord);

    const next = words[i + 1];
    const endsSentence = /[.?!:;]$/.test(w.text);
    const hasPause = next ? next.start - w.end >= 0.22 : true;
    const hitLimit = current.length >= 6;

    if (endsSentence || hasPause || hitLimit || !next) {
      const gStart = current[0].start;
      const gEnd = Math.min(meta.end - 0.05, current[current.length - 1].end + 0.12);
      groups.push({
        id: `cap_s${meta.code}_g${groups.length}`,
        start: Number(gStart.toFixed(3)),
        end: Number(gEnd.toFixed(3)),
        words: current,
      });
      current = [];
    }
  }
  return groups;
}

const allGroups = [];
for (const meta of SCENE_META) {
  allGroups.push(...buildGroupsForScene(meta));
}

for (let i = 0; i < allGroups.length - 1; i++) {
  if (allGroups[i].end > allGroups[i + 1].start) {
    allGroups[i].end = Number((allGroups[i + 1].start - 0.02).toFixed(3));
  }
}

let htmlGroups = "";
for (const g of allGroups) {
  const spans = g.words
    .map((w) => `<span id="${w.id}" class="cap-word">${w.text}</span>`)
    .join(" ");
  htmlGroups += `      <div id="${g.id}" class="cap-group" data-layout-allow-caption-zone><div class="cap-pill">${spans}</div></div>\n`;
}

const captionsHtml = `<template>
  <style>
    #root {
      position: absolute;
      inset: 0;
      pointer-events: none;
      font-family: "Inter", sans-serif;
      overflow: visible;
    }
    .captions-band {
      position: absolute;
      left: 140px;
      right: 140px;
      bottom: 78px;
      height: 84px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: visible;
    }
    .cap-group {
      position: absolute;
      left: 0;
      right: 0;
      text-align: center;
      opacity: 0;
      visibility: hidden;
      overflow: visible;
    }
    .cap-pill {
      display: inline-block;
      background: #FFFFFF;
      border: 3px solid #16A34A;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
      padding: 12px 28px;
      border-radius: 18px;
      font-size: 36px;
      font-weight: 800;
      line-height: 1.25;
      color: #0F172A;
    }
    .cap-word {
      display: inline-block;
      color: #0F172A;
      padding: 0 5px;
      border-radius: 8px;
    }
  </style>

  <div id="root" data-composition-id="captions" data-width="1920" data-height="1080">
    <div id="cap-clip" class="clip" data-start="0" data-duration="${TOTAL_DURATION}" data-track-index="0">
      <div class="captions-band" data-layout-allow-caption-zone>
${htmlGroups}      </div>
    </div>
  </div>

  <script>
    const tl = gsap.timeline({ paused: true });
    const groups = ${JSON.stringify(allGroups)};

    groups.forEach((g) => {
      const gSel = "#" + g.id;
      const openAt = Math.max(0.05, g.start);
      tl.set(gSel, { visibility: "visible", opacity: 1 }, openAt);

      g.words.forEach((w) => {
        const wSel = "#" + w.id;
        const wStart = Math.max(openAt, w.start);
        const wDur = Math.max(0.07, w.end - w.start);
        tl.to(wSel, { color: "#15803D", backgroundColor: "#DCFCE7", duration: 0.05, ease: "none" }, wStart);
        tl.to(wSel, { color: "#0F172A", backgroundColor: "rgba(220,252,231,0)", duration: 0.06, ease: "none" }, wStart + wDur);
      });

      const maxEnd = Math.min(g.end, ${Number((TOTAL_DURATION - 1.05).toFixed(3))});
      const fadeStart = Math.max(openAt + 0.05, maxEnd - 0.1);
      tl.to(gSel, { opacity: 0, duration: 0.1, ease: "power2.in" }, fadeStart);
      tl.set(gSel, { opacity: 0, visibility: "hidden" }, maxEnd);
    });

    window.__timelines["captions"] = tl;
  </script>
</template>
`;

fs.writeFileSync(path.join(compsDir, "captions.html"), captionsHtml, "utf8");

// ---------------------------------------------------------
// GENERAR INDEX.HTML RAÍZ (FONDO BLANCO #FFFFFF + BGM + MOTION SFX)
// ---------------------------------------------------------
let sceneHostsHtml = "";
let audioClipsHtml = "";
let sfxClipsHtml = "";

// Música ambiental suave durante todo el video (volumen equilibrado para no tapar la narración)
audioClipsHtml += `      <audio id="bgm-main" class="clip" src="assets/sfx/bgm_ambient.mp3" data-start="0" data-duration="${TOTAL_DURATION}" data-track-index="4" data-volume="0.14"></audio>\n`;

// Efectos de sonido (whoosh en cambios de escena, pop en entradas de tarjetas, chime en hitos)
// Todos en lane 5 sin solaparse
let sfxIdx = 0;
for (let i = 0; i < SCENE_META.length; i++) {
  const meta = SCENE_META[i];
  sceneHostsHtml += `      <div id="${meta.id}" class="clip" data-composition-id="${meta.id}" data-composition-src="compositions/${meta.id}.html" data-start="${meta.start}" data-duration="${meta.duration}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index: 2;"></div>\n`;
  audioClipsHtml += `      <audio id="vo-${meta.id}" class="clip" src="assets/escena_${meta.code}.mp3" data-start="${meta.start}" data-duration="${meta.duration}" data-track-index="3" data-volume="1"></audio>\n`;

  if (i > 0) {
    const wStart = Number(Math.max(0.05, meta.start - 0.12).toFixed(3));
    sfxClipsHtml += `      <audio id="sfx-${++sfxIdx}" class="clip" src="assets/sfx/whoosh.mp3" data-start="${wStart}" data-duration="0.44" data-track-index="5" data-volume="0.22"></audio>\n`;
  }
  const popStart = Number((meta.start + 0.55).toFixed(3));
  sfxClipsHtml += `      <audio id="sfx-${++sfxIdx}" class="clip" src="assets/sfx/pop.mp3" data-start="${popStart}" data-duration="0.17" data-track-index="5" data-volume="0.24"></audio>\n`;

  if ([3, 7, 9, 10, 11, 16].includes(meta.num)) {
    const chimeStart = Number((meta.start + Math.min(4.5, meta.duration * 0.45)).toFixed(3));
    sfxClipsHtml += `      <audio id="sfx-${++sfxIdx}" class="clip" src="assets/sfx/chime.mp3" data-start="${chimeStart}" data-duration="0.62" data-track-index="5" data-volume="0.24"></audio>\n`;
  }
}

audioClipsHtml += sfxClipsHtml;

const indexHtml = `<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html,
      body {
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: #FFFFFF;
        font-family: "Inter", sans-serif;
      }
      #root {
        position: relative;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: #FFFFFF;
      }
      .bg-stage {
        position: absolute;
        inset: 0;
        background: #FFFFFF;
        z-index: 0;
      }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="${TOTAL_DURATION}"
      data-fps="30"
      data-width="1920"
      data-height="1080"
    >
      <div class="bg-stage"></div>
${sceneHostsHtml}      <div id="captions" class="clip" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="${TOTAL_DURATION}" data-track-index="2" data-track-kind="captions" data-width="1920" data-height="1080" style="z-index: 10;"></div>
${audioClipsHtml}    </div>

    <script>
      window.__timelines["main"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
`;

fs.writeFileSync(path.join(__dirname, "index.html"), indexHtml, "utf8");
console.log(`[OK] Proyecto de 16 escenas reconstruido en tema blanco (${TOTAL_DURATION}s, ${allGroups.length} grupos de subtítulos).`);
