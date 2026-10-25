/**
 * Capa de Persistencia Local Offline (IndexedDB / Dexie.js).
 * ==========================================================
 * Proporciona el soporte de almacenamiento en cliente para la PWA de TierSystem:
 * Permite que el laboratorista opere en zonas rurales del departamento del Huila
 * sin cobertura de red móvil ni conexión a internet:
 *   - Almacena solicitudes activas precargadas.
 *   - Mantiene en caché el catálogo agronómico de cultivos para calibración local.
 *   - Registra de forma inmediata cada captura física de la sonda ESP32.
 *   - Encola resultados edafológicos locales pendientes de sincronización hacia el servidor Django.
 *
 * Dependencia:
 *   Requiere Dexie.js cargado previamente en el DOM:
 *   <script src="https://unpkg.com/dexie/dist/dexie.js"></script>
 */

// Instanciación de la base de datos local en el navegador
const db = new Dexie('TierSystemOfflineDB');

// Definición del esquema de tablas e índices primarios/secundarios
db.version(1).stores({
  // Tabla de órdenes de análisis asignadas al laboratorista
  solicitudes: 'id, agricultor_id, terreno_id, cultivo_id, estado, fecha_creacion',
  // Tabla de catálogo agronómico para evaluación de compatibilidad offline
  cultivos: 'id, nombre, ph_min, ph_max, n_min, n_max, p_min, p_max, k_min, k_max, humedad_min, humedad_max, ce_min, ce_max, temp_min, temp_max',
  // Tabla de submuestras individuales capturadas en los puntos de la cuadrícula
  capturas: '++id, solicitud_id, punto_numero, ph, n, p, k, humedad, ce, temperatura, timestamp',
  // Cola de sincronización de análisis calculados en modo desconectado
  analisis_locales: '++id, solicitud_id, compatibilidad, json_resultado, sincronizado'
});

/**
 * Guarda una captura de telemetría proveniente del sensor ESP32 en la base de datos local.
 *
 * @param {number|string} solicitud_id - Identificador único de la solicitud de análisis.
 * @param {number} punto_numero - Número secuencial del punto de muestreo en la cuadrícula de campo.
 * @param {Object} datosSensor - Mediciones físico-químicas leídas de la sonda.
 * @param {number} datosSensor.ph - Acidez o alcalinidad del suelo.
 * @param {number} datosSensor.n - Nitrógeno disponible en mg/kg.
 * @param {number} datosSensor.p - Fósforo disponible en mg/kg.
 * @param {number} datosSensor.k - Potasio disponible en mg/kg.
 * @param {number} datosSensor.humedad - Porcentaje de humedad edáfica.
 * @param {number} datosSensor.ce - Conductividad eléctrica en dS/m.
 * @param {number} datosSensor.temperatura - Temperatura en grados Celsius.
 * @returns {Promise<void>}
 */
async function guardarCapturaLocal(solicitud_id, punto_numero, datosSensor) {
  try {
    // Inserción asíncrona del registro con marca temporal ISO 8601
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
    console.error("Error al guardar captura offline en IndexedDB:", error);
  }
}
