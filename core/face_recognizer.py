# core/face_recognizer.py

import face_recognition
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pickle


class FaceRecognizer:
    """
    Reconocedor facial que compara rostros detectados con personas conocidas
    Gestiona encodings y determina identidades
    """

    def __init__(self, db_manager, tolerance: float = 0.6):
        """
        Args:
            db_manager: Instancia de DatabaseManager
            tolerance: Umbral de similitud (menor = más estricto)
                      0.6 es el valor por defecto recomendado
                      0.5 = muy estricto
                      0.7 = más permisivo
        """
        self.db_manager = db_manager
        self.tolerance = tolerance

        # Cache de personas conocidas
        self.known_encodings = []
        self.known_ids = []
        self.known_names = []
        self.known_types = []

        # Cargar personas conocidas
        self.load_known_faces()

        print(f"✓ FaceRecognizer inicializado")
        print(f"  - Personas conocidas: {len(self.known_encodings)}")
        print(f"  - Tolerancia: {tolerance}")

    def load_known_faces(self):
        """Carga todas las personas conocidas desde la base de datos"""
        personas = self.db_manager.obtener_personas_activas()

        self.known_encodings = []
        self.known_ids = []
        self.known_names = []
        self.known_types = []

        for persona in personas:
            self.known_encodings.append(persona['encoding'])
            self.known_ids.append(persona['id'])
            nombre_completo = f"{persona['nombre']} {persona['apellido'] or ''}".strip()
            self.known_names.append(nombre_completo)
            self.known_types.append(persona['tipo'])

        print(f"✓ Cargadas {len(self.known_encodings)} personas conocidas")

    def reload_known_faces(self):
        """Recarga las personas conocidas (útil después de agregar nuevas)"""
        print("→ Recargando personas conocidas...")
        self.load_known_faces()

    def recognize_face(self, face_encoding: np.ndarray) -> Dict:
        """
        Reconoce un rostro comparándolo con los conocidos

        Args:
            face_encoding: Encoding del rostro a reconocer

        Returns:
            Diccionario con:
            - persona_id: ID de la persona (None si es desconocido)
            - nombre: Nombre de la persona (o "Desconocido")
            - tipo: Tipo de persona (residente, empleado, etc.)
            - confianza: Nivel de confianza (0-1)
            - distancia: Distancia facial (menor = más similar)
            - es_desconocido: Boolean
        """
        if not self.known_encodings:
            return self._create_unknown_result()

        # Comparar con todos los rostros conocidos
        distances = face_recognition.face_distance(self.known_encodings, face_encoding)
        matches = face_recognition.compare_faces(
            self.known_encodings,
            face_encoding,
            tolerance=self.tolerance
        )

        # Encontrar la mejor coincidencia
        best_match_index = None
        if True in matches:
            # De todas las coincidencias, obtener la más cercana
            matched_distances = [d for d, m in zip(distances, matches) if m]
            best_distance = min(matched_distances)
            best_match_index = list(distances).index(best_distance)

        # Si hay coincidencia
        if best_match_index is not None:
            persona_id = self.known_ids[best_match_index]
            nombre = self.known_names[best_match_index]
            tipo = self.known_types[best_match_index]
            distancia = distances[best_match_index]
            confianza = 1.0 - distancia  # Convertir distancia a confianza

            return {
                'persona_id': persona_id,
                'nombre': nombre,
                'tipo': tipo,
                'confianza': float(confianza),
                'distancia': float(distancia),
                'es_desconocido': False
            }
        else:
            return self._create_unknown_result()

    def _create_unknown_result(self) -> Dict:
        """Crea resultado para persona desconocida"""
        return {
            'persona_id': None,
            'nombre': 'Desconocido',
            'tipo': 'desconocido',
            'confianza': 0.0,
            'distancia': 1.0,
            'es_desconocido': True
        }

    def recognize_multiple_faces(self, face_encodings: List[np.ndarray]) -> List[Dict]:
        """
        Reconoce múltiples rostros de una vez

        Args:
            face_encodings: Lista de encodings faciales

        Returns:
            Lista de resultados de reconocimiento
        """
        results = []
        for encoding in face_encodings:
            result = self.recognize_face(encoding)
            results.append(result)

        return results

    def add_new_person(self, nombre: str, apellido: str, face_encoding: np.ndarray,
                       tipo: str = 'residente', foto_referencia: str = None,
                       notas: str = None) -> int:
        """
        Agrega una nueva persona al sistema

        Returns:
            ID de la persona agregada
        """
        persona_id = self.db_manager.agregar_persona(
            nombre=nombre,
            apellido=apellido,
            encoding=face_encoding,
            tipo=tipo,
            foto_referencia=foto_referencia,
            notas=notas
        )

        # Recargar personas conocidas
        self.reload_known_faces()

        print(f"✓ Persona agregada: {nombre} {apellido} (ID: {persona_id})")

        return persona_id

    def find_similar_faces(self, face_encoding: np.ndarray,
                           top_k: int = 5) -> List[Dict]:
        """
        Encuentra las K personas más similares al rostro dado
        Útil para sugerencias o verificación manual

        Args:
            face_encoding: Encoding del rostro
            top_k: Número de resultados a devolver

        Returns:
            Lista ordenada de personas similares con sus distancias
        """
        if not self.known_encodings:
            return []

        # Calcular distancias
        distances = face_recognition.face_distance(self.known_encodings, face_encoding)

        # Ordenar por distancia (menor = más similar)
        sorted_indices = np.argsort(distances)[:top_k]

        results = []
        for idx in sorted_indices:
            results.append({
                'persona_id': self.known_ids[idx],
                'nombre': self.known_names[idx],
                'tipo': self.known_types[idx],
                'distancia': float(distances[idx]),
                'confianza': float(1.0 - distances[idx])
            })

        return results

    def verify_face(self, face_encoding: np.ndarray, persona_id: int,
                    strict: bool = False) -> Dict:
        """
        Verifica si un rostro pertenece a una persona específica

        Args:
            face_encoding: Encoding del rostro
            persona_id: ID de la persona a verificar
            strict: Usar umbral más estricto (tolerance * 0.8)

        Returns:
            Diccionario con resultado de verificación
        """
        # Buscar encoding de la persona
        if persona_id not in self.known_ids:
            return {
                'verificado': False,
                'persona_id': persona_id,
                'error': 'Persona no encontrada'
            }

        idx = self.known_ids.index(persona_id)
        known_encoding = self.known_encodings[idx]

        # Calcular distancia
        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]

        # Determinar umbral
        threshold = self.tolerance * 0.8 if strict else self.tolerance

        # Verificar
        is_match = distance <= threshold

        return {
            'verificado': is_match,
            'persona_id': persona_id,
            'nombre': self.known_names[idx],
            'distancia': float(distance),
            'confianza': float(1.0 - distance),
            'umbral_usado': threshold
        }

    def get_recognition_summary(self) -> Dict:
        """Obtiene resumen del estado del reconocedor"""
        return {
            'personas_conocidas': len(self.known_encodings),
            'tolerance': self.tolerance,
            'nombres': self.known_names,
            'tipos': dict(zip(self.known_names, self.known_types))
        }

    def update_tolerance(self, new_tolerance: float):
        """Actualiza el umbral de tolerancia"""
        self.tolerance = new_tolerance
        print(f"✓ Tolerancia actualizada a: {new_tolerance}")

    def export_encodings(self, filepath: str):
        """Exporta encodings a un archivo pickle (backup)"""
        data = {
            'encodings': self.known_encodings,
            'ids': self.known_ids,
            'names': self.known_names,
            'types': self.known_types,
            'tolerance': self.tolerance,
            'export_date': datetime.now().isoformat()
        }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        print(f"✓ Encodings exportados a: {filepath}")

    def import_encodings(self, filepath: str):
        """Importa encodings desde un archivo pickle"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        self.known_encodings = data['encodings']
        self.known_ids = data['ids']
        self.known_names = data['names']
        self.known_types = data['types']

        print(f"✓ Encodings importados desde: {filepath}")
        print(f"  - Personas cargadas: {len(self.known_encodings)}")


class RecognitionCache:
    """
    Cache para evitar reconocer la misma persona continuamente
    Reduce carga computacional y evita spam de detecciones
    """

    def __init__(self, cooldown_seconds: int = 30):
        """
        Args:
            cooldown_seconds: Tiempo mínimo entre detecciones de la misma persona
        """
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.cache = {}  # {persona_id: ultimo_timestamp}

    def should_process(self, persona_id: int) -> bool:
        """
        Verifica si se debe procesar una detección

        Args:
            persona_id: ID de la persona detectada

        Returns:
            True si ha pasado suficiente tiempo desde última detección
        """
        if persona_id is None:  # Siempre procesar desconocidos
            return True

        now = datetime.now()

        if persona_id not in self.cache:
            self.cache[persona_id] = now
            return True

        last_seen = self.cache[persona_id]
        time_elapsed = now - last_seen

        if time_elapsed >= self.cooldown:
            self.cache[persona_id] = now
            return True

        return False

    def mark_seen(self, persona_id: int):
        """Marca una persona como vista ahora"""
        if persona_id is not None:
            self.cache[persona_id] = datetime.now()

    def clear_cache(self):
        """Limpia todo el cache"""
        self.cache.clear()

    def get_time_until_next(self, persona_id: int) -> Optional[float]:
        """Obtiene segundos restantes hasta que se pueda procesar de nuevo"""
        if persona_id not in self.cache:
            return 0.0

        last_seen = self.cache[persona_id]
        elapsed = datetime.now() - last_seen
        remaining = self.cooldown - elapsed

        if remaining.total_seconds() > 0:
            return remaining.total_seconds()

        return 0.0


# =============================================================================
# UTILIDADES Y TESTS
# =============================================================================

def test_recognizer():
    """Test básico del reconocedor"""
    print("\n" + "=" * 70)
    print("TEST: FaceRecognizer")
    print("=" * 70 + "\n")

    # Importar dependencias
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from database.db_manager import DatabaseManager
    from config import Config

    # Inicializar
    db = DatabaseManager(Config.DB_PATH)
    recognizer = FaceRecognizer(db, tolerance=0.6)

    # Mostrar resumen
    summary = recognizer.get_recognition_summary()
    print("Resumen del sistema:")
    print(f"  - Personas conocidas: {summary['personas_conocidas']}")
    print(f"  - Tolerancia: {summary['tolerance']}")

    if summary['nombres']:
        print(f"\nPersonas registradas:")
        for nombre, tipo in summary['tipos'].items():
            print(f"  - {nombre} ({tipo})")
    else:
        print("\n⚠ No hay personas registradas aún")
        print("  Usa add_new_person() para agregar personas al sistema")

    db.close()
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_recognizer()