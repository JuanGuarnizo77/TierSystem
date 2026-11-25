#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const assetsDir = path.join(__dirname, "assets");
const compsDir = path.join(__dirname, "compositions");

const SCENE_OFFSETS = {
  1: 0.0,
  2: 11.4,
  3: 18.55,
  4: 27.75,
  5: 35.3,
  6: 42.2,
};

function buildGroupsForScene(sceneNum, offset) {
  const wordsPath = path.join(assetsDir, `escena_${sceneNum}.words.json`);
  const words = JSON.parse(fs.readFileSync(wordsPath, "utf8"));
  const groups = [];
  let current = [];

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const absWord = {
      id: `s${sceneNum}_${w.id}`,
      text: w.text,
      start: Number((offset + w.start).toFixed(3)),
      end: Number((offset + w.end).toFixed(3)),
    };
    current.push(absWord);

    const next = words[i + 1];
    const endsSentence = /[.?!:;]$/.test(w.text);
    const hasPause = next ? next.start - w.end >= 0.22 : true;
    const hitLimit = current.length >= 5;

    if (endsSentence || hasPause || hitLimit || !next) {
      const gStart = current[0].start;
      const gEnd = current[current.length - 1].end + 0.14;
      groups.push({
        id: `cap_s${sceneNum}_g${groups.length}`,
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
for (const s of [1, 2, 3, 4, 5, 6]) {
  allGroups.push(...buildGroupsForScene(s, SCENE_OFFSETS[s]));
}

// Asegurar que ningún grupo se solape con el siguiente
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

const groupsJson = JSON.stringify(allGroups);

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
      left: 160px;
      right: 160px;
      bottom: 84px;
      height: 88px;
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
      border: 2.5px solid #0A4D3C;
      box-shadow: 0 10px 28px rgba(10, 77, 60, 0.14);
      padding: 12px 28px;
      border-radius: 16px;
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
    <div id="cap-clip" class="clip" data-start="0" data-duration="47.45" data-track-index="0">
      <div class="captions-band" data-layout-allow-caption-zone>
${htmlGroups}      </div>
    </div>
  </div>

  <script>
    const tl = gsap.timeline({ paused: true });
    const groups = ${groupsJson};

    groups.forEach((g) => {
      const gSel = "#" + g.id;
      const openAt = Math.max(0.05, g.start);
      tl.set(gSel, { visibility: "visible", opacity: 1 }, openAt);

      g.words.forEach((w) => {
        const wSel = "#" + w.id;
        const wStart = Math.max(openAt, w.start);
        const wDur = Math.max(0.08, w.end - w.start);
        tl.to(
          wSel,
          { color: "#1B5E20", backgroundColor: "#D1FAE5", duration: 0.06, ease: "none" },
          wStart
        );
        tl.to(
          wSel,
          { color: "#0F172A", backgroundColor: "rgba(209,250,229,0)", duration: 0.08, ease: "none" },
          wStart + wDur
        );
      });

      // En la última escena cerramos a los 4.2s antes del fundido a negro
      const maxEnd = Math.min(g.end, 45.8);
      const fadeStart = Math.max(openAt + 0.05, maxEnd - 0.12);
      tl.to(gSel, { opacity: 0, duration: 0.12, ease: "power2.in" }, fadeStart);
      tl.set(gSel, { opacity: 0, visibility: "hidden" }, maxEnd);
    });

    window.__timelines["captions"] = tl;
  </script>
</template>
`;

fs.writeFileSync(path.join(compsDir, "captions.html"), captionsHtml, "utf8");
console.log(`[OK] captions.html generado con ${allGroups.length} grupos de subtítulos.`);
