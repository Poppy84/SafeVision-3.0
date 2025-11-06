# Estructura del proyecto:
"""
videovigilancia_ia/
│
├── main.py                          # Punto de entrada principal
├── config.py                        # Configuración global
├── requirements.txt                 # Dependencias
│
├── core/                            # Núcleo del sistema
│   ├── __init__.py
│   ├── video_capture.py            # Captura de video (webcam/IP)
│   ├── face_detector.py            # Detección de rostros
│   ├── face_recognizer.py          # Reconocimiento facial
│   └── pattern_analyzer.py         # Análisis de patrones
│
├── database/                        # Capa de base de datos
│   ├── __init__.py
│   ├── db_manager.py               # Gestor principal de BD
│   ├── models.py                   # Modelos/clases de datos
│   └── schema.sql                  # Esquema SQL
│
├── services/                        # Servicios y lógica de negocio
│   ├── __init__.py
│   ├── detection_service.py        # Servicio de detección
│   ├── event_service.py            # Gestión de eventos
│   ├── alert_service.py            # Sistema de alertas
│   └── storage_service.py          # Almacenamiento de imágenes
│
├── api/                             # API REST (Flask/FastAPI)
│   ├── __init__.py
│   ├── app.py                      # Aplicación web
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── personas.py             # Endpoints de personas
│   │   ├── camaras.py              # Endpoints de cámaras
│   │   ├── eventos.py              # Endpoints de eventos
│   │   └── dashboard.py            # Endpoints del dashboard
│   └── middleware.py               # Middleware de autenticación, etc.
│
├── utils/                           # Utilidades
│   ├── __init__.py
│   ├── logger.py                   # Sistema de logging
│   ├── image_utils.py              # Procesamiento de imágenes
│   └── validators.py               # Validadores
│
├── frontend/                        # Frontend web (opcional)
│   └── static/
│       ├── index.html
│       ├── css/
│       └── js/
│
├── data/                            # Datos persistentes
│   ├── database.db                 # Base de datos SQLite
│   ├── known_faces/                # Imágenes de referencia
│   ├── captures/                   # Capturas de detecciones
│   └── logs/                       # Archivos de log
│
└── tests/                           # Tests unitarios
    ├── __init__.py
    ├── test_detector.py
    └── test_recognizer.py
"""

# =============================================================================
# config.py - Configuración centralizada
# =============================================================================

import os
from pathlib import Path


class Config:
    # Rutas base
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    DB_PATH = DATA_DIR / 'database.db'
    KNOWN_FACES_DIR = DATA_DIR / 'known_faces'
    CAPTURES_DIR = DATA_DIR / 'captures'
    LOGS_DIR = DATA_DIR / 'logs'

    # Crear directorios si no existen
    for directory in [DATA_DIR, KNOWN_FACES_DIR, CAPTURES_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    # Configuración de reconocimiento facial
    FACE_RECOGNITION_TOLERANCE = 0.6  # Menor = más estricto
    FACE_DETECTION_MODEL = 'hog'  # 'hog' o 'cnn' (cnn es más preciso pero lento)
    MIN_FACE_SIZE = 50  # Píxeles mínimos para considerar un rostro

    # Configuración de video
    FRAME_SKIP = 2  # Procesar 1 de cada N frames para optimizar
    MAX_FPS = 30
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480

    # Configuración de alertas
    ALERT_COOLDOWN = 30  # Segundos entre alertas de la misma persona
    ENABLE_ALERTS = True

    # Configuración de almacenamiento
    SAVE_UNKNOWN_FACES = True
    SAVE_FULL_FRAMES = True
    IMAGE_RETENTION_DAYS = 30

    # API
    API_HOST = '0.0.0.0'
    API_PORT = 5000
    API_DEBUG = True

    # Logging
    LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
    LOG_TO_FILE = True
    LOG_TO_CONSOLE = True


# =============================================================================
# main.py - Punto de entrada
# =============================================================================

"""
import sys
import signal
from core.video_capture import VideoCapture
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from services.detection_service import DetectionService
from database.db_manager import DatabaseManager
from utils.logger import setup_logger
from config import Config

logger = setup_logger(__name__)

class VideovigilanciaSystem:
    def __init__(self):
        self.db_manager = DatabaseManager(Config.DB_PATH)
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer(self.db_manager)
        self.detection_service = DetectionService(
            self.db_manager,
            self.face_detector,
            self.face_recognizer
        )
        self.running = False

    def start(self, camera_source=0):
        self.running = True
        video_capture = VideoCapture(camera_source)

        logger.info("Sistema iniciado. Presiona 'q' para salir.")

        try:
            for frame in video_capture.read_frames():
                if not self.running:
                    break

                # Procesar frame
                results = self.detection_service.process_frame(frame, camera_id=1)

                # Aquí puedes añadir visualización o logging
                # cv2.imshow('Videovigilancia', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break

        except KeyboardInterrupt:
            logger.info("Interrupción del usuario")
        finally:
            video_capture.release()
            self.stop()

    def stop(self):
        self.running = False
        logger.info("Sistema detenido")

def signal_handler(sig, frame):
    logger.info('Señal de interrupción recibida')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    system = VideovigilanciaSystem()

    # Iniciar con webcam (0) o cámara IP (url)
    camera_source = 0  # Cambiar a URL para cámara IP
    system.start(camera_source)
"""