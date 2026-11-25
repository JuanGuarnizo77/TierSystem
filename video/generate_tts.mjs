#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");
const envPath = path.join(projectRoot, ".env");
const assetsDir = path.join(__dirname, "assets");

const SCENES = {
  1: "En el Huila, la mayoría de los agricultores siembran arroz y café. No solo por gusto, sino por tradición: saben que sus tierras funcionan bien para esos cultivos. Pero cuando quieren probar algo distinto, aparece la duda: ¿mi suelo servirá? Experimentar cuesta dinero y tiempo, y no todos pueden asumir ese riesgo sin un respaldo técnico.",
  2: "Hoy, conocer las propiedades del suelo depende de laboratorios que suelen quedar lejos de las zonas rurales. El costo y la logística hacen que muchos desistan y siembren por intuición. Tampoco existe un registro que muestre cómo ha cambiado cada terreno, ni información clara de precios al momento de vender la cosecha.",
  3: "Para responder a esto nace TierSystem: una aplicación web que apoya el análisis técnico de suelos agrícolas. Combina un sensor portátil con inteligencia artificial y organiza el proceso entre tres roles: agricultor, laboratorista y administrador.",
  4: "El agricultor es el usuario final: se registra por su cuenta, administra sus terrenos y solicita los análisis. El laboratorista opera el sensor en campo y comparte los resultados. Y el administrador gestiona las cuentas de los laboratoristas, configura el sistema y supervisa la operación.",
  5: "Todo empieza cuando el agricultor registra su terreno con nombre y área. Luego crea una solicitud de análisis indicando el cultivo que desea sembrar y si prefiere llevar la muestra o pedir una visita técnica. Solo puede tener una solicitud activa a la vez y puede cancelarla mientras esté pendiente.",
  6: "El laboratorista revisa las solicitudes pendientes, las acepta o rechaza y les asigna una fecha de atención. El agricultor recibe una notificación con cada cambio de estado.",
  7: "En campo, el laboratorista conecta el sensor por WiFi o Bluetooth y verifica su estado. Está formado por un microcontrolador ESP32 y una sonda RS485 que mide siete parámetros: pH, nitrógeno, fósforo, potasio, humedad, conductividad eléctrica y temperatura. El sensor solo entrega lecturas; no las interpreta.",
  8: "Para que el análisis represente todo el terreno, el sistema sugiere cuántos puntos de muestreo tomar según su área. El laboratorista captura cada punto, el sistema valida que las lecturas estén en rango y calcula el perfil promedio del suelo. Si una lectura sale fuera de rango, pide repetir la captura.",
  9: "Con ese perfil, el sistema consulta al servicio de inteligencia artificial, que lo compara con los parámetros ideales del cultivo y calcula un porcentaje de compatibilidad: alta, media o baja. Cada parámetro se marca en verde si es óptimo, amarillo si es deficiente y rojo si es excesivo. También genera recomendaciones de mejora y, si la compatibilidad es baja, sugiere cultivos alternativos.",
  10: "El laboratorista revisa el resultado completo en una sola pantalla y lo comparte con el agricultor, quien recibe una notificación. Así decide con datos técnicos y no solo con la experiencia.",
  11: "Como muchas zonas rurales tienen poca señal, el laboratorista puede capturar datos y generar el análisis sin internet. Si la inteligencia artificial no responde, un motor local calcula la compatibilidad con los rangos agronómicos registrados y marca el resultado como análisis en modo local. Al volver la conexión, todo se sincroniza.",
  12: "Cada análisis queda guardado. El agricultor puede consultarlo, comparar dos análisis para ver cómo evoluciona su suelo, con mejoras en verde y deterioros en rojo, y exportar su historial.",
  13: "TierSystem incluye inteligencia de mercado. El agricultor consulta el precio de su cultivo, la evolución de las últimas tres semanas con su tendencia, y los compradores activos de su región, con datos de referencia del SIPSA del DANE.",
  14: "El administrador configura los rangos agronómicos, gestiona el catálogo de cultivos, define cuánto esperar a la inteligencia artificial y qué hacer si no responde, monitorea el sensor y su batería, y genera reportes en PDF o Excel.",
  15: "Los datos se protegen con acceso por roles, comunicación cifrada y cumplimiento de la Ley 1581 de 2012. La interfaz se adapta desde teléfonos hasta tabletas y puede instalarse como aplicación.",
  16: "En resumen, TierSystem le da al agricultor lo que antes dependía de un laboratorio lejano: conocer su suelo, recibir recomendaciones, hacer seguimiento a su terreno y negociar con información real. No reemplaza su criterio: le da datos para decidir mejor. Proyecto del tecnólogo en Análisis y Desarrollo de Software, SENA, Centro de Formación Agroindustrial La Angostura, Huila. Gracias por su atención.",
};

