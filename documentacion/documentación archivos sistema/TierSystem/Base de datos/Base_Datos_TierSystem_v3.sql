-- ============================================================
-- TierSystem - Base de Datos Oficial (v3)
-- SENA - Centro Agroindustrial La Angostura
-- Basado en Base_Datos_Tiersystemv2.sql, revisado y extendido
-- para cubrir los 49 RF / 10 módulos del SRS.
-- ============================================================

CREATE TABLE `rol` (
  `id_rol` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre_rol` VARCHAR(30) UNIQUE NOT NULL
);

CREATE TABLE `usuario` (
  `id_usuario` INT PRIMARY KEY AUTO_INCREMENT,
  `id_rol` INT NOT NULL,
  `nombre` VARCHAR(100) NOT NULL,
  `correo` VARCHAR(150) UNIQUE NOT NULL,
  `contrasena` VARCHAR(255) NOT NULL,
  `estado` ENUM ('activo', 'inactivo') NOT NULL DEFAULT 'activo',
  `nivel_acceso` VARCHAR(30) COMMENT 'Solo aplica cuando id_rol = Administrador',
  `fecha_registro` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `fecha_actualizacion` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP) ON UPDATE CURRENT_TIMESTAMP
);

-- NUEVO: soporta RF004 - Recuperación de contraseña mediante enlace al correo
CREATE TABLE `token_recuperacion` (
  `id_token` INT PRIMARY KEY AUTO_INCREMENT,
  `id_usuario` INT NOT NULL,
  `token` VARCHAR(255) UNIQUE NOT NULL,
  `fecha_expiracion` DATETIME NOT NULL,
  `usado` BOOLEAN NOT NULL DEFAULT false,
  `fecha_creacion` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

-- NUEVO: soporta RF040 - Actividad de Laboratoristas y trazabilidad general (RNF004)
CREATE TABLE `bitacora_actividad` (
  `id_bitacora` INT PRIMARY KEY AUTO_INCREMENT,
  `id_usuario` INT NOT NULL,
  `accion` VARCHAR(100) NOT NULL COMMENT 'Ej: login, aceptar_solicitud, compartir_resultado',
  `detalle` VARCHAR(255),
  `fecha` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE `terreno` (
  `id_terreno` INT PRIMARY KEY AUTO_INCREMENT,
  `id_usuario` INT NOT NULL COMMENT 'Agricultor dueño del terreno',
  `nombre_terreno` VARCHAR(100) NOT NULL,
  `area` DECIMAL(10,2) NOT NULL,
  `ubicacion` VARCHAR(255),
  `activo` BOOLEAN NOT NULL DEFAULT true COMMENT 'Soft delete: preserva el historial de análisis (RF008/RF011)',
  `fecha_registro` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `fecha_actualizacion` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP) ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `chk_terreno_area` CHECK (area > 0)
);

CREATE TABLE `cultivo` (
  `id_cultivo` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre_cultivo` VARCHAR(100) UNIQUE NOT NULL,
  `descripcion` VARCHAR(255),
  `activo` BOOLEAN NOT NULL DEFAULT true COMMENT 'Soft delete: preserva integridad de análisis históricos (RF037)',
  `ph_ideal_min` DECIMAL(4,2),
  `ph_ideal_max` DECIMAL(4,2),
  `n_ideal_min` DECIMAL(6,2),
  `n_ideal_max` DECIMAL(6,2),
  `p_ideal_min` DECIMAL(6,2),
  `p_ideal_max` DECIMAL(6,2),
  `k_ideal_min` DECIMAL(6,2),
  `k_ideal_max` DECIMAL(6,2),
  `humedad_ideal_min` DECIMAL(5,2),
  `humedad_ideal_max` DECIMAL(5,2),
  `ce_ideal_min` DECIMAL(6,2),
  `ce_ideal_max` DECIMAL(6,2),
  `temperatura_ideal_min` DECIMAL(5,2),
  `temperatura_ideal_max` DECIMAL(5,2),
  CONSTRAINT `chk_cultivo_ph` CHECK (ph_ideal_max IS NULL OR ph_ideal_max > ph_ideal_min),
  CONSTRAINT `chk_cultivo_n` CHECK (n_ideal_max IS NULL OR n_ideal_max > n_ideal_min),
  CONSTRAINT `chk_cultivo_p` CHECK (p_ideal_max IS NULL OR p_ideal_max > p_ideal_min),
  CONSTRAINT `chk_cultivo_k` CHECK (k_ideal_max IS NULL OR k_ideal_max > k_ideal_min),
  CONSTRAINT `chk_cultivo_humedad` CHECK (humedad_ideal_max IS NULL OR humedad_ideal_max > humedad_ideal_min),
  CONSTRAINT `chk_cultivo_ce` CHECK (ce_ideal_max IS NULL OR ce_ideal_max > ce_ideal_min),
  CONSTRAINT `chk_cultivo_temp` CHECK (temperatura_ideal_max IS NULL OR temperatura_ideal_max > temperatura_ideal_min)
);

