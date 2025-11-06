# core/video_capture.py

import cv2
import numpy as np
from typing import Generator, Optional, Tuple
import time
from threading import Thread, Lock
import queue


class VideoCapture:
    """
    Gestor unificado de captura de video que soporta:
    - Webcam (índice numérico)
    - Cámaras IP (URL RTSP/HTTP)
    - Archivos de video (para testing)
    """

    def __init__(self, source, frame_width: int = 640, frame_height: int = 480,
                 max_fps: int = 30, frame_skip: int = 1):
        """
        Args:
            source: Puede ser int (webcam), str (URL o path), o objeto VideoCapture
            frame_width: Ancho del frame
            frame_height: Alto del frame
            max_fps: FPS máximo de procesamiento
            frame_skip: Procesar 1 de cada N frames (para optimizar)
        """
        self.source = source
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.max_fps = max_fps
        self.frame_skip = frame_skip

        self.cap = None
        self.is_running = False
        self.frame_count = 0

        # Para modo threading (opcional, mejor rendimiento)
        self.use_threading = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.thread = None
        self.lock = Lock()

        self._initialize_capture()

    def _initialize_capture(self):
        """Inicializa la captura de video según el tipo de fuente"""
        try:
            # Si es un número, es una webcam
            if isinstance(self.source, int):
                self.cap = cv2.VideoCapture(self.source)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                print(f"✓ Webcam {self.source} inicializada")

            # Si es string, puede ser URL o archivo
            elif isinstance(self.source, str):
                # Detectar si es URL de cámara IP
                if self.source.startswith(('rtsp://', 'http://', 'https://')):
                    self.cap = cv2.VideoCapture(self.source)
                    print(f"✓ Cámara IP conectada: {self.source[:50]}...")
                else:
                    # Es un archivo de video
                    self.cap = cv2.VideoCapture(self.source)
                    print(f"✓ Archivo de video abierto: {self.source}")

            else:
                raise ValueError(f"Tipo de fuente no válido: {type(self.source)}")

            if not self.cap.isOpened():
                raise RuntimeError(f"No se pudo abrir la fuente de video: {self.source}")

            # Configurar buffer (importante para cámaras IP)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.is_running = True

        except Exception as e:
            print(f"✗ Error al inicializar captura: {e}")
            raise

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Lee un frame de la fuente de video

        Returns:
            Tuple[bool, np.ndarray]: (éxito, frame)
        """
        if not self.cap or not self.is_running:
            return False, None

        ret, frame = self.cap.read()

        if not ret:
            return False, None

        # Redimensionar si es necesario
        if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))

        self.frame_count += 1
        return True, frame

    def read_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Generador que yield frames continuamente
        Respeta frame_skip y max_fps

        Yields:
            np.ndarray: Frame de video
        """
        frame_time = 1.0 / self.max_fps
        last_time = time.time()

        while self.is_running:
            current_time = time.time()

            # Control de FPS
            if current_time - last_time < frame_time:
                time.sleep(frame_time - (current_time - last_time))

            ret, frame = self.read_frame()

            if not ret:
                print("⚠ No se pudo leer frame, intentando reconectar...")
                self._reconnect()
                continue

            # Aplicar frame skip
            if self.frame_count % self.frame_skip == 0:
                last_time = time.time()
                yield frame

    def start_threaded(self):
        """Inicia captura en un thread separado (mejor rendimiento)"""
        if self.use_threading:
            return

        self.use_threading = True
        self.thread = Thread(target=self._capture_thread, daemon=True)
        self.thread.start()
        print("✓ Captura en modo threading iniciada")

    def _capture_thread(self):
        """Thread que captura frames continuamente"""
        while self.is_running:
            ret, frame = self.read_frame()

            if ret:
                # Limpiar cola si está llena
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                try:
                    self.frame_queue.put(frame, timeout=1)
                except queue.Full:
                    pass

    def get_frame_threaded(self) -> Optional[np.ndarray]:
        """Obtiene un frame del queue (para modo threading)"""
        if not self.use_threading:
            raise RuntimeError("Modo threading no está activado")

        try:
            return self.frame_queue.get(timeout=1)
        except queue.Empty:
            return None

    def _reconnect(self, max_attempts: int = 3):
        """Intenta reconectar a la fuente de video"""
        for attempt in range(max_attempts):
            print(f"Intento de reconexión {attempt + 1}/{max_attempts}...")

            self.release()
            time.sleep(2)

            try:
                self._initialize_capture()
                print("✓ Reconexión exitosa")
                return True
            except:
                continue

        print("✗ No se pudo reconectar")
        self.is_running = False
        return False

    def get_properties(self) -> dict:
        """Obtiene propiedades de la captura"""
        if not self.cap:
            return {}

        return {
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': int(self.cap.get(cv2.CAP_PROP_FPS)),
            'frame_count': self.frame_count,
            'is_running': self.is_running,
            'backend': self.cap.getBackendName()
        }

    def is_opened(self) -> bool:
        """Verifica si la captura está abierta"""
        return self.cap is not None and self.cap.isOpened()

    def release(self):
        """Libera recursos de la captura"""
        self.is_running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

        if self.cap:
            self.cap.release()
            self.cap = None

        print("✓ Recursos de captura liberados")

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.release()

    def __del__(self):
        """Destructor"""
        self.release()


