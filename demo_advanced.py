# demo_advanced.py
"""
Demo del sistema con features avanzados de IA
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cv2
import time
from datetime import datetime

from database.db_manager import DatabaseManager
from core.video_capture import VideoCapture
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from services.detection_service import DetectionService
from core.advanced_features import (
    AdvancedDetectionService,
    PeopleCounter,
    RestrictedZone,
    BehaviorAnalyzer
)
from config import Config


def demo_contador_personas(duration: int = 30):
    """Demo del contador de personas"""
    print("\n" + "=" * 70)
    print("DEMO: CONTADOR DE PERSONAS")
    print("=" * 70)
    print("\nEste feature cuenta:")
    print("  - Número actual de personas en pantalla")
    print("  - Total de entradas (cruzan línea amarilla hacia abajo)")
    print("  - Total de salidas (cruzan línea amarilla hacia arriba)")
    print(f"\nDuración: {duration} segundos")
    print("Presiona 'q' para salir antes\n")

    input("Presiona ENTER para iniciar...")

    # Inicializar componentes básicos
    db = DatabaseManager(Config.DB_PATH)
    detector = FaceDetector(model='hog')
    recognizer = FaceRecognizer(db, tolerance=0.6)

    camaras = db.obtener_camaras_activas()
    camera_id = camaras[0]['id'] if camaras else 1

    base_service = DetectionService(db, detector, recognizer)

    # Crear servicio avanzado con contador
    advanced_service = AdvancedDetectionService(
        base_service,
        enable_counting=True,
        enable_zones=False,
        enable_behavior=False
    )

    # Iniciar captura
    cap = VideoCapture(source=0)
    start_time = time.time()

    try:
        print("\n✓ Sistema iniciado con contador de personas\n")

        for frame in cap.read_frames():
            # Procesar con features avanzados
            results = advanced_service.process_frame_advanced(frame, camera_id)

            # Dibujar resultados base
            display_frame, _ = base_service.process_and_display(frame, camera_id, show_info=False)

            # Agregar features avanzados
            display_frame = advanced_service.draw_advanced_features(display_frame, results)

            # Info adicional
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed

            cv2.putText(display_frame, f"Tiempo: {remaining}s",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            cv2.imshow('Demo: Contador de Personas', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if time.time() - start_time > duration:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()

        # Estadísticas finales
        if 'counter' in results:
            print("\n" + "=" * 70)
            print("ESTADÍSTICAS FINALES:")
            print("=" * 70)
            stats = results['counter']
            print(f"  Personas actuales: {stats['current_count']}")
            print(f"  Total de entradas: {stats['total_entries']}")
            print(f"  Total de salidas: {stats['total_exits']}")
            print(f"  Balance: {stats['total_entries'] - stats['total_exits']}")
            print("=" * 70 + "\n")


def demo_zonas_restringidas(duration: int = 30):
    """Demo de zonas restringidas"""
    print("\n" + "=" * 70)
    print("DEMO: ZONAS RESTRINGIDAS")
    print("=" * 70)
    print("\nEste feature:")
    print("  - Define áreas restringidas en la imagen")
    print("  - Alerta cuando personas no autorizadas entran")
    print("  - Zona amarilla: Solo empleados")
    print("  - Zona se pone ROJA cuando hay violación")
    print(f"\nDuración: {duration} segundos\n")

    input("Presiona ENTER para iniciar...")

    # Inicializar
    db = DatabaseManager(Config.DB_PATH)
    detector = FaceDetector(model='hog')
    recognizer = FaceRecognizer(db, tolerance=0.6)

    camaras = db.obtener_camaras_activas()
    camera_id = camaras[0]['id'] if camaras else 1

    base_service = DetectionService(db, detector, recognizer)

    # Crear servicio con zonas
    advanced_service = AdvancedDetectionService(
        base_service,
        enable_counting=False,
        enable_zones=True,
        enable_behavior=False
    )

    # Definir zona restringida (centro de la imagen)
    # Primero necesitamos obtener dimensiones del frame
    cap = VideoCapture(source=0)
    ret, sample_frame = cap.read_frame()

    if ret:
        h, w = sample_frame.shape[:2]

        # Zona rectangular en el centro (solo empleados)
        center_zone = [
            (int(w * 0.3), int(h * 0.3)),  # Top-left
            (int(w * 0.7), int(h * 0.3)),  # Top-right
            (int(w * 0.7), int(h * 0.7)),  # Bottom-right
            (int(w * 0.3), int(h * 0.7))  # Bottom-left
        ]

        advanced_service.zones.add_zone(
            name="Area Restringida",
            polygon=center_zone,
            authorized_types=['empleado']
        )

        print("\n✓ Zona restringida configurada en el centro")
        print("  → Solo 'empleados' pueden entrar")
        print("  → Residentes y desconocidos generarán alerta\n")

    start_time = time.time()
    violations_detected = 0

    try:
        for frame in cap.read_frames():
            # Procesar
            results = advanced_service.process_frame_advanced(frame, camera_id)

            # Dibujar base
            display_frame, _ = base_service.process_and_display(frame, camera_id, show_info=False)

            # Dibujar zonas y violaciones
            display_frame = advanced_service.draw_advanced_features(display_frame, results)

            # Contar violaciones
            if results.get('zone_violations'):
                violations_detected += len(results['zone_violations'])

            # Info
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed

            cv2.putText(display_frame, f"Tiempo: {remaining}s | Violaciones: {violations_detected}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            cv2.imshow('Demo: Zonas Restringidas', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if time.time() - start_time > duration:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()

        print("\n" + "=" * 70)
        print("ESTADÍSTICAS FINALES:")
        print("=" * 70)
        print(f"  Violaciones detectadas: {violations_detected}")
        print("=" * 70 + "\n")


def demo_analisis_comportamiento(duration: int = 45):
    """Demo de análisis de comportamiento"""
    print("\n" + "=" * 70)
    print("DEMO: ANÁLISIS DE COMPORTAMIENTO")
    print("=" * 70)
    print("\nEste feature detecta comportamientos sospechosos:")
    print("  ⚠ Movimiento errático (zigzag)")
    print("  ⚠ Merodeo (quedarse mucho tiempo en un lugar)")
    print("  ⚠ Movimiento rápido (correr)")
    print("  ⚠ Patrullaje (ir y venir repetidamente)")
    print(f"\nDuración: {duration} segundos")
    print("\n💡 TIP: Muévete de diferentes formas para activar las alertas!\n")

    input("Presiona ENTER para iniciar...")

    # Inicializar
    db = DatabaseManager(Config.DB_PATH)
    detector = FaceDetector(model='hog')
    recognizer = FaceRecognizer(db, tolerance=0.6)

    camaras = db.obtener_camaras_activas()
    camera_id = camaras[0]['id'] if camaras else 1

    base_service = DetectionService(db, detector, recognizer)

    # Crear servicio con análisis de comportamiento
    advanced_service = AdvancedDetectionService(
        base_service,
        enable_counting=False,
        enable_zones=False,
        enable_behavior=True
    )

    cap = VideoCapture(source=0)
    start_time = time.time()

    behavior_counts = {
        'movimiento_errático': 0,
        'merodeo': 0,
        'movimiento_rápido': 0,
        'patrullaje': 0
    }

    try:
        print("\n✓ Análisis de comportamiento activo")
        print("→ Muévete frente a la cámara de diferentes formas\n")

        for frame in cap.read_frames():
            # Procesar
            results = advanced_service.process_frame_advanced(frame, camera_id)

            # Dibujar base
            display_frame, _ = base_service.process_and_display(frame, camera_id, show_info=False)

            # Dibujar alertas de comportamiento
            display_frame = advanced_service.draw_advanced_features(display_frame, results)

            # Contar comportamientos detectados
            for rec in results.get('recognitions', []):
                for behavior in rec.get('behaviors', []):
                    if behavior in behavior_counts:
                        behavior_counts[behavior] += 1

            # Info
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed

            cv2.putText(display_frame, f"Tiempo: {remaining}s",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Mostrar contadores en pantalla
            y_pos = frame.shape[0] - 100
            cv2.putText(display_frame, "Comportamientos detectados:",
                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_pos += 20
            for behavior, count in behavior_counts.items():
                if count > 0:
                    cv2.putText(display_frame, f"{behavior}: {count}",
                                (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                    y_pos += 20

            cv2.imshow('Demo: Análisis de Comportamiento', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if time.time() - start_time > duration:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()

        print("\n" + "=" * 70)
        print("COMPORTAMIENTOS DETECTADOS:")
        print("=" * 70)
        for behavior, count in behavior_counts.items():
            print(f"  {behavior}: {count}")
        print("=" * 70 + "\n")


def demo_completo_avanzado(duration: int = 60):
    """Demo con TODOS los features avanzados activados"""
    print("\n" + "=" * 70)
    print("DEMO COMPLETO: TODOS LOS FEATURES AVANZADOS")
    print("=" * 70)
    print("\nFeatures activos:")
    print("  ✓ Contador de personas")
    print("  ✓ Zonas restringidas")
    print("  ✓ Análisis de comportamiento")
    print("  ✓ Reconocimiento facial")
    print(f"\nDuración: {duration} segundos\n")

    input("Presiona ENTER para ver el poder completo del sistema...")

    # Inicializar todo
    db = DatabaseManager(Config.DB_PATH)
    detector = FaceDetector(model='hog')
    recognizer = FaceRecognizer(db, tolerance=0.6)

    camaras = db.obtener_camaras_activas()
    camera_id = camaras[0]['id'] if camaras else 1

    base_service = DetectionService(db, detector, recognizer)

    # Servicio con TODO activado
    advanced_service = AdvancedDetectionService(
        base_service,
        enable_counting=True,
        enable_zones=True,
        enable_behavior=True
    )

    # Configurar zona
    cap = VideoCapture(source=0)
    ret, sample_frame = cap.read_frame()

    if ret:
        h, w = sample_frame.shape[:2]
        zone = [
            (int(w * 0.3), int(h * 0.3)),
            (int(w * 0.7), int(h * 0.3)),
            (int(w * 0.7), int(h * 0.7)),
            (int(w * 0.3), int(h * 0.7))
        ]
        advanced_service.zones.add_zone("Zona VIP", zone, ['empleado'])

    start_time = time.time()

    try:
        print("\n✓ Sistema completo activado\n")

        for frame in cap.read_frames():
            # Procesar todo
            results = advanced_service.process_frame_advanced(frame, camera_id)

            # Dibujar todo
            display_frame, _ = base_service.process_and_display(frame, camera_id, show_info=False)
            display_frame = advanced_service.draw_advanced_features(display_frame, results)

            # Info general
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed

            cv2.putText(display_frame, f"SISTEMA COMPLETO | Tiempo: {remaining}s",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('Demo: Sistema Completo Avanzado', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if time.time() - start_time > duration:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

        # Estadísticas finales
        print("\n" + "=" * 70)
        print("ESTADÍSTICAS FINALES DEL SISTEMA COMPLETO:")
        print("=" * 70)
        stats = advanced_service.stats
        print(f"  Total alertas: {stats['total_alerts']}")
        print(f"  Violaciones de zona: {stats['zone_violations']}")
        print(f"  Alertas de comportamiento: {stats['behavior_alerts']}")
        print("=" * 70 + "\n")

        db.close()


def menu_principal():
    """Menú para seleccionar qué demo ejecutar"""
    while True:
        print("\n" + "=" * 70)
        print("DEMOS DE FEATURES AVANZADOS")
        print("=" * 70)
        print("\n1. Contador de personas (entrada/salida)")
        print("2. Zonas restringidas (control de acceso)")
        print("3. Análisis de comportamiento (detección de sospechosos)")
        print("4. DEMO COMPLETO (todos los features)")
        print("0. Salir")
        print("\n" + "=" * 70)

        opcion = input("\nSelecciona una opción: ").strip()

        if opcion == '1':
            demo_contador_personas()
        elif opcion == '2':
            demo_zonas_restringidas()
        elif opcion == '3':
            demo_analisis_comportamiento()
        elif opcion == '4':
            demo_completo_avanzado()
        elif opcion == '0':
            print("\n¡Hasta luego!")
            break
        else:
            print("\n✗ Opción inválida")

        input("\nPresiona ENTER para continuar...")


if __name__ == '__main__':
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n✗ Interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cv2.destroyAllWindows()