function pad2(n) {
  return String(n).padStart(2, "0");
}

function loadEnv(filePath) {
  const env = {};
  if (!fs.existsSync(filePath)) return env;
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    const val = trimmed.slice(idx + 1).trim();
    env[key] = val;
  }
  return env;
}

function alignmentToWords(alignment) {
  const chars = alignment?.characters || [];
  const starts = alignment?.character_start_times_seconds || [];
  const ends = alignment?.character_end_times_seconds || [];
  const words = [];
  let currentText = "";
  let wordStart = null;
  let wordEnd = null;

  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    const s = starts[i];
    const e = ends[i];
    if (/\s/.test(ch)) {
      if (currentText.length > 0) {
        words.push({
          id: `w${words.length}`,
          text: currentText,
          start: Number(wordStart.toFixed(3)),
          end: Number(wordEnd.toFixed(3)),
        });
        currentText = "";
        wordStart = null;
        wordEnd = null;
      }
    } else {
      if (wordStart === null) wordStart = s;
      wordEnd = e;
      currentText += ch;
    }
  }
  if (currentText.length > 0) {
    words.push({
      id: `w${words.length}`,
      text: currentText,
      start: Number(wordStart.toFixed(3)),
      end: Number(wordEnd.toFixed(3)),
    });
  }
  return words;
}

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

async function getSubscription(apiKey) {
  const resp = await fetch("https://api.elevenlabs.io/v1/user", {
    headers: { "xi-api-key": apiKey },
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Error consultando cuenta (${resp.status}): ${errText}`);
  }
  const data = await resp.json();
  return data.subscription;
}

async function generateScene(num, env, force = false) {
  const text = SCENES[num];
  if (!text) throw new Error(`Escena inválida: ${num}`);

  const code = pad2(num);
  fs.mkdirSync(assetsDir, { recursive: true });
  const mp3Path = path.join(assetsDir, `escena_${code}.mp3`);
  const wordsPath = path.join(assetsDir, `escena_${code}.words.json`);

  if (!force && fs.existsSync(mp3Path) && fs.existsSync(wordsPath)) {
    const duration = getAudioDuration(mp3Path);
    console.log(`[SKIP] escena_${code} ya existe (${duration}s)`);
    return { skipped: true, chars: 0, duration };
  }

  const voiceId = env.ELEVENLABS_VOICE_ID;
  const modelId = env.ELEVENLABS_MODEL_ID || "eleven_multilingual_v2";
  const stability = parseFloat(env.ELEVENLABS_STABILITY ?? "0.45");
  const similarity_boost = parseFloat(env.ELEVENLABS_SIMILARITY_BOOST ?? "0.80");
  const style = parseFloat(env.ELEVENLABS_STYLE ?? "0.15");
  const speed = parseFloat(env.ELEVENLABS_SPEED ?? "1.08");

  const url = `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/with-timestamps`;
  const body = {
    text,
    model_id: modelId,
    voice_settings: {
      stability,
      similarity_boost,
      style,
      speed,
    },
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "xi-api-key": env.ELEVENLABS_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Error en ElevenLabs escena_${code} (HTTP ${resp.status}): ${errText}`);
  }

  const payload = await resp.json();
  if (!payload.audio_base64) {
    throw new Error(`Respuesta sin audio_base64 en escena_${code}`);
  }

  const audioBuffer = Buffer.from(payload.audio_base64, "base64");
  fs.writeFileSync(mp3Path, audioBuffer);

  const alignment = payload.alignment || payload.normalized_alignment;
  const words = alignmentToWords(alignment);
  fs.writeFileSync(wordsPath, JSON.stringify(words, null, 2), "utf8");

  const duration = getAudioDuration(mp3Path);
  console.log(`[OK] escena_${code}.mp3 (${duration}s, ${audioBuffer.length} bytes) y escena_${code}.words.json (${words.length} palabras, ${text.length} caracteres)`);
  return { skipped: false, chars: text.length, duration, wordsCount: words.length };
}

