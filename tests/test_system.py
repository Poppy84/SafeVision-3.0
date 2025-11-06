# tests/test_system.py
"""
Scripts de prueba para validar cada componente del sistema
Ejecutar: python tests/test_system.py
"""

import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
import time
from datetime import datetime

# Importar nuestros módulos
from database.db_manager import DatabaseManager
from core.video_capture import VideoCapture, test_camera
from config import Config


# =============================================================================
# TEST 1: BASE DE DATOS
# =============================================================================

def test_database():
    """Prueba todas las funcionalidades de la base de datos"""
    print("\n" + "=" * 70)
    print("TEST 1: BASE DE DATOS")
    print("=" * 70 + "\n")

    try:
        # Inicializar BD
        db = DatabaseManager(Config.DB_PATH)
        print("✓ Base de datos inicializada")

        # Test 1.1: Agregar persona
        print("\n[1.1] Agregando persona de prueba...")
        encoding_fake = np.random.rand(128)  # Encoding fake para prueba
        persona_id = db.agregar_persona(
            nombre="Juan",
            apellido="Pérez",
            tipo="residente",
            encoding=encoding_fake,
            foto_referencia="data/known_faces/juan_perez.jpg",
            notas="Usuario de prueba"
        )
        print(f"✓ Persona agregada con ID: {persona_id}")

        # Test 1.2: Obtener personas activas
        print("\n[1.2] Obteniendo personas activas...")
        personas = db.obtener_personas_activas()
        print(f"✓ Personas encontradas: {len(personas)}")
        for p in personas:
            print(f"   - ID {p['id']}: {p['nombre']} {p['apellido']} ({p['tipo']})")

        # Test 1.3: Agregar cámara
        print("\n[1.3] Agregando cámara de prueba...")
        camara_id = db.agregar_camara(
            nombre="Cámara Principal",
            ubicacion="Entrada principal",
            tipo="webcam",
            url_stream=None
        )
        print(f"✓ Cámara agregada con ID: {camara_id}")

        # Test 1.4: Registrar detección
        print("\n[1.4] Registrando detección de prueba...")
        deteccion_id = db.registrar_deteccion(
            camara_id=camara_id,
            persona_id=persona_id,
            confianza=0.85,
            es_desconocido=False,
            imagen_captura="data/captures/capture_001.jpg"
        )
        print(f"✓ Detección registrada con ID: {deteccion_id}")

        # Test 1.5: Crear evento
        print("\n[1.5] Creando evento de prueba...")
        evento_id = db.crear_evento(
            tipo="persona_detectada",
            camara_id=camara_id,
            severidad="baja",
            descripcion="Persona conocida detectada",
            deteccion_id=deteccion_id
        )
        print(f"✓ Evento creado con ID: {evento_id}")

        # Test 1.6: Obtener detecciones recientes
        print("\n[1.6] Obteniendo detecciones recientes...")
        detecciones = db.obtener_detecciones_recientes(limit=10)
        print(f"✓ Detecciones encontradas: {len(detecciones)}")
        for d in detecciones[:3]:  # Mostrar solo las 3 primeras
            persona = f"{d['nombre']} {d['apellido']}" if d['nombre'] else "Desconocido"
            print(f"   - {d['timestamp']}: {persona} (confianza: {d['confianza']})")

        # Test 1.7: Obtener estadísticas
        print("\n[1.7] Obteniendo estadísticas del día...")
        stats = db.obtener_estadisticas_hoy()
        print("✓ Estadísticas:")
        print(f"   - Detecciones hoy: {stats['detecciones_hoy']}")
        print(f"   - Personas únicas: {stats['personas_unicas_hoy']}")
        print(f"   - Desconocidos: {stats['desconocidos_hoy']}")
        print(f"   - Eventos pendientes: {stats['eventos_pendientes']}")

        # Test 1.8: Configuración
        print("\n[1.8] Probando configuración...")
        db.actualizar_configuracion('test_key', 'test_value')
        valor = db.obtener_configuracion('test_key')
        print(f"✓ Configuración guardada y recuperada: {valor}")

        print("\n" + "=" * 70)
        print("✓ TODOS LOS TESTS DE BASE DE DATOS PASARON")
        print("=" * 70)

        db.close()
        return True

    except Exception as e:
        print(f"\n✗ ERROR EN TEST DE BASE DE DATOS: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# TEST 2: CAPTURA DE VIDEO
# =============================================================================

def test_video_capture_basic():
    """Prueba básica de captura de video"""
    print("\n" + "=" * 70)
    print("TEST 2: CAPTURA DE VIDEO")
    print("=" * 70 + "\n")

    print("Este test intentará capturar de tu webcam durante 5 segundos.")
    print("Se mostrará una ventana con el video. Presiona 'q' para salir antes.")
    input("\nPresiona ENTER para continuar...")

    try:
        print("\n[2.1] Inicializando captura de webcam...")
        cap = VideoCapture(source=0, frame_width=640, frame_height=480)

        if not cap.is_opened():
            print("✗ No se pudo abrir la webcam")
            return False

        print("✓ Webcam abierta correctamente")
        print(f"✓ Propiedades: {cap.get_properties()}")

        print("\n[2.2] Capturando frames...")
        start_time = time.time()
        frame_count = 0

        for frame in cap.read_frames():
            frame_count += 1

            # Agregar información al frame
            cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Test de Video", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Presiona 'q' para salir", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            cv2.imshow('Test de Captura', frame)

            # Salir con 'q' o después de 5 segundos
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n→ Salida manual por usuario")
                break

            if time.time() - start_time > 5:
                print("\n→ Tiempo de prueba completado")
                break

        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0

        print(f"\n✓ Captura exitosa:")
        print(f"   - Frames capturados: {frame_count}")
        print(f"   - Tiempo: {elapsed:.2f}s")
        print(f"   - FPS promedio: {fps:.2f}")

        cap.release()
        cv2.destroyAllWindows()

        print("\n" + "=" * 70)
        print("✓ TEST DE CAPTURA DE VIDEO PASÓ")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ ERROR EN TEST DE CAPTURA: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        return False


# =============================================================================
# TEST 3: INTEGRACIÓN BÁSICA
# =============================================================================

def test_integration():
    """Prueba integración básica: captura + almacenamiento en BD"""
    print("\n" + "=" * 70)
    print("TEST 3: INTEGRACIÓN BÁSICA")
    print("=" * 70 + "\n")

    try:
        # Inicializar componentes
        print("[3.1] Inicializando componentes...")
        db = DatabaseManager(Config.DB_PATH)

        # Verificar que hay al menos una cámara registrada
        camaras = db.obtener_camaras_activas()
        if not camaras:
            print("→ No hay cámaras registradas, agregando una...")
            camara_id = db.agregar_camara(
                nombre="Webcam Test",
                ubicacion="Sistema de prueba",
                tipo="webcam"
            )
        else:
            camara_id = camaras[0]['id']

        print(f"✓ Usando cámara ID: {camara_id}")

        # Capturar algunos frames y simular detecciones
        print("\n[3.2] Capturando frames y simulando detecciones...")
        cap = VideoCapture(source=0)

        frames_to_capture = 3
        captured = 0

        print(f"→ Capturando {frames_to_capture} frames...")

        for frame in cap.read_frames():
            if captured >= frames_to_capture:
                break

            captured += 1
            print(f"   Frame {captured}/{frames_to_capture} capturado")

            # Simular una detección (sin IA real todavía)
            # En la implementación real, aquí detectarías rostros
            deteccion_id = db.registrar_deteccion(
                camara_id=camara_id,
                persona_id=None,  # Desconocido por ahora
                confianza=None,
                es_desconocido=True,
                imagen_frame=f"test_frame_{captured}.jpg"
            )
            print(f"   ✓ Detección registrada (ID: {deteccion_id})")

        cap.release()

        # Verificar que se guardaron las detecciones
        print("\n[3.3] Verificando detecciones en BD...")
        detecciones = db.obtener_detecciones_recientes(limit=5)
        print(f"✓ Detecciones en BD: {len(detecciones)}")

        # Mostrar estadísticas
        print("\n[3.4] Estadísticas del sistema...")
        stats = db.obtener_estadisticas_hoy()
        print(f"✓ Detecciones totales hoy: {stats['detecciones_hoy']}")

        db.close()

        print("\n" + "=" * 70)
        print("✓ TEST DE INTEGRACIÓN PASÓ")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ ERROR EN TEST DE INTEGRACIÓN: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# TEST 4: ESTRUCTURA DE DIRECTORIOS
# =============================================================================

def test_directory_structure():
    """Verifica que todos los directorios necesarios existen"""
    print("\n" + "=" * 70)
    print("TEST 4: ESTRUCTURA DE DIRECTORIOS")
    print("=" * 70 + "\n")

    required_dirs = [
        Config.DATA_DIR,
        Config.KNOWN_FACES_DIR,
        Config.CAPTURES_DIR,
        Config.LOGS_DIR
    ]

    all_exist = True

    for directory in required_dirs:
        exists = directory.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {directory}")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n" + "=" * 70)
        print("✓ TODOS LOS DIRECTORIOS EXISTEN")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ ALGUNOS DIRECTORIOS NO EXISTEN")
        print("=" * 70)

    return all_exist


