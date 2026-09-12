// Configuración de la base de datos local usando Dexie.js (Wrapper de IndexedDB)
// Requiere importar Dexie.js antes de este archivo: <script src="https://unpkg.com/dexie/dist/dexie.js"></script>

const db = new Dexie('TierSystemOfflineDB');

// Definir el esquema
db.version(1).stores({
  solicitudes: 'id, agricultor_id, terreno_id, cultivo_id, estado, fecha_creacion',
  cultivos: 'id, nombre, ph_min, ph_max, n_min, n_max, p_min, p_max, k_min, k_max, humedad_min, humedad_max, ce_min, ce_max, temp_min, temp_max',
  capturas: '++id, solicitud_id, punto_numero, ph, n, p, k, humedad, ce, temperatura, timestamp',
  analisis_locales: '++id, solicitud_id, compatibilidad, json_resultado, sincronizado'
});

// Función para guardar una captura proveniente del ESP32 de forma offline
async function guardarCapturaLocal(solicitud_id, punto_numero, datosSensor) {
  try {
    await db.capturas.add({
      solicitud_id: solicitud_id,
      punto_numero: punto_numero,
      ph: datosSensor.ph,
      n: datosSensor.n,
      p: datosSensor.p,
      k: datosSensor.k,
      humedad: datosSensor.humedad,
      ce: datosSensor.ce,
      temperatura: datosSensor.temperatura,
      timestamp: new Date().toISOString()
    });
    console.log(`Captura del punto ${punto_numero} guardada offline correctamente.`);
  } catch (error) {
    console.error("Error al guardar captura offline:", error);
  }
}
