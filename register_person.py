# register_person.py
"""
Script interactivo para registrar nuevas personas en el sistema
Uso: python register_person.py
"""

import cv2
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from core.video_capture import VideoCapture
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from services.detection_service import DetectionService
from config import Config
import time
from datetime import datetime


class PersonRegistration:
    """
    Sistema interactivo para registrar nuevas personas
    """

    def __init__(self):
        print("\n" + "=" * 70)
        print("SISTEMA DE REGISTRO DE PERSONAS")
        print("=" * 70 + "\n")

        # Inicializar componentes
        print("Inicializando sistema...")
        self.db = DatabaseManager(Config.DB_PATH)
        self.detector = FaceDetector(model='hog')
        self.recognizer = FaceRecognizer(self.db, tolerance=0.6)

        # Verificar cámara
        camaras = self.db.obtener_camaras_activas()
        if not camaras:
            self.camera_id = self.db.agregar_camara(
                nombre="Cámara de Registro",
                ubicacion="Sistema de registro",
                tipo="webcam"
            )
        else:
            self.camera_id = camaras[0]['id']

        self.service = DetectionService(
            db_manager=self.db,
            face_detector=self.detector,
            face_recognizer=self.recognizer
        )

        print("✓ Sistema inicializado correctamente\n")

    def show_menu(self):
        """Muestra el menú principal"""
        print("\n" + "=" * 70)
        print("MENÚ DE REGISTRO")
        print("=" * 70)
        print("\n1. Registrar nueva persona")
        print("2. Ver personas registradas")
        print("3. Probar reconocimiento en vivo")
        print("4. Eliminar persona")
        print("0. Salir")
        print("\n" + "=" * 70)

    def register_new_person(self, camera_source=0):
        """
        Registra una nueva persona capturando su rostro desde la cámara
        """
        print("\n" + "=" * 70)
        print("REGISTRO DE NUEVA PERSONA")
        print("=" * 70 + "\n")

        # Solicitar información
        nombre = input("Nombre: ").strip()
        if not nombre:
            print("✗ El nombre es obligatorio")
            return False

        apellido = input("Apellido: ").strip()

        print("\nTipo de persona:")
        print("  1. Residente")
        print("  2. Empleado")
        print("  3. Visitante autorizado")
        tipo_opcion = input("Selecciona (1-3) [1]: ").strip() or "1"

        tipos = {
            "1": "residente",
            "2": "empleado",
            "3": "visitante_autorizado"
        }
        tipo = tipos.get(tipo_opcion, "residente")

        notas = input("Notas adicionales (opcional): ").strip() or None

        # Confirmar datos
        print("\n" + "-" * 70)
        print("Datos a registrar:")
        print(f"  Nombre: {nombre} {apellido}")
        print(f"  Tipo: {tipo}")
        if notas:
            print(f"  Notas: {notas}")
        print("-" * 70)

        confirmar = input("\n¿Confirmar? (s/n) [s]: ").strip().lower()
        if confirmar and confirmar != 's':
            print("✗ Registro cancelado")
            return False

        # Capturar rostro
        print("\n" + "=" * 70)
        print("CAPTURA DE ROSTRO")
        print("=" * 70)
        print("\nInstrucciones:")
        print("  1. Colócate frente a la cámara")
        print("  2. Asegúrate de que tu rostro esté bien iluminado")
        print("  3. Mira directamente a la cámara")
        print("  4. Presiona ESPACIO cuando veas tu rostro en el recuadro verde")
        print("  5. Presiona 'q' para cancelar")
        print("\n" + "=" * 70 + "\n")

        input("Presiona ENTER para abrir la cámara...")

        # Iniciar captura
        cap = VideoCapture(source=camera_source)
        captured_frame = None
        face_detected = False

        try:
            print("\n✓ Cámara iniciada. Buscando rostro...\n")

            for frame in cap.read_frames():
                # Detectar rostros
                face_locations = self.detector.detect_faces(frame, scale_factor=0.5)

                # Crear frame de visualización
                display_frame = frame.copy()

                if len(face_locations) == 1:
                    # UN rostro detectado - PERFECTO
                    face_detected = True
                    location = face_locations[0]

                    # Dibujar rectángulo VERDE
                    top, right, bottom, left = location
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)

                    # Instrucciones
                    cv2.putText(display_frame, "ROSTRO DETECTADO - Presiona ESPACIO",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Registrando: {nombre} {apellido}",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                elif len(face_locations) > 1:
                    # Varios rostros - ERROR
                    face_detected = False

                    # Dibujar todos en ROJO
                    for location in face_locations:
                        top, right, bottom, left = location
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 2)

                    cv2.putText(display_frame, f"ERROR: {len(face_locations)} rostros detectados",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(display_frame, "Solo debe haber UNA persona",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                else:
                    # Sin rostros
                    face_detected = False
                    cv2.putText(display_frame, "Buscando rostro...",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(display_frame, "Colócate frente a la cámara",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                # Mostrar frame
                cv2.imshow('Registro de Persona', display_frame)

                # Capturar teclas
                key = cv2.waitKey(1) & 0xFF

                if key == ord(' ') and face_detected:  # ESPACIO
                    captured_frame = frame.copy()
                    print("✓ Rostro capturado correctamente")
                    break
                elif key == ord('q'):  # SALIR
                    print("✗ Captura cancelada")
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        # Verificar si se capturó algo
        if captured_frame is None:
            print("\n✗ No se capturó ningún rostro")
            return False

        # Registrar en el sistema
        print("\nProcesando y guardando...")

        result = self.service.register_new_person_from_frame(
            frame=captured_frame,
            nombre=nombre,
            apellido=apellido,
            tipo=tipo
        )

        if result['success']:
            print("\n" + "=" * 70)
            print("✓ PERSONA REGISTRADA EXITOSAMENTE")
            print("=" * 70)
            print(f"  ID: {result['persona_id']}")
            print(f"  Nombre: {result['nombre']}")
            print(f"  Foto guardada en: {result['foto']}")
            print("=" * 70 + "\n")

            # Mostrar foto capturada
            foto = cv2.imread(result['foto'])
            if foto is not None:
                cv2.imshow('Foto Registrada', foto)
                print("Mostrando foto registrada... Presiona cualquier tecla para continuar")
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            return True
        else:
            print(f"\n✗ Error al registrar: {result['error']}")
            return False

    def list_registered_persons(self):
        """Lista todas las personas registradas"""
        print("\n" + "=" * 70)
        print("PERSONAS REGISTRADAS")
        print("=" * 70 + "\n")

        personas = self.db.obtener_personas_activas()

        if not personas:
            print("No hay personas registradas en el sistema\n")
            return

        print(f"Total: {len(personas)} persona(s)\n")
        print(f"{'ID':<5} {'Nombre':<30} {'Tipo':<20} {'Fecha Registro'}")
        print("-" * 70)

        for persona in personas:
            nombre_completo = f"{persona['nombre']} {persona['apellido'] or ''}".strip()
            # Obtener info adicional de la BD
            p_info = self.db.obtener_persona(persona['id'])
            fecha = p_info.get('fecha_registro', 'N/A') if p_info else 'N/A'

            print(f"{persona['id']:<5} {nombre_completo:<30} {persona['tipo']:<20} {fecha}")

        print("\n")

    def test_recognition_live(self, camera_source=0, duration=30):
        """Prueba el reconocimiento en vivo"""
        print("\n" + "=" * 70)
        print("PRUEBA DE RECONOCIMIENTO EN VIVO")
        print("=" * 70)
        print(f"\nDuración: {duration} segundos")
        print("Presiona 'q' para salir antes\n")

        input("Presiona ENTER para iniciar...")

        cap = VideoCapture(source=camera_source)
        start_time = time.time()

        try:
            for frame in cap.read_frames():
                # Procesar y mostrar
                display_frame, results = self.service.process_and_display(
                    frame, self.camera_id, show_info=True
                )

                # Mostrar
                cv2.imshow('Prueba de Reconocimiento', display_frame)

                # Controles
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break

                if time.time() - start_time > duration:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

            # Estadísticas
            stats = self.service.get_session_stats()
            print("\n" + "=" * 70)
            print("ESTADÍSTICAS DE LA PRUEBA:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print("=" * 70 + "\n")

    def delete_person(self):
        """Elimina una persona del sistema"""
        print("\n" + "=" * 70)
        print("ELIMINAR PERSONA")
        print("=" * 70 + "\n")

        # Mostrar personas
        self.list_registered_persons()

        try:
            persona_id = int(input("ID de la persona a eliminar (0 para cancelar): "))

            if persona_id == 0:
                print("✗ Operación cancelada")
                return

            # Verificar que existe
            persona = self.db.obtener_persona(persona_id)
            if not persona:
                print(f"✗ No se encontró persona con ID {persona_id}")
                return

            nombre = f"{persona['nombre']} {persona['apellido'] or ''}".strip()

            # Confirmar
            print(f"\n¿Estás seguro de eliminar a {nombre}?")
            confirmar = input("Escribe 'ELIMINAR' para confirmar: ").strip()

            if confirmar != 'ELIMINAR':
                print("✗ Eliminación cancelada")
                return

            # Eliminar (soft delete)
            self.db.eliminar_persona(persona_id, soft_delete=True)
            self.recognizer.reload_known_faces()

            print(f"\n✓ {nombre} ha sido eliminado del sistema")

        except ValueError:
            print("✗ ID inválido")
        except Exception as e:
            print(f"✗ Error: {e}")

    def run(self):
        """Ejecuta el menú interactivo"""
        while True:
            self.show_menu()

            opcion = input("\nSelecciona una opción: ").strip()

            if opcion == '1':
                self.register_new_person()
            elif opcion == '2':
                self.list_registered_persons()
            elif opcion == '3':
                self.test_recognition_live()
            elif opcion == '4':
                self.delete_person()
            elif opcion == '0':
                print("\n¡Hasta luego!")
                break
            else:
                print("\n✗ Opción inválida")

            input("\nPresiona ENTER para continuar...")

    def cleanup(self):
        """Limpia recursos"""
        if hasattr(self, 'db'):
            self.db.close()


# =============================================================================
# MODO RÁPIDO: Registro desde línea de comandos
# =============================================================================

def quick_register(nombre: str, apellido: str = "", tipo: str = "residente"):
    """
    Modo rápido para registrar desde línea de comandos

    Uso:
        python register_person.py --quick "Juan" "Pérez"
    """
    print("\n" + "=" * 70)
    print(f"REGISTRO RÁPIDO: {nombre} {apellido}")
    print("=" * 70 + "\n")

    registration = PersonRegistration()

    try:
        # Captura directa
        cap = VideoCapture(source=0)
        captured = False

        print("✓ Cámara iniciada")
        print("→ Buscando rostro...\n")
        print("Instrucciones:")
        print("  - Presiona ESPACIO cuando tu rostro esté en el recuadro verde")
        print("  - Presiona 'q' para cancelar\n")

        for frame in cap.read_frames():
            face_locations = registration.detector.detect_faces(frame, scale_factor=0.5)

            display_frame = frame.copy()

            if len(face_locations) == 1:
                location = face_locations[0]
                top, right, bottom, left = location
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                cv2.putText(display_frame, "Presiona ESPACIO para capturar",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('Registro Rápido', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' ') and len(face_locations) == 1:
                result = registration.service.register_new_person_from_frame(
                    frame=frame,
                    nombre=nombre,
                    apellido=apellido,
                    tipo=tipo
                )

                if result['success']:
                    print(f"\n✓ {nombre} {apellido} registrado exitosamente!")
                    captured = True
                break
            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        return captured

    finally:
        registration.cleanup()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sistema de Registro de Personas')
    parser.add_argument('--quick', action='store_true', help='Modo rápido de registro')
    parser.add_argument('nombre', nargs='?', help='Nombre de la persona')
    parser.add_argument('apellido', nargs='?', default='', help='Apellido de la persona')
    parser.add_argument('--tipo', default='residente', choices=['residente', 'empleado', 'visitante_autorizado'],
                        help='Tipo de persona')

    args = parser.parse_args()

    try:
        if args.quick and args.nombre:
            # Modo rápido desde línea de comandos
            quick_register(args.nombre, args.apellido, args.tipo)
        else:
            # Modo interactivo con menú
            registration = PersonRegistration()
            registration.run()
            registration.cleanup()

    except KeyboardInterrupt:
        print("\n\n✗ Interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        import traceback

        traceback.print_exc()