# =============================================================================
# MENÚ PRINCIPAL
# =============================================================================

def run_all_tests():
    """Ejecuta todos los tests en secuencia"""
    print("\n" + "=" * 70)
    print("EJECUTANDO BATERÍA COMPLETA DE TESTS")
    print("=" * 70)

    results = {
        "Estructura de directorios": test_directory_structure(),
        "Base de datos": test_database(),
        "Captura de video": test_video_capture_basic(),
        "Integración básica": test_integration()
    }

    print("\n\n" + "=" * 70)
    print("RESUMEN DE TESTS")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✓ PASÓ" if result else "✗ FALLÓ"
        print(f"{status:12} - {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ TODOS LOS TESTS PASARON")
        print("El sistema está listo para continuar con el desarrollo")
    else:
        print("✗ ALGUNOS TESTS FALLARON")
        print("Revisa los errores arriba antes de continuar")
    print("=" * 70 + "\n")

    return all_passed


def show_menu():
    """Muestra menú interactivo de tests"""
    while True:
        print("\n" + "=" * 70)
        print("MENÚ DE TESTS - Sistema de Videovigilancia IA")
        print("=" * 70)
        print("\n1. Probar estructura de directorios")
        print("2. Probar base de datos")
        print("3. Probar captura de video")
        print("4. Probar integración básica")
        print("5. Ejecutar TODOS los tests")
        print("6. Test específico de cámara IP (requiere URL)")
        print("0. Salir")
        print("\n" + "=" * 70)

        choice = input("\nSelecciona una opción: ").strip()

        if choice == "1":
            test_directory_structure()
        elif choice == "2":
            test_database()
        elif choice == "3":
            test_video_capture_basic()
        elif choice == "4":
            test_integration()
        elif choice == "5":
            run_all_tests()
        elif choice == "6":
            url = input("\nIngresa la URL de la cámara IP (RTSP/HTTP): ").strip()
            if url:
                print(f"\nProbando cámara: {url}")
                test_camera(source=url, duration=10)
        elif choice == "0":
            print("\n¡Hasta luego!")
            break
        else:
            print("\n✗ Opción inválida")

        input("\nPresiona ENTER para continuar...")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         SISTEMA DE VIDEOVIGILANCIA INTELIGENTE - TESTS              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    show_menu()