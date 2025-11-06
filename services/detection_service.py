# services/detection_service.py

import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time


class DetectionService:
    """
    Servicio principal que orquesta detección, reconocimiento y almacenamiento
    Este es el cerebro que une todos los componentes
    """

    def __init__(self, db_manager, face_detector, face_recognizer,
                 save_captures: bool = True,
                 alert_on_unknown: bool = True,
                 cooldown_seconds: int = 30):
        """
        Args:
            db_manager: Gestor de base de datos
            face_detector: Detector de rostros
            face_recognizer: Reconocedor facial
            save_captures: Guardar imágenes de las detecciones
            alert_on_unknown: Generar alertas para desconocidos
            cooldown_seconds: Tiempo mínimo entre detecciones de la misma persona
        """
        self.db = db_manager
        self.detector = face_detector
        self.recognizer = face_recognizer

        self.save_captures = save_captures
        self.alert_on_unknown = alert_on_unknown
        self.cooldown_seconds = cooldown_seconds

        # Cache para evitar detecciones repetidas
        from core.face_recognizer import RecognitionCache
        self.cache = RecognitionCache(cooldown_seconds=cooldown_seconds)

        # Estadísticas de sesión
        self.session_stats = {
            'frames_processed': 0,
            'faces_detected': 0,
            'known_detected': 0,
            'unknown_detected': 0,
            'events_created': 0,
            'start_time': datetime.now()
        }

        print("✓ DetectionService inicializado")

    def process_frame(self, frame: np.ndarray, camera_id: int,
                      scale_factor: float = 0.5) -> Dict:
        """
        Procesa un frame completo: detecta, reconoce y almacena

        Args:
            frame: Frame de video
            camera_id: ID de la cámara
            scale_factor: Factor de escala para optimización

        Returns:
            Diccionario con resultados del procesamiento
        """
        start_time = time.time()

        # Detectar y codificar rostros
        detections = self.detector.detect_and_encode(frame, scale_factor=scale_factor)

        results = {
            'timestamp': datetime.now(),
            'camera_id': camera_id,
            'faces_detected': len(detections),
            'recognitions': [],
            'processing_time': 0
        }

        if not detections:
            self.session_stats['frames_processed'] += 1
            results['processing_time'] = time.time() - start_time
            return results

        # Reconocer cada rostro
        for detection in detections:
            location = detection['location']
            encoding = detection['encoding']

            # Reconocer rostro
            recognition = self.recognizer.recognize_face(encoding)

            # Verificar si debe procesarse (cooldown)
            should_save = self.cache.should_process(recognition['persona_id'])

            if should_save:
                # Procesar detección
                result = self._process_detection(
                    frame=frame,
                    location=location,
                    recognition=recognition,
                    camera_id=camera_id
                )

                results['recognitions'].append(result)

                # Actualizar estadísticas
                self.session_stats['faces_detected'] += 1
                if recognition['es_desconocido']:
                    self.session_stats['unknown_detected'] += 1
                else:
                    self.session_stats['known_detected'] += 1
            else:
                # Persona ya vista recientemente, solo agregar info visual
                results['recognitions'].append({
                    'persona_id': recognition['persona_id'],
                    'nombre': recognition['nombre'],
                    'tipo': recognition['tipo'],
                    'confianza': recognition['confianza'],
                    'location': location,
                    'cached': True,
                    'cooldown_remaining': self.cache.get_time_until_next(
                        recognition['persona_id']
                    )
                })

        self.session_stats['frames_processed'] += 1
        results['processing_time'] = time.time() - start_time

        return results

    def _process_detection(self, frame: np.ndarray, location: Tuple,
                           recognition: Dict, camera_id: int) -> Dict:
        """
        Procesa una detección individual: guarda en BD, crea eventos, guarda imágenes
        """
        # Guardar imágenes si está habilitado
        imagen_captura = None
        imagen_frame = None

        if self.save_captures:
            imagen_captura = self._save_face_capture(frame, location, recognition)
            imagen_frame = self._save_full_frame(frame, recognition)

        # Registrar detección en BD
        deteccion_id = self.db.registrar_deteccion(
            camara_id=camera_id,
            persona_id=recognition['persona_id'],
            confianza=recognition['confianza'],
            es_desconocido=recognition['es_desconocido'],
            imagen_captura=imagen_captura,
            imagen_frame=imagen_frame
        )

        # Crear eventos si es necesario
        evento_id = None
        if recognition['es_desconocido'] and self.alert_on_unknown:
            evento_id = self._create_unknown_event(deteccion_id, camera_id)
            self.session_stats['events_created'] += 1

        return {
            'deteccion_id': deteccion_id,
            'evento_id': evento_id,
            'persona_id': recognition['persona_id'],
            'nombre': recognition['nombre'],
            'tipo': recognition['tipo'],
            'confianza': recognition['confianza'],
            'es_desconocido': recognition['es_desconocido'],
            'location': location,
            'imagen_captura': imagen_captura,
            'cached': False
        }

    def _save_face_capture(self, frame: np.ndarray, location: Tuple,
                           recognition: Dict) -> str:
        """Guarda la imagen del rostro recortado"""
        try:
            # Extraer rostro
            face_image = self.detector.get_face_image(frame, location, padding=20)

            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            nombre = recognition['nombre'].replace(" ", "_")
            filename = f"face_{nombre}_{timestamp}.jpg"

            # Ruta completa
            from config import Config
            filepath = Config.CAPTURES_DIR / filename

            # Guardar imagen
            cv2.imwrite(str(filepath), face_image)

            return str(filepath)

        except Exception as e:
            print(f"⚠ Error guardando captura de rostro: {e}")
            return None

    def _save_full_frame(self, frame: np.ndarray, recognition: Dict) -> str:
        """Guarda el frame completo con contexto"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            nombre = recognition['nombre'].replace(" ", "_")
            filename = f"frame_{nombre}_{timestamp}.jpg"

            from config import Config
            filepath = Config.CAPTURES_DIR / filename

            cv2.imwrite(str(filepath), frame)

            return str(filepath)

        except Exception as e:
            print(f"⚠ Error guardando frame completo: {e}")
            return None

    def _create_unknown_event(self, deteccion_id: int, camera_id: int) -> int:
        """Crea un evento de alerta para persona desconocida"""
        evento_id = self.db.crear_evento(
            tipo='intruso_detectado',
            severidad='alta',
            descripcion='Persona desconocida detectada en el sistema',
            deteccion_id=deteccion_id,
            camara_id=camera_id
        )

        return evento_id

    def process_and_display(self, frame: np.ndarray, camera_id: int,
                            show_info: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        Procesa un frame y lo prepara para visualización

        Returns:
            Tuple[frame_procesado, resultados]
        """
        # Procesar frame
        results = self.process_frame(frame, camera_id)

        # Dibujar resultados en el frame
        display_frame = frame.copy()

        for recognition in results['recognitions']:
            location = recognition['location']
            nombre = recognition['nombre']
            confianza = recognition.get('confianza', 0)
            es_desconocido = recognition.get('es_desconocido', False)
            cached = recognition.get('cached', False)

            # Color según tipo
            if es_desconocido:
                color = (0, 0, 255)  # Rojo para desconocidos
                label = f"⚠ {nombre}"
            elif cached:
                color = (128, 128, 128)  # Gris para cacheados
                cooldown = recognition.get('cooldown_remaining', 0)
                label = f"{nombre} ({cooldown:.0f}s)"
            else:
                color = (0, 255, 0)  # Verde para conocidos
                label = f"✓ {nombre} ({confianza:.0%})"

            # Dibujar rectángulo y etiqueta
            top, right, bottom, left = location
            cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)

            # Fondo para texto
            cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)

            # Texto
            cv2.putText(display_frame, label, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

        # Información adicional en pantalla
        if show_info:
            info_lines = [
                f"Rostros: {results['faces_detected']}",
                f"Procesamiento: {results['processing_time'] * 1000:.0f}ms",
                f"Frames: {self.session_stats['frames_processed']}"
            ]

            y_pos = 30
            for line in info_lines:
                cv2.putText(display_frame, line, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                y_pos += 30

        return display_frame, results

    def get_session_stats(self) -> Dict:
        """Obtiene estadísticas de la sesión actual"""
        elapsed = datetime.now() - self.session_stats['start_time']

        return {
            **self.session_stats,
            'elapsed_time': str(elapsed).split('.')[0],
            'fps': (self.session_stats['frames_processed'] / elapsed.total_seconds()
                    if elapsed.total_seconds() > 0 else 0)
        }

    def reset_session_stats(self):
        """Reinicia las estadísticas de sesión"""
        self.session_stats = {
            'frames_processed': 0,
            'faces_detected': 0,
            'known_detected': 0,
            'unknown_detected': 0,
            'events_created': 0,
            'start_time': datetime.now()
        }

        self.cache.clear_cache()

    def register_new_person_from_frame(self, frame: np.ndarray,
                                       nombre: str, apellido: str,
                                       tipo: str = 'residente') -> Dict:
        """
        Registra una nueva persona desde un frame
        Útil para agregar personas directamente desde la cámara

        Returns:
            Diccionario con resultado del registro
        """
        # Detectar rostros
        detections = self.detector.detect_and_encode(frame, scale_factor=1.0)

        if len(detections) == 0:
            return {
                'success': False,
                'error': 'No se detectó ningún rostro en el frame'
            }

        if len(detections) > 1:
            return {
                'success': False,
                'error': f'Se detectaron {len(detections)} rostros. Solo debe haber uno.'
            }

        # Extraer encoding y ubicación
        detection = detections[0]
        encoding = detection['encoding']
        location = detection['location']

        # Guardar foto de referencia
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{nombre.lower()}_{apellido.lower()}_{timestamp}.jpg"

        from config import Config
        foto_path = Config.KNOWN_FACES_DIR / filename

        # Extraer y guardar rostro
        face_image = self.detector.get_face_image(frame, location, padding=20)
        cv2.imwrite(str(foto_path), face_image)

        # Agregar a la base de datos
        persona_id = self.recognizer.add_new_person(
            nombre=nombre,
            apellido=apellido,
            face_encoding=encoding,
            tipo=tipo,
            foto_referencia=str(foto_path)
        )

        return {
            'success': True,
            'persona_id': persona_id,
            'nombre': f"{nombre} {apellido}",
            'foto': str(foto_path)
        }


# =============================================================================
# FUNCIÓN PRINCIPAL PARA DEMO
# =============================================================================

def run_live_detection(camera_source=0, duration: int = 60):
    """
    Ejecuta el sistema completo en tiempo real
    Perfecto para demos y presentaciones
    """
    print("\n" + "=" * 70)
    print("SISTEMA DE VIDEOVIGILANCIA INTELIGENTE - DEMO EN VIVO")
    print("=" * 70 + "\n")

    # Importar dependencias
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from database.db_manager import DatabaseManager
    from core.video_capture import VideoCapture
    from core.face_detector import FaceDetector
    from core.face_recognizer import FaceRecognizer
    from config import Config

    # Inicializar componentes
    print("Inicializando sistema...")
    db = DatabaseManager(Config.DB_PATH)

    # Verificar si hay cámaras registradas
    camaras = db.obtener_camaras_activas()
    if not camaras:
        print("→ Registrando cámara...")
        camera_id = db.agregar_camara(
            nombre="Cámara Demo",
            ubicacion="Sistema principal",
            tipo="webcam"
        )
    else:
        camera_id = camaras[0]['id']

    # Crear detector y reconocedor
    detector = FaceDetector(model='hog')
    recognizer = FaceRecognizer(db, tolerance=0.6)

    # Crear servicio de detección
    service = DetectionService(
        db_manager=db,
        face_detector=detector,
        face_recognizer=recognizer,
        save_captures=True,
        alert_on_unknown=True,
        cooldown_seconds=30
    )

    # Iniciar captura
    cap = VideoCapture(source=camera_source)

    print(f"\n✓ Sistema iniciado correctamente")
    print(f"✓ Duración: {duration} segundos")
    print(f"✓ Personas conocidas: {len(recognizer.known_names)}")
    print("\nControles:")
    print("  - Presiona 'q' para salir")
    print("  - Presiona 's' para ver estadísticas")
    print("\n" + "=" * 70 + "\n")

    start_time = time.time()

    try:
        for frame in cap.read_frames():
            # Procesar y mostrar
            display_frame, results = service.process_and_display(
                frame, camera_id, show_info=True
            )

            cv2.imshow('Videovigilancia Inteligente - Demo', display_frame)

            # Controles de teclado
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n→ Salida manual")
                break
            elif key == ord('s'):
                stats = service.get_session_stats()
                print("\n" + "=" * 70)
                print("ESTADÍSTICAS DE SESIÓN:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                print("=" * 70 + "\n")

            # Salir después del tiempo
            if time.time() - start_time > duration:
                print("\n→ Tiempo completado")
                break

    finally:
        # Limpiar
        cap.release()
        cv2.destroyAllWindows()

        # Estadísticas finales
        print("\n" + "=" * 70)
        print("RESUMEN FINAL:")
        stats = service.get_session_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 70 + "\n")

        db.close()


if __name__ == '__main__':
    # Ejecutar demo
    run_live_detection(camera_source=0, duration=60)