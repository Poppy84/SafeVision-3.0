# core/face_detector.py

import face_recognition
import cv2
import numpy as np
from typing import List, Tuple, Dict
import time


class FaceDetector:
    """
    Detector de rostros optimizado para videovigilancia
    Usa face_recognition (basado en dlib) para detectar rostros en frames
    """

    def __init__(self,
                 model: str = 'hog',
                 min_face_size: int = 50,
                 number_of_times_to_upsample: int = 1):
        """
        Args:
            model: 'hog' (rápido, CPU) o 'cnn' (preciso, GPU)
            min_face_size: Tamaño mínimo de rostro en píxeles
            number_of_times_to_upsample: Veces que escalar imagen para detectar rostros pequeños
        """
        self.model = model
        self.min_face_size = min_face_size
        self.upsample = number_of_times_to_upsample

        # Estadísticas
        self.total_detections = 0
        self.total_processing_time = 0

        print(f"✓ FaceDetector inicializado (modelo: {model})")

    def detect_faces(self, frame: np.ndarray,
                     scale_factor: float = 0.5) -> List[Tuple[int, int, int, int]]:
        """
        Detecta rostros en un frame

        Args:
            frame: Frame de video (BGR)
            scale_factor: Factor de escala para optimizar velocidad (0.5 = mitad del tamaño)

        Returns:
            Lista de ubicaciones de rostros [(top, right, bottom, left), ...]
        """
        start_time = time.time()

        # Optimización: reducir tamaño del frame
        small_frame = frame
        if scale_factor < 1.0:
            small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)

        # Convertir de BGR (OpenCV) a RGB (face_recognition)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detectar rostros
        face_locations = face_recognition.face_locations(
            rgb_frame,
            number_of_times_to_upsample=self.upsample,
            model=self.model
        )

        # Escalar coordenadas de vuelta al tamaño original
        if scale_factor < 1.0:
            face_locations = [
                (int(top / scale_factor), int(right / scale_factor),
                 int(bottom / scale_factor), int(left / scale_factor))
                for top, right, bottom, left in face_locations
            ]

        # Filtrar rostros muy pequeños
        face_locations = [
            loc for loc in face_locations
            if self._is_valid_face(loc)
        ]

        # Estadísticas
        processing_time = time.time() - start_time
        self.total_detections += len(face_locations)
        self.total_processing_time += processing_time

        return face_locations

    def _is_valid_face(self, location: Tuple[int, int, int, int]) -> bool:
        """Verifica si un rostro detectado cumple los requisitos mínimos"""
        top, right, bottom, left = location
        width = right - left
        height = bottom - top

        # Verificar tamaño mínimo
        if width < self.min_face_size or height < self.min_face_size:
            return False

        # Verificar aspect ratio razonable (evitar falsos positivos)
        aspect_ratio = width / height if height > 0 else 0
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            return False

        return True

    def extract_face_encodings(self, frame: np.ndarray,
                               face_locations: List[Tuple[int, int, int, int]],
                               num_jitters: int = 1) -> List[np.ndarray]:
        """
        Extrae encodings (características) de los rostros detectados

        Args:
            frame: Frame de video (BGR)
            face_locations: Ubicaciones de rostros detectados
            num_jitters: Número de re-muestreos para mejorar precisión (1=rápido, 10=preciso)

        Returns:
            Lista de encodings faciales (vectores de 128 dimensiones)
        """
        if not face_locations:
            return []

        # Convertir a RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Extraer encodings
        encodings = face_recognition.face_encodings(
            rgb_frame,
            known_face_locations=face_locations,
            num_jitters=num_jitters
        )

        return encodings

    def detect_and_encode(self, frame: np.ndarray,
                          scale_factor: float = 0.5,
                          num_jitters: int = 1) -> List[Dict]:
        """
        Detecta rostros y extrae encodings en un solo paso

        Returns:
            Lista de diccionarios con 'location' y 'encoding'
        """
        # Detectar rostros
        face_locations = self.detect_faces(frame, scale_factor)

        if not face_locations:
            return []

        # Extraer encodings
        encodings = self.extract_face_encodings(frame, face_locations, num_jitters)

        # Combinar resultados
        results = []
        for location, encoding in zip(face_locations, encodings):
            results.append({
                'location': location,
                'encoding': encoding,
                'confidence': 1.0  # Placeholder, se calcula en el reconocimiento
            })

        return results

    def draw_faces(self, frame: np.ndarray,
                   face_locations: List[Tuple[int, int, int, int]],
                   labels: List[str] = None,
                   color: Tuple[int, int, int] = (0, 255, 0),
                   thickness: int = 2) -> np.ndarray:
        """
        Dibuja rectángulos alrededor de los rostros detectados

        Args:
            frame: Frame de video
            face_locations: Ubicaciones de rostros
            labels: Etiquetas opcionales para cada rostro
            color: Color del rectángulo (BGR)
            thickness: Grosor de las líneas

        Returns:
            Frame con rostros marcados
        """
        frame_copy = frame.copy()

        for idx, (top, right, bottom, left) in enumerate(face_locations):
            # Dibujar rectángulo
            cv2.rectangle(frame_copy, (left, top), (right, bottom), color, thickness)

            # Dibujar etiqueta si existe
            if labels and idx < len(labels):
                label = labels[idx]

                # Calcular tamaño del texto
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 0.6
                font_thickness = 1

                (text_width, text_height), baseline = cv2.getTextSize(
                    label, font, font_scale, font_thickness
                )

                # Dibujar fondo para el texto
                cv2.rectangle(
                    frame_copy,
                    (left, bottom + 5),
                    (left + text_width + 10, bottom + text_height + baseline + 10),
                    color,
                    cv2.FILLED
                )

                # Dibujar texto
                cv2.putText(
                    frame_copy,
                    label,
                    (left + 5, bottom + text_height + 5),
                    font,
                    font_scale,
                    (255, 255, 255),
                    font_thickness
                )

        return frame_copy

    def get_face_image(self, frame: np.ndarray,
                       location: Tuple[int, int, int, int],
                       padding: int = 20) -> np.ndarray:
        """
        Extrae la imagen de un rostro específico con padding

        Args:
            frame: Frame completo
            location: (top, right, bottom, left)
            padding: Píxeles adicionales alrededor del rostro

        Returns:
            Imagen del rostro recortada
        """
        top, right, bottom, left = location
        height, width = frame.shape[:2]

        # Aplicar padding con límites
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        left = max(0, left - padding)

        # Extraer rostro
        face_image = frame[top:bottom, left:right]

        return face_image

    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del detector"""
        avg_time = (self.total_processing_time / self.total_detections
                    if self.total_detections > 0 else 0)

        return {
            'total_detections': self.total_detections,
            'total_processing_time': round(self.total_processing_time, 2),
            'average_time_per_detection': round(avg_time, 4),
            'model': self.model,
            'min_face_size': self.min_face_size
        }

    def reset_statistics(self):
        """Reinicia las estadísticas"""
        self.total_detections = 0
        self.total_processing_time = 0


# =============================================================================
# UTILIDADES Y TESTS
# =============================================================================

def test_detector_with_image(image_path: str):
    """Prueba el detector con una imagen"""
    print("\n" + "=" * 70)
    print("TEST: FaceDetector con imagen")
    print("=" * 70 + "\n")

    # Cargar imagen
    image = cv2.imread(image_path)
    if image is None:
        print(f"✗ No se pudo cargar la imagen: {image_path}")
        return

    print(f"✓ Imagen cargada: {image.shape}")

    # Crear detector
    detector = FaceDetector(model='hog')

    # Detectar rostros
    print("\nDetectando rostros...")
    face_locations = detector.detect_faces(image)

    print(f"✓ Rostros detectados: {len(face_locations)}")

    # Dibujar resultados
    result_image = detector.draw_faces(
        image,
        face_locations,
        labels=[f"Rostro {i + 1}" for i in range(len(face_locations))]
    )

    # Mostrar imagen
    cv2.imshow('Detección de Rostros', result_image)
    print("\nPresiona cualquier tecla en la ventana para cerrar...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Estadísticas
    print("\nEstadísticas:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def test_detector_with_webcam(duration: int = 10):
    """Prueba el detector con webcam en tiempo real"""
    print("\n" + "=" * 70)
    print("TEST: FaceDetector con webcam")
    print("=" * 70 + "\n")

    # Importar VideoCapture
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.video_capture import VideoCapture

    # Crear detector y captura
    detector = FaceDetector(model='hog')
    cap = VideoCapture(source=0)

    print(f"✓ Iniciando detección por {duration} segundos...")
    print("Presiona 'q' para salir antes\n")

    start_time = time.time()
    frame_count = 0

    try:
        for frame in cap.read_frames():
            frame_count += 1

            # Detectar rostros
            face_locations = detector.detect_faces(frame, scale_factor=0.5)

            # Dibujar resultados
            result_frame = detector.draw_faces(
                frame,
                face_locations,
                labels=[f"Persona {i + 1}" for i in range(len(face_locations))]
            )

            # Información en pantalla
            info_text = f"Rostros: {len(face_locations)} | Frame: {frame_count}"
            cv2.putText(result_frame, info_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            cv2.imshow('Detección en Tiempo Real', result_frame)

            # Salir con 'q' o después del tiempo
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if time.time() - start_time > duration:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    # Estadísticas finales
    print("\n" + "=" * 70)
    print("Estadísticas finales:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    # Descomentar para probar
    # test_detector_with_webcam(duration=10)
    pass