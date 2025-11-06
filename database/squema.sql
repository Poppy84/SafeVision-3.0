-- Base de datos para Sistema de Videovigilancia Inteligente

-- Tabla de personas conocidas (rostros registrados)
CREATE TABLE personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    tipo VARCHAR(20) DEFAULT 'residente', -- residente, empleado, visitante_autorizado
    encoding BLOB NOT NULL, -- Encoding facial serializado
    foto_referencia VARCHAR(255), -- Ruta a la imagen de referencia
    activo BOOLEAN DEFAULT 1,
    notas TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de cámaras
CREATE TABLE camaras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    ubicacion VARCHAR(200),
    tipo VARCHAR(20), -- ip, webcam, rtsp
    url_stream VARCHAR(255), -- Para cámaras IP
    activa BOOLEAN DEFAULT 1,
    configuracion TEXT, -- JSON con configuración adicional
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de detecciones (log de todas las detecciones faciales)
CREATE TABLE detecciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camara_id INTEGER NOT NULL,
    persona_id INTEGER, -- NULL si es desconocido
    confianza FLOAT, -- Nivel de confianza del reconocimiento (0-1)
    es_desconocido BOOLEAN DEFAULT 0,
    imagen_captura VARCHAR(255), -- Ruta a la captura del rostro
    imagen_frame VARCHAR(255), -- Ruta al frame completo
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camara_id) REFERENCES camaras(id),
    FOREIGN KEY (persona_id) REFERENCES personas(id)
);

-- Tabla de eventos (situaciones importantes que generan alertas)
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo VARCHAR(50) NOT NULL, -- intruso_detectado, persona_no_autorizada, horario_inusual, etc
    severidad VARCHAR(20) DEFAULT 'media', -- baja, media, alta, critica
    descripcion TEXT,
    deteccion_id INTEGER,
    camara_id INTEGER NOT NULL,
    resuelto BOOLEAN DEFAULT 0,
    notas_resolucion TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    FOREIGN KEY (deteccion_id) REFERENCES detecciones(id),
    FOREIGN KEY (camara_id) REFERENCES camaras(id)
);

-- Tabla de patrones detectados
CREATE TABLE patrones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo VARCHAR(50), -- frecuencia_visitas, horario_inusual, permanencia_prolongada
    persona_id INTEGER,
    camara_id INTEGER,
    descripcion TEXT,
    metadata TEXT, -- JSON con datos adicionales del patrón
    fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (persona_id) REFERENCES personas(id),
    FOREIGN KEY (camara_id) REFERENCES camaras(id)
);

-- Tabla de configuración del sistema
CREATE TABLE configuracion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT,
    descripcion TEXT,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de alertas enviadas
CREATE TABLE alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    tipo_alerta VARCHAR(50), -- email, push, sms, webhook
    destinatario VARCHAR(255),
    enviada BOOLEAN DEFAULT 0,
    fecha_envio TIMESTAMP,
    error TEXT,
    FOREIGN KEY (evento_id) REFERENCES eventos(id)
);

-- Índices para optimizar consultas frecuentes
CREATE INDEX idx_detecciones_timestamp ON detecciones(timestamp);
CREATE INDEX idx_detecciones_persona ON detecciones(persona_id);
CREATE INDEX idx_detecciones_camara ON detecciones(camara_id);
CREATE INDEX idx_eventos_timestamp ON eventos(timestamp);
CREATE INDEX idx_eventos_resuelto ON eventos(resuelto);
CREATE INDEX idx_personas_activo ON personas(activo);

-- Insertar configuraciones iniciales
INSERT INTO configuracion (clave, valor, descripcion) VALUES
('umbral_confianza', '0.6', 'Umbral mínimo de confianza para reconocimiento facial'),
('tiempo_entre_detecciones', '30', 'Segundos mínimos entre detecciones de la misma persona'),
('activar_alertas', '1', 'Activar sistema de alertas'),
('guardar_frames', '1', 'Guardar frames completos de detecciones'),
('dias_retencion_imagenes', '30', 'Días para mantener imágenes almacenadas');