class MultiCameraCapture:
    """
    Gestor de múltiples cámaras simultáneas
    Útil para sistemas con varias cámaras
    """

    def __init__(self, sources: list):
        """
        Args:
            sources: Lista de fuentes (int, str, etc.)
        """
        self.sources = sources
        self.captures = {}
        self.initialize_all()

    def initialize_all(self):
        """Inicializa todas las cámaras"""
        for idx, source in enumerate(self.sources):
            try:
                capture = VideoCapture(source)
                self.captures[idx] = {
                    'capture': capture,
                    'source': source,
                    'active': True
                }
                print(f"✓ Cámara {idx} inicializada")
            except Exception as e:
                print(f"✗ Error con cámara {idx}: {e}")
                self.captures[idx] = {
                    'capture': None,
                    'source': source,
                    'active': False
                }

    def read_all_frames(self) -> dict:
        """Lee frames de todas las cámaras activas"""
        frames = {}

        for idx, cam_data in self.captures.items():
            if cam_data['active'] and cam_data['capture']:
                ret, frame = cam_data['capture'].read_frame()
                if ret:
                    frames[idx] = frame

        return frames

    def get_camera(self, idx: int) -> Optional[VideoCapture]:
        """Obtiene una cámara específica"""
        cam_data = self.captures.get(idx)
        return cam_data['capture'] if cam_data else None

    def release_all(self):
        """Libera todas las cámaras"""
        for cam_data in self.captures.values():
            if cam_data['capture']:
                cam_data['capture'].release()

        print("✓ Todas las cámaras liberadas")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_all()


# =============================================================================
# UTILIDADES PARA TESTING
# =============================================================================

def test_camera(source=0, duration: int = 10):
    """
    Prueba una cámara durante X segundos

    Args:
        source: Fuente de video
        duration: Duración del tests en segundos
    """
    print(f"\n{'=' * 60}")
    print(f"Probando cámara: {source}")
    print(f"Duración: {duration} segundos")
    print(f"{'=' * 60}\n")

    try:
        with VideoCapture(source) as cap:
            print(f"Propiedades: {cap.get_properties()}\n")

            start_time = time.time()
            frame_count = 0

            for frame in cap.read_frames():
                frame_count += 1

                # Mostrar frame con información
                cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {cap.max_fps}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Presiona 'q' para salir", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                cv2.imshow('Test de Cámara', frame)

                # Salir con 'q' o cuando se cumpla el tiempo
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                if time.time() - start_time > duration:
                    break

            elapsed = time.time() - start_time
            avg_fps = frame_count / elapsed if elapsed > 0 else 0

            print(f"\n{'=' * 60}")
            print(f"Test completado:")
            print(f"  - Frames capturados: {frame_count}")
            print(f"  - Tiempo transcurrido: {elapsed:.2f}s")
            print(f"  - FPS promedio: {avg_fps:.2f}")
            print(f"{'=' * 60}\n")

    except Exception as e:
        print(f"\n✗ Error durante el tests: {e}\n")

    finally:
        cv2.destroyAllWindows()


if __name__ == '__main__':
    # Probar con webcam
    test_camera(source=0, duration=10)

    # Para probar con cámara IP, descomentar:
    # test_camera(source='rtsp://usuario:password@ip:puerto/stream', duration=10)