async function main() {
  const env = loadEnv(envPath);
  if (!env.ELEVENLABS_API_KEY) {
    console.error("Falta ELEVENLABS_API_KEY en .env");
    process.exit(1);
  }
  if (!env.ELEVENLABS_VOICE_ID || env.ELEVENLABS_VOICE_ID === "<ID_DE_LA_VOZ>") {
    console.error("Falta ELEVENLABS_VOICE_ID válido en .env");
    process.exit(1);
  }

  const args = process.argv.slice(2);

  // Calcular caracteres totales del guion de 16 escenas
  let totalScriptChars = 0;
  const perSceneChars = {};
  for (let i = 1; i <= 16; i++) {
    perSceneChars[pad2(i)] = SCENES[i].length;
    totalScriptChars += SCENES[i].length;
  }

  const subBefore = await getSubscription(env.ELEVENLABS_API_KEY);
  const remainingBefore = subBefore.character_limit - subBefore.character_count;

  if (args.includes("--check-only")) {
    console.log(
      JSON.stringify(
        {
          total_script_chars: totalScriptChars,
          per_scene_chars: perSceneChars,
          account_used: subBefore.character_count,
          account_limit: subBefore.character_limit,
          account_remaining: remainingBefore,
          enough_quota: remainingBefore >= totalScriptChars,
          shortfall: Math.max(0, totalScriptChars - remainingBefore),
        },
        null,
        2
      )
    );
    return;
  }

  if (remainingBefore < totalScriptChars && !args.includes("--allow-partial")) {
    console.error(
      `Saldo insuficiente para el guion completo: requiere ${totalScriptChars} caracteres y quedan ${remainingBefore} (faltan ${totalScriptChars - remainingBefore}).`
    );
    process.exit(2);
  }

  let targets = [];
  let forceSingle = false;

  const idxEscena = args.indexOf("--escena");
  if (idxEscena !== -1 && args[idxEscena + 1]) {
    const n = parseInt(args[idxEscena + 1], 10);
    targets = [n];
    forceSingle = args.includes("--force");
  } else if (args.includes("--rest") || args.includes("--all")) {
    targets = Array.from({ length: 16 }, (_, i) => i + 1);
  } else {
    targets = [1];
  }

  let charsUsedInBatch = 0;
  for (const n of targets) {
    const res = await generateScene(n, env, forceSingle);
    charsUsedInBatch += res.chars;
  }

  const subAfter = await getSubscription(env.ELEVENLABS_API_KEY);
  const remainingAfter = subAfter.character_limit - subAfter.character_count;
  console.log(
    JSON.stringify({
      total_script_chars: totalScriptChars,
      batch_chars_text: charsUsedInBatch,
      account_used_before: subBefore.character_count,
      account_used_after: subAfter.character_count,
      account_limit: subAfter.character_limit,
      account_remaining: remainingAfter,
    })
  );
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
