# demo_completo.py
"""
Demo completo del Sistema de Videovigilancia Inteligente
Este script te guía paso a paso para probar todas las funcionalidades
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
from config import Config


class DemoCompleto:
    """Demo interactivo del sistema completo"""

    def __init__(self):
        self.db = None
        self.detector = None
        self.recognizer = None
        self.service = None
        self.camera_id = None

    def print_header(self, texto):
        """Imprime un encabezado bonito"""
        print("\n" + "=" * 70)
        print(f"  {texto}")
        print("=" * 70 + "\n")

    def print_step(self, numero, texto):
        """Imprime un paso del demo"""
        print(f"\n{'─' * 70}")
        print(f"📍 PASO {numero}: {texto}")
        print(f"{'─' * 70}\n")

    def wait_for_user(self, mensaje="Presiona ENTER para continuar..."):
        """Espera que el usuario presione ENTER"""
        input(f"\n{mensaje}")

    def paso_1_verificar_instalacion(self):
        """Verifica que todo esté instalado correctamente"""
        self.print_step(1, "VERIFICAR INSTALACIÓN")

        print("Verificando dependencias...")

        try:
            import cv2
            print(f"✓ OpenCV: {cv2.__version__}")
        except ImportError:
            print("✗ OpenCV no instalado")
            return False

        try:
            import face_recognition
            print(f"✓ face_recognition: {face_recognition.__version__}")
        except ImportError:
            print("✗ face_recognition no instalado")
            return False

        try:
            import numpy as np
            print(f"✓ NumPy: {np.__version__}")
        except ImportError:
            print("✗ NumPy no instalado")
            return False

        # Verificar estructura de directorios
        print("\nVerificando estructura de directorios...")
        dirs_ok = True
        for directory in [Config.DATA_DIR, Config.KNOWN_FACES_DIR,
                          Config.CAPTURES_DIR, Config.LOGS_DIR]:
            if directory.exists():
                print(f"✓ {directory}")
            else:
                print(f"✗ {directory} no existe")
                dirs_ok = False

        if dirs_ok:
            print("\n✓ Todas las dependencias están instaladas correctamente")
            return True
        else:
            print("\n✗ Faltan algunos directorios")
            return False

    def paso_2_inicializar_sistema(self):
        """Inicializa todos los componentes del sistema"""
        self.print_step(2, "INICIALIZAR SISTEMA")

        try:
            print("Inicializando base de datos...")
            self.db = DatabaseManager(Config.DB_PATH)
            print("✓ Base de datos inicializada")

            print("\nVerificando/Creando cámara...")
            camaras = self.db.obtener_camaras_activas()
            if not camaras:
                self.camera_id = self.db.agregar_camara(
                    nombre="Cámara Demo",
                    ubicacion="Sistema de prueba",
                    tipo="webcam"
                )
                print(f"✓ Cámara creada con ID: {self.camera_id}")
            else:
                self.camera_id = camaras[0]['id']
                print(f"✓ Usando cámara existente ID: {self.camera_id}")

            print("\nInicializando detector de rostros...")
            self.detector = FaceDetector(model='hog')
            print("✓ Detector inicializado")

            print("\nInicializando reconocedor facial...")
            self.recognizer = FaceRecognizer(self.db, tolerance=0.6)
            print(f"✓ Reconocedor inicializado ({len(self.recognizer.known_names)} personas registradas)")

            print("\nInicializando servicio de detección...")
            self.service = DetectionService(
                db_manager=self.db,
                face_detector=self.detector,
                face_recognizer=self.recognizer,
                save_captures=True,
                alert_on_unknown=True
            )
            print("✓ Servicio de detección inicializado")

            print("\n" + "=" * 70)
            print("✓ SISTEMA COMPLETAMENTE INICIALIZADO")
            print("=" * 70)

            return True

        except Exception as e:
            print(f"\n✗ Error al inicializar: {e}")
            import traceback
            traceback.print_exc()
            return False

    def paso_3_test_camara(self):
        """Prueba la cámara y detección básica"""
        self.print_step(3, "PROBAR CÁMARA Y DETECCIÓN")

        print("Este test abrirá tu cámara y detectará rostros durante 10 segundos.")
        print("\nControles:")
        print("  - Presiona 'q' para salir antes")
        print("  - Muévete frente a la cámara para probar la detección")

        self.wait_for_user()

        cap = VideoCapture(source=0)
        start_time = time.time()
        detecciones_totales = 0

        try:
            print("\n✓ Cámara iniciada")
            print("→ Detectando rostros...\n")

            for frame in cap.read_frames():
                # Detectar rostros
                face_locations = self.detector.detect_faces(frame, scale_factor=0.5)
                detecciones_totales += len(face_locations)

                # Dibujar resultados
                display_frame = self.detector.draw_faces(
                    frame,
                    face_locations,
                    labels=[f"Rostro {i + 1}" for i in range(len(face_locations))]
                )

                # Info en pantalla
                elapsed = int(time.time() - start_time)
                remaining = 10 - elapsed

                cv2.putText(display_frame, f"Rostros detectados: {len(face_locations)}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Tiempo restante: {remaining}s",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(display_frame, "Presiona 'q' para salir",
                            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow('Test de Cámara', display_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                if time.time() - start_time > 10:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        print(f"\n✓ Test completado")
        print(f"  - Detecciones totales: {detecciones_totales}")
        print(f"  - Tiempo: {int(time.time() - start_time)}s")

        if detecciones_totales > 0:
            print("\n✓ La detección de rostros funciona correctamente")
            return True
        else:
            print("\n⚠ No se detectaron rostros. Asegúrate de estar frente a la cámara.")
            return False

    def paso_4_registrar_persona(self):
        """Registra una persona de prueba"""
        self.print_step(4, "REGISTRAR PERSONA DE PRUEBA")

        personas_actuales = len(self.recognizer.known_names)

        if personas_actuales > 0:
            print(f"Ya tienes {personas_actuales} persona(s) registrada(s):")
            for nombre in self.recognizer.known_names:
                print(f"  - {nombre}")

            print("\n¿Deseas registrar otra persona?")
            respuesta = input("(s/n) [n]: ").strip().lower()

            if respuesta != 's':
                print("→ Saltando registro")
                return True

        print("\nVamos a registrar una nueva persona.")
        print("Necesitarás:")
        print("  1. Estar frente a la cámara")
        print("  2. Buena iluminación")
        print("  3. Mirar directamente a la cámara")

        self.wait_for_user()

        # Solicitar datos
        print("\nDatos de la persona:")
        nombre = input("Nombre: ").strip()
        if not nombre:
            print("✗ Nombre obligatorio")
            return False

        apellido = input("Apellido (opcional): ").strip()

        print("\nTipo:")
        print("  1. Residente")
        print("  2. Empleado")
        print("  3. Visitante autorizado")
        tipo_opt = input("Selecciona [1]: ").strip() or "1"

        tipos = {"1": "residente", "2": "empleado", "3": "visitante_autorizado"}
        tipo = tipos.get(tipo_opt, "residente")

        print(f"\n→ Registrando: {nombre} {apellido} ({tipo})")

        self.wait_for_user("Presiona ENTER para abrir la cámara...")

        # Capturar
        cap = VideoCapture(source=0)
        captured = False

        try:
            print("\n✓ Cámara iniciada")
            print("→ Colócate frente a la cámara y presiona ESPACIO cuando veas el recuadro verde\n")

            for frame in cap.read_frames():
                face_locations = self.detector.detect_faces(frame, scale_factor=0.5)

                display_frame = frame.copy()

                if len(face_locations) == 1:
                    # Perfecto - un rostro
                    location = face_locations[0]
                    top, right, bottom, left = location

                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                    cv2.putText(display_frame, "LISTO - Presiona ESPACIO para capturar",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"{nombre} {apellido}",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                elif len(face_locations) > 1:
                    # Error - varios rostros
                    for location in face_locations:
                        top, right, bottom, left = location
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 2)

                    cv2.putText(display_frame, f"ERROR: {len(face_locations)} rostros",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(display_frame, "Solo debe haber UNA persona",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    # Sin rostros
                    cv2.putText(display_frame, "Buscando rostro...",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                cv2.imshow('Registro de Persona', display_frame)

                key = cv2.waitKey(1) & 0xFF

                if key == ord(' ') and len(face_locations) == 1:
                    # Capturar y registrar
                    result = self.service.register_new_person_from_frame(
                        frame=frame,
                        nombre=nombre,
                        apellido=apellido,
                        tipo=tipo
                    )

                    if result['success']:
                        print(f"\n✓ {nombre} {apellido} registrado con ID: {result['persona_id']}")
                        captured = True
                    else:
                        print(f"\n✗ Error: {result['error']}")

                    break

                elif key == ord('q'):
                    print("\n✗ Registro cancelado")
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        return captured

    def paso_5_test_reconocimiento(self):
        """Prueba el reconocimiento con las personas registradas"""
        self.print_step(5, "PROBAR RECONOCIMIENTO FACIAL")

        if len(self.recognizer.known_names) == 0:
            print("⚠ No hay personas registradas para reconocer")
            print("Debes completar el Paso 4 primero")
            return False

        print(f"Personas registradas en el sistema: {len(self.recognizer.known_names)}")
        for nombre in self.recognizer.known_names:
            print(f"  - {nombre}")

        print("\nEste test mostrará en tiempo real:")
        print("  🟢 Verde: Personas CONOCIDAS (con nombre y confianza)")
        print("  🔴 Rojo: Personas DESCONOCIDAS (alerta)")
        print("  ⚪ Gris: Personas vistas recientemente (cooldown)")

        print("\nDuración: 30 segundos")
        print("Puedes probar con diferentes personas frente a la cámara")

        self.wait_for_user()

        cap = VideoCapture(source=0)
        start_time = time.time()

        reconocimientos = {
            'conocidos': 0,
            'desconocidos': 0,
            'total_frames': 0
        }

        try:
            print("\n✓ Sistema de reconocimiento activo\n")

            for frame in cap.read_frames():
                reconocimientos['total_frames'] += 1

                # Procesar con el servicio completo
                display_frame, results = self.service.process_and_display(
                    frame,
                    self.camera_id,
                    show_info=True
                )

                # Contar reconocimientos
                for rec in results.get('recognitions', []):
                    if not rec.get('cached', False):  # No contar cacheados
                        if rec.get('es_desconocido', False):
                            reconocimientos['desconocidos'] += 1
                        else:
                            reconocimientos['conocidos'] += 1

                # Tiempo restante
                elapsed = int(time.time() - start_time)
                remaining = 30 - elapsed

                cv2.putText(display_frame, f"Tiempo: {remaining}s",
                            (10, display_frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                cv2.imshow('Test de Reconocimiento', display_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                if time.time() - start_time > 30:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        # Resultados
        print("\n" + "=" * 70)
        print("RESULTADOS DEL TEST:")
        print("=" * 70)
        print(f"  Frames procesados: {reconocimientos['total_frames']}")
        print(f"  Personas conocidas detectadas: {reconocimientos['conocidos']}")
        print(f"  Personas desconocidas detectadas: {reconocimientos['desconocidos']}")

        # Estadísticas del servicio
        stats = self.service.get_session_stats()
        print(f"\nEstadísticas de sesión:")
        print(f"  Total rostros detectados: {stats['faces_detected']}")
        print(f"  Eventos creados: {stats['events_created']}")
        print("=" * 70)

        return True

    def paso_6_verificar_base_datos(self):
        """Verifica que todo se guardó en la base de datos"""
        self.print_step(6, "VERIFICAR BASE DE DATOS")

        print("Verificando datos almacenados...\n")

        # Personas
        personas = self.db.obtener_personas_activas()
        print(f"✓ Personas registradas: {len(personas)}")
        for p in personas:
            print(f"   - {p['nombre']} {p['apellido'] or ''} ({p['tipo']})")

        # Detecciones
        detecciones = self.db.obtener_detecciones_recientes(limit=10)
        print(f"\n✓ Detecciones recientes: {len(detecciones)}")
        for d in detecciones[:5]:
            nombre = d['nombre'] if d['nombre'] else "Desconocido"
            print(f"   - {d['timestamp']}: {nombre}")

        # Eventos
        eventos = self.db.obtener_eventos_no_resueltos()
        print(f"\n✓ Eventos pendientes: {len(eventos)}")
        if eventos:
            for e in eventos[:3]:
                print(f"   - [{e['severidad']}] {e['tipo']}: {e['descripcion']}")

        # Estadísticas
        stats = self.db.obtener_estadisticas_hoy()
        print(f"\n✓ Estadísticas de hoy:")
        print(f"   - Detecciones: {stats['detecciones_hoy']}")
        print(f"   - Personas únicas: {stats['personas_unicas_hoy']}")
        print(f"   - Desconocidos: {stats['desconocidos_hoy']}")

        return True

    def ejecutar_demo(self):
        """Ejecuta el demo completo paso a paso"""
        self.print_header("DEMO COMPLETO - SISTEMA DE VIDEOVIGILANCIA INTELIGENTE")

        print("Este demo te guiará paso a paso para probar todo el sistema.")
        print("\nPasos del demo:")
        print("  1. Verificar instalación")
        print("  2. Inicializar sistema")
        print("  3. Probar cámara y detección")
        print("  4. Registrar persona de prueba")
        print("  5. Probar reconocimiento facial")
        print("  6. Verificar base de datos")

        self.wait_for_user("\nPresiona ENTER para comenzar...")

        # Ejecutar pasos
        pasos = [
            self.paso_1_verificar_instalacion,
            self.paso_2_inicializar_sistema,
            self.paso_3_test_camara,
            self.paso_4_registrar_persona,
            self.paso_5_test_reconocimiento,
            self.paso_6_verificar_base_datos
        ]

        for paso_func in pasos:
            if not paso_func():
                print("\n⚠ Hubo un problema en este paso.")
                continuar = input("¿Continuar de todos modos? (s/n) [n]: ").strip().lower()
                if continuar != 's':
                    print("\n✗ Demo interrumpido")
                    return False

        # Final
        self.print_header("✓ DEMO COMPLETADO EXITOSAMENTE")

        print("¡Felicidades! El sistema está funcionando correctamente.")
        print("\nPróximos pasos sugeridos:")
        print("  1. Registra más personas con: python register_person.py")
        print("  2. Ejecuta el sistema completo con: python services/detection_service.py")
        print("  3. Revisa las capturas en: data/captures/")
        print("  4. Revisa los logs en: data/logs/")

        print("\n" + "=" * 70)

        return True


if __name__ == '__main__':
    try:
        demo = DemoCompleto()
        demo.ejecutar_demo()
    except KeyboardInterrupt:
        print("\n\n✗ Demo interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if demo.db:
            demo.db.close()
        cv2.destroyAllWindows()