#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const assetsDir = path.join(__dirname, "assets");
const origDir = path.join(assetsDir, "original_1x");

fs.mkdirSync(origDir, { recursive: true });

const SPEED = 1.12; // 12% más rápido: ágil, dinámico y natural sin sonar acelerado

function getAudioDuration(filePath) {
  const res = spawnSync(
    "ffprobe",
    ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filePath],
    { encoding: "utf8" }
  );
  if (res.status === 0 && res.stdout.trim()) {
    return Number(parseFloat(res.stdout.trim()).toFixed(3));
  }
  return null;
}

// 1. Respaldar originales 1x si aún no están respaldados
for (let i = 1; i <= 16; i++) {
  const code = String(i).padStart(2, "0");
  const srcMp3 = path.join(assetsDir, `escena_${code}.mp3`);
  const srcWords = path.join(assetsDir, `escena_${code}.words.json`);
  const bakMp3 = path.join(origDir, `escena_${code}.mp3`);
  const bakWords = path.join(origDir, `escena_${code}.words.json`);

  if (!fs.existsSync(bakMp3) && fs.existsSync(srcMp3)) {
    fs.copyFileSync(srcMp3, bakMp3);
  }
  if (!fs.existsSync(bakWords) && fs.existsSync(srcWords)) {
    fs.copyFileSync(srcWords, bakWords);
  }
}

const newDurations = {};
let sumAudio = 0;

for (let i = 1; i <= 16; i++) {
  const code = String(i).padStart(2, "0");
  const bakMp3 = path.join(origDir, `escena_${code}.mp3`);
  const bakWords = path.join(origDir, `escena_${code}.words.json`);
  const outMp3 = path.join(assetsDir, `escena_${code}.mp3`);
  const outWords = path.join(assetsDir, `escena_${code}.words.json`);

  const rawWords = JSON.parse(fs.readFileSync(bakWords, "utf8"));
  let scaledWords = [];

  if (i < 16) {
    // Escenas 01 a 15: aplicar atempo=1.12
    const ff = spawnSync(
      "ffmpeg",
      ["-y", "-i", bakMp3, "-filter:a", `atempo=${SPEED}`, "-b:a", "128k", outMp3],
      { encoding: "utf8" }
    );
    if (ff.status !== 0) {
      throw new Error(`Error ffmpeg en escena_${code}: ${ff.stderr}`);
    }

    scaledWords = rawWords.map((w, idx) => ({
      id: `w${idx}`,
      text: w.text,
      start: Number((w.start / SPEED).toFixed(3)),
      end: Number((w.end / SPEED).toFixed(3)),
    }));
  } else {
    // Escena 16: Quitar "Proyecto del tecnólogo en Análisis y Desarrollo de Software, SENA, Centro de Formación Agroindustrial La Angostura, Huila."
    // Parte 1: 0.0s -> 18.85s (hasta "le da datos para decidir mejor.")
    // Parte 2: 28.10s -> final ("Gracias por su atención.")
    const CUT_END_1 = 18.85;
    const CUT_START_2 = 28.10;
    const GAP_REMOVED = CUT_START_2 - CUT_END_1; // 9.25s eliminados

    const filterComplex = `[0:a]atrim=0:${CUT_END_1},asetpts=PTS-STARTPTS[a1];[0:a]atrim=${CUT_START_2},asetpts=PTS-STARTPTS[a2];[a1][a2]concat=n=2:v=0:a=1,atempo=${SPEED}[outa]`;
    const ff = spawnSync(
      "ffmpeg",
      ["-y", "-i", bakMp3, "-filter_complex", filterComplex, "-map", "[outa]", "-b:a", "128k", outMp3],
      { encoding: "utf8" }
    );
    if (ff.status !== 0) {
      throw new Error(`Error ffmpeg en escena_16: ${ff.stderr}`);
    }

    // Filtrar palabras w0..w39 (<18.85s) y w57..w60 (>=28.10s)
    const filtered = [];
    for (const w of rawWords) {
      if (w.end <= CUT_END_1) {
        filtered.push({
          text: w.text,
          start: w.start / SPEED,
          end: w.end / SPEED,
        });
      } else if (w.start >= CUT_START_2) {
        filtered.push({
          text: w.text,
          start: (w.start - GAP_REMOVED) / SPEED,
          end: (w.end - GAP_REMOVED) / SPEED,
        });
      }
    }

    scaledWords = filtered.map((w, idx) => ({
      id: `w${idx}`,
      text: w.text,
      start: Number(w.start.toFixed(3)),
      end: Number(w.end.toFixed(3)),
    }));
  }

  fs.writeFileSync(outWords, JSON.stringify(scaledWords, null, 2), "utf8");
  const dur = getAudioDuration(outMp3);
  newDurations[i] = dur;
  sumAudio += dur;
  console.log(`[OK] escena_${code}.mp3 -> ${dur}s (${scaledWords.length} palabras)`);
}

const totalWithPauses = Number((sumAudio + 15 * 0.4).toFixed(3));
console.log(
  JSON.stringify(
    {
      speed_factor: SPEED,
      sum_audio_seconds: Number(sumAudio.toFixed(3)),
      total_with_pauses_seconds: totalWithPauses,
      total_minutes: `${Math.floor(totalWithPauses / 60)}:${String(Math.round(totalWithPauses % 60)).padStart(2, "0")}`,
      durations: newDurations,
    },
    null,
    2
  )
);