-- Rangos físicos válidos que puede medir el sensor (distintos de los rangos ideales por cultivo).
-- Se usan para marcar `punto_muestreo.fuera_de_rango`.
CREATE TABLE `rango_sensor` (
  `id_parametro` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre_parametro` VARCHAR(30) UNIQUE NOT NULL COMMENT 'pH, N, P, K, Humedad, CE, Temperatura',
  `valor_min_valido` DECIMAL(8,2) NOT NULL,
  `valor_max_valido` DECIMAL(8,2) NOT NULL,
  CONSTRAINT `chk_rango_sensor` CHECK (valor_max_valido > valor_min_valido)
);

CREATE TABLE `sensor` (
  `id_sensor` INT PRIMARY KEY AUTO_INCREMENT,
  `identificador` VARCHAR(50) UNIQUE NOT NULL,
  `id_usuario_laboratorista` INT,
  `estado_conexion` ENUM ('activo', 'inactivo') NOT NULL DEFAULT 'inactivo',
  `nivel_bateria` INT,
  `ultima_lectura` DATETIME,
  CONSTRAINT `chk_sensor_bateria` CHECK (nivel_bateria IS NULL OR (nivel_bateria BETWEEN 0 AND 100))
);

CREATE TABLE `solicitud_analisis` (
  `id_solicitud` INT PRIMARY KEY AUTO_INCREMENT,
  `id_terreno` INT NOT NULL,
  `id_usuario_laboratorista` INT COMMENT 'Se asigna cuando se acepta la solicitud',
  `id_cultivo` INT NOT NULL COMMENT 'Cultivo deseado indicado por el Agricultor',
  `modalidad_entrega` ENUM ('llevar_muestra', 'visita_terreno') NOT NULL,
  `estado` ENUM ('pendiente', 'aceptada', 'en_proceso', 'finalizada', 'rechazada', 'cancelada') NOT NULL DEFAULT 'pendiente',
  `observaciones_estado` VARCHAR(255) COMMENT 'Motivo de rechazo o de cancelación',
  `fecha_creacion` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `fecha_actualizacion` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP) ON UPDATE CURRENT_TIMESTAMP,
  `fecha_asignada` DATE
);

CREATE TABLE `punto_muestreo` (
  `id_punto` INT PRIMARY KEY AUTO_INCREMENT,
  `id_solicitud` INT NOT NULL,
  `id_sensor` INT COMMENT 'Sensor físico que capturó el punto (trazabilidad de hardware, RF036)',
  `numero_punto` INT NOT NULL,
  `ph` DECIMAL(4,2),
  `n` DECIMAL(6,2),
  `p` DECIMAL(6,2),
  `k` DECIMAL(6,2),
  `humedad` DECIMAL(5,2),
  `ce` DECIMAL(6,2),
  `temperatura` DECIMAL(5,2),
  `fuera_de_rango` BOOLEAN NOT NULL DEFAULT false,
  `fecha_captura` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE `analisis` (
  `id_analisis` INT PRIMARY KEY AUTO_INCREMENT,
  `id_solicitud` INT UNIQUE NOT NULL COMMENT 'Relacion 1:1 con la solicitud',
  `perfil_ph` DECIMAL(4,2),
  `perfil_n` DECIMAL(6,2),
  `perfil_p` DECIMAL(6,2),
  `perfil_k` DECIMAL(6,2),
  `perfil_humedad` DECIMAL(5,2),
  `perfil_ce` DECIMAL(6,2),
  `perfil_temperatura` DECIMAL(5,2),
  `porcentaje_compatibilidad` DECIMAL(5,2),
  `modo` ENUM ('online', 'offline_local') NOT NULL,
  `estado_ia` ENUM ('pendiente', 'completado', 'error') NOT NULL DEFAULT 'pendiente',
  `sincronizado_ia` BOOLEAN NOT NULL DEFAULT true COMMENT 'false mientras un análisis offline_local espera reenvío a la IA externa',
  `fecha_sincronizacion_ia` DATETIME COMMENT 'Fecha en que el análisis local fue confirmado por la IA externa',
  `compartido_con_agricultor` BOOLEAN NOT NULL DEFAULT false,
  `fecha_comparticion` DATETIME,
  `fecha_analisis` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  CONSTRAINT `chk_analisis_compatibilidad` CHECK (porcentaje_compatibilidad IS NULL OR (porcentaje_compatibilidad BETWEEN 0 AND 100))
);

CREATE TABLE `recomendacion_mejora` (
  `id_recomendacion` INT PRIMARY KEY AUTO_INCREMENT,
  `id_analisis` INT NOT NULL,
  `parametro` VARCHAR(30) NOT NULL,
  `tipo` ENUM ('deficiente', 'excesivo') NOT NULL,
  `descripcion` VARCHAR(255) NOT NULL,
  `mejora_estimada` DECIMAL(5,2)
);

CREATE TABLE `cultivo_alternativo` (
  `id_cultivoAlternativo` INT PRIMARY KEY AUTO_INCREMENT,
  `id_analisis` INT NOT NULL,
  `id_cultivo` INT NOT NULL,
  `porcentaje_compatibilidad` DECIMAL(5,2) NOT NULL,
  CONSTRAINT `uq_alternativo_analisis_cultivo` UNIQUE (`id_analisis`, `id_cultivo`),
  CONSTRAINT `chk_alternativo_compatibilidad` CHECK (porcentaje_compatibilidad BETWEEN 0 AND 100)
);

CREATE TABLE `precio_mercado` (
  `id_precio` INT PRIMARY KEY AUTO_INCREMENT,
  `id_cultivo` INT NOT NULL,
  `region` VARCHAR(100) NOT NULL,
  `fecha` DATE NOT NULL,
  `precio` DECIMAL(10,2) NOT NULL,
  `fuente` VARCHAR(50) COMMENT 'SIPSA / DANE',
  CONSTRAINT `chk_precio_positivo` CHECK (precio > 0)
);

CREATE TABLE `comprador` (
  `id_comprador` INT PRIMARY KEY AUTO_INCREMENT,
  `nombre` VARCHAR(150) NOT NULL,
  `tipo` VARCHAR(50),
  `municipio` VARCHAR(100),
  `contacto` VARCHAR(150),
  `activo` BOOLEAN NOT NULL DEFAULT true COMMENT 'Permite filtrar "compradores activos" (RF016)'
);

CREATE TABLE `comprador_cultivo` (
  `id_compradorCultivo` INT PRIMARY KEY AUTO_INCREMENT,
  `id_comprador` INT NOT NULL,
  `id_cultivo` INT NOT NULL,
  CONSTRAINT `uq_cc_comprador_cultivo` UNIQUE (`id_comprador`, `id_cultivo`)
);

CREATE TABLE `configuracion_sistema` (
  `id_configuracion` INT PRIMARY KEY AUTO_INCREMENT,
  `tiempo_espera_ia` INT NOT NULL DEFAULT 30 COMMENT 'Segundos de espera antes de usar el motor local',
  `accion_fallo_ia` ENUM ('usar_local', 'notificar_cancelar') NOT NULL DEFAULT 'usar_local'
);

-- ============================================================
-- INDICES
-- ============================================================

CREATE INDEX `idx_usuario_rol` ON `usuario` (`id_rol`);

CREATE INDEX `idx_token_usuario` ON `token_recuperacion` (`id_usuario`);

CREATE INDEX `idx_bitacora_usuario` ON `bitacora_actividad` (`id_usuario`);
CREATE INDEX `idx_bitacora_fecha` ON `bitacora_actividad` (`fecha`);

CREATE UNIQUE INDEX `uq_terreno_nombre_por_usuario` ON `terreno` (`id_usuario`, `nombre_terreno`);
CREATE INDEX `idx_terreno_usuario` ON `terreno` (`id_usuario`);

CREATE INDEX `idx_solicitud_terreno` ON `solicitud_analisis` (`id_terreno`);
CREATE INDEX `idx_solicitud_laboratorista` ON `solicitud_analisis` (`id_usuario_laboratorista`);
CREATE INDEX `idx_solicitud_estado` ON `solicitud_analisis` (`estado`);
CREATE INDEX `idx_solicitud_fecha` ON `solicitud_analisis` (`fecha_creacion`) COMMENT 'Soporta reportes filtrados por rango de fechas (RF035)';

CREATE UNIQUE INDEX `uq_punto_por_solicitud` ON `punto_muestreo` (`id_solicitud`, `numero_punto`);
CREATE INDEX `idx_punto_sensor` ON `punto_muestreo` (`id_sensor`);

CREATE INDEX `idx_analisis_fecha` ON `analisis` (`fecha_analisis`);

CREATE UNIQUE INDEX `uq_precio_dia` ON `precio_mercado` (`id_cultivo`, `region`, `fecha`);
CREATE INDEX `idx_precio_cultivo_fecha` ON `precio_mercado` (`id_cultivo`, `fecha`);

-- ============================================================
-- LLAVES FORANEAS
-- ============================================================

ALTER TABLE `usuario` ADD CONSTRAINT `fk_usuario_rol` FOREIGN KEY (`id_rol`) REFERENCES `rol` (`id_rol`);

ALTER TABLE `token_recuperacion` ADD CONSTRAINT `fk_token_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE;

ALTER TABLE `bitacora_actividad` ADD CONSTRAINT `fk_bitacora_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE;

ALTER TABLE `terreno` ADD CONSTRAINT `fk_terreno_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`);

ALTER TABLE `sensor` ADD CONSTRAINT `fk_sensor_laboratorista` FOREIGN KEY (`id_usuario_laboratorista`) REFERENCES `usuario` (`id_usuario`);

ALTER TABLE `solicitud_analisis` ADD CONSTRAINT `fk_solicitud_terreno` FOREIGN KEY (`id_terreno`) REFERENCES `terreno` (`id_terreno`);

ALTER TABLE `solicitud_analisis` ADD CONSTRAINT `fk_solicitud_laboratorista` FOREIGN KEY (`id_usuario_laboratorista`) REFERENCES `usuario` (`id_usuario`);

ALTER TABLE `solicitud_analisis` ADD CONSTRAINT `fk_solicitud_cultivo` FOREIGN KEY (`id_cultivo`) REFERENCES `cultivo` (`id_cultivo`);

ALTER TABLE `punto_muestreo` ADD CONSTRAINT `fk_punto_solicitud` FOREIGN KEY (`id_solicitud`) REFERENCES `solicitud_analisis` (`id_solicitud`) ON DELETE CASCADE;

ALTER TABLE `punto_muestreo` ADD CONSTRAINT `fk_punto_sensor` FOREIGN KEY (`id_sensor`) REFERENCES `sensor` (`id_sensor`);

ALTER TABLE `analisis` ADD CONSTRAINT `fk_analisis_solicitud` FOREIGN KEY (`id_solicitud`) REFERENCES `solicitud_analisis` (`id_solicitud`) ON DELETE CASCADE;

ALTER TABLE `recomendacion_mejora` ADD CONSTRAINT `fk_recomendacion_analisis` FOREIGN KEY (`id_analisis`) REFERENCES `analisis` (`id_analisis`) ON DELETE CASCADE;

ALTER TABLE `cultivo_alternativo` ADD CONSTRAINT `fk_alternativo_analisis` FOREIGN KEY (`id_analisis`) REFERENCES `analisis` (`id_analisis`) ON DELETE CASCADE;

ALTER TABLE `cultivo_alternativo` ADD CONSTRAINT `fk_alternativo_cultivo` FOREIGN KEY (`id_cultivo`) REFERENCES `cultivo` (`id_cultivo`);

ALTER TABLE `precio_mercado` ADD CONSTRAINT `fk_precio_cultivo` FOREIGN KEY (`id_cultivo`) REFERENCES `cultivo` (`id_cultivo`);

ALTER TABLE `comprador_cultivo` ADD CONSTRAINT `fk_cc_comprador` FOREIGN KEY (`id_comprador`) REFERENCES `comprador` (`id_comprador`) ON DELETE CASCADE;

ALTER TABLE `comprador_cultivo` ADD CONSTRAINT `fk_cc_cultivo` FOREIGN KEY (`id_cultivo`) REFERENCES `cultivo` (`id_cultivo`) ON DELETE CASCADE;

-- ============================================================
-- DATOS INICIALES
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO `configuracion_sistema` (`tiempo_espera_ia`, `accion_fallo_ia`)
VALUES
  (30, 'usar_local');

INSERT INTO `rol` (`nombre_rol`)
VALUES
  ('Agricultor'),
  ('Laboratorista'),
  ('Administrador');

INSERT INTO `rango_sensor` (`nombre_parametro`, `valor_min_valido`, `valor_max_valido`)
VALUES
  ('pH', 0, 14),
  ('N', 0, 999),
  ('P', 0, 999),
  ('K', 0, 999),
  ('Humedad', 0, 100),
  ('CE', 0, 20),
  ('Temperatura', -10, 60);

SET FOREIGN_KEY_CHECKS = 1;
