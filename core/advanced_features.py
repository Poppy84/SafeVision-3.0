# core/advanced_features.py
"""
Features avanzados de IA para el sistema de videovigilancia
- Detección de comportamientos sospechosos
- Análisis de patrones temporales
- Contador de personas
- Zonas restringidas
- Alertas inteligentes
"""

import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import deque, defaultdict
import json


class PeopleCounter:
    """
    Contador inteligente de personas en el área de vigilancia
    Útil para: aforo, estadísticas, control de acceso
    """

    def __init__(self, max_history: int = 30):
        """
        Args:
            max_history: Frames de historia para tracking
        """
        self.max_history = max_history
        self.person_tracks = {}  # {track_id: [positions]}
        self.next_track_id = 0
        self.current_count = 0
        self.total_entries = 0
        self.total_exits = 0

        # Línea virtual para contar entradas/salidas
        self.counting_line_y = None

    def set_counting_line(self, frame_height: int, position: float = 0.5):
        """
        Define una línea virtual para contar entradas/salidas

        Args:
            frame_height: Alto del frame
            position: Posición relativa (0.5 = centro)
        """
        self.counting_line_y = int(frame_height * position)

    def update(self, face_locations: List[Tuple], frame_shape: Tuple) -> Dict:
        """
        Actualiza el contador con nuevas detecciones

        Returns:
            Diccionario con estadísticas actualizadas
        """
        frame_height, frame_width = frame_shape[:2]

        if self.counting_line_y is None:
            self.set_counting_line(frame_height)

        # Centros de rostros detectados
        current_centers = []
        for top, right, bottom, left in face_locations:
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            current_centers.append((center_x, center_y))

        # Actualizar conteo actual
        self.current_count = len(current_centers)

        # Tracking simple (por proximidad)
        matched_tracks = set()

        for center in current_centers:
            # Buscar track más cercano
            best_track = None
            min_distance = float('inf')

            for track_id, positions in self.person_tracks.items():
                if track_id in matched_tracks:
                    continue

                if positions:
                    last_pos = positions[-1]
                    distance = np.sqrt((center[0] - last_pos[0]) ** 2 +
                                       (center[1] - last_pos[1]) ** 2)

                    if distance < min_distance and distance < 100:  # Umbral de proximidad
                        min_distance = distance
                        best_track = track_id

            if best_track is not None:
                # Actualizar track existente
                self.person_tracks[best_track].append(center)
                matched_tracks.add(best_track)

                # Detectar cruce de línea
                if len(self.person_tracks[best_track]) >= 2:
                    prev_y = self.person_tracks[best_track][-2][1]
                    curr_y = center[1]

                    # De arriba hacia abajo (entrada)
                    if prev_y < self.counting_line_y <= curr_y:
                        self.total_entries += 1
                    # De abajo hacia arriba (salida)
                    elif prev_y > self.counting_line_y >= curr_y:
                        self.total_exits += 1

                # Limitar historia
                if len(self.person_tracks[best_track]) > self.max_history:
                    self.person_tracks[best_track].pop(0)
            else:
                # Crear nuevo track
                self.person_tracks[self.next_track_id] = [center]
                self.next_track_id += 1

        # Limpiar tracks viejos
        tracks_to_remove = []
        for track_id in self.person_tracks:
            if track_id not in matched_tracks:
                tracks_to_remove.append(track_id)

        for track_id in tracks_to_remove:
            del self.person_tracks[track_id]

        return {
            'current_count': self.current_count,
            'total_entries': self.total_entries,
            'total_exits': self.total_exits,
            'active_tracks': len(self.person_tracks)
        }

    def draw_counting_line(self, frame: np.ndarray) -> np.ndarray:
        """Dibuja la línea de conteo en el frame"""
        if self.counting_line_y is not None:
            cv2.line(frame, (0, self.counting_line_y),
                     (frame.shape[1], self.counting_line_y),
                     (0, 255, 255), 2)

            cv2.putText(frame, "Linea de conteo", (10, self.counting_line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        return frame


class RestrictedZone:
    """
    Define zonas restringidas en el área de vigilancia
    Genera alertas cuando personas no autorizadas ingresan
    """

    def __init__(self, zones: List[Dict] = None):
        """
        Args:
            zones: Lista de zonas, cada una con:
                - name: Nombre de la zona
                - polygon: Lista de puntos [(x,y), ...]
                - authorized_types: Tipos de personas autorizadas
        """
        self.zones = zones or []
        self.violations = []

    def add_zone(self, name: str, polygon: List[Tuple],
                 authorized_types: List[str] = None):
        """Agrega una nueva zona restringida"""
        self.zones.append({
            'name': name,
            'polygon': np.array(polygon, dtype=np.int32),
            'authorized_types': authorized_types or []
        })

    def check_violations(self, detections: List[Dict]) -> List[Dict]:
        """
        Verifica si hay violaciones de zona

        Args:
            detections: Lista de detecciones con location, nombre, tipo

        Returns:
            Lista de violaciones detectadas
        """
        violations = []

        for detection in detections:
            location = detection['location']
            tipo = detection.get('tipo', 'desconocido')
            nombre = detection.get('nombre', 'Desconocido')

            # Centro del rostro
            top, right, bottom, left = location
            center = ((left + right) // 2, (top + bottom) // 2)

            # Verificar cada zona
            for zone in self.zones:
                # Verificar si el punto está dentro del polígono
                is_inside = cv2.pointPolygonTest(
                    zone['polygon'],
                    center,
                    False
                ) >= 0

                if is_inside:
                    # Verificar autorización
                    if tipo not in zone['authorized_types'] and tipo != 'desconocido':
                        violations.append({
                            'zone_name': zone['name'],
                            'person_name': nombre,
                            'person_type': tipo,
                            'location': location,
                            'timestamp': datetime.now()
                        })

        self.violations = violations
        return violations

    def draw_zones(self, frame: np.ndarray, show_violations: bool = True) -> np.ndarray:
        """Dibuja las zonas en el frame"""
        overlay = frame.copy()

        for zone in self.zones:
            # Color según si hay violaciones
            has_violation = any(v['zone_name'] == zone['name']
                                for v in self.violations)

            color = (0, 0, 255) if has_violation else (255, 255, 0)

            # Dibujar polígono
            cv2.polylines(overlay, [zone['polygon']], True, color, 2)

            # Rellenar con transparencia
            cv2.fillPoly(overlay, [zone['polygon']], color)

            # Nombre de la zona
            centroid = np.mean(zone['polygon'], axis=0).astype(int)
            cv2.putText(frame, zone['name'], tuple(centroid),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Mezclar con transparencia
        alpha = 0.3
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Mostrar violaciones
        if show_violations and self.violations:
            y_pos = 30
            for violation in self.violations:
                text = f"⚠ ALERTA: {violation['person_name']} en {violation['zone_name']}"
                cv2.putText(frame, text, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                y_pos += 30

        return frame


class BehaviorAnalyzer:
    """
    Analiza comportamientos sospechosos basado en patrones de movimiento
    """

    def __init__(self, history_size: int = 100):
        """
        Args:
            history_size: Número de frames de historia a mantener
        """
        self.history_size = history_size
        self.person_histories = defaultdict(lambda: deque(maxlen=history_size))
        self.alerts = []

    def analyze_person(self, person_id: int, location: Tuple,
                       timestamp: datetime) -> List[str]:
        """
        Analiza el comportamiento de una persona

        Returns:
            Lista de comportamientos detectados
        """
        behaviors = []

        # Agregar a historia
        top, right, bottom, left = location
        center = ((left + right) // 2, (top + bottom) // 2)

        self.person_histories[person_id].append({
            'center': center,
            'timestamp': timestamp,
            'location': location
        })

        history = list(self.person_histories[person_id])

        if len(history) < 10:
            return behaviors

        # Análisis 1: Movimiento errático (zigzag)
        if self._is_erratic_movement(history):
            behaviors.append('movimiento_errático')

        # Análisis 2: Permanencia prolongada en un punto
        if self._is_loitering(history):
            behaviors.append('merodeo')

        # Análisis 3: Movimiento rápido (corriendo)
        if self._is_rapid_movement(history):
            behaviors.append('movimiento_rápido')

        # Análisis 4: Patrón de ida y vuelta
        if self._is_pacing(history):
            behaviors.append('patrullaje')

        return behaviors

    def _is_erratic_movement(self, history: List[Dict]) -> bool:
        """Detecta movimiento errático (zigzag)"""
        if len(history) < 20:
            return False

        # Calcular cambios de dirección
        direction_changes = 0
        prev_direction = None

        for i in range(1, len(history)):
            dx = history[i]['center'][0] - history[i - 1]['center'][0]
            dy = history[i]['center'][1] - history[i - 1]['center'][1]

            if abs(dx) > 5 or abs(dy) > 5:  # Movimiento significativo
                current_direction = (np.sign(dx), np.sign(dy))

                if prev_direction and current_direction != prev_direction:
                    direction_changes += 1

                prev_direction = current_direction

        # Si cambia de dirección más de 8 veces en 20 frames
        return direction_changes > 8

    def _is_loitering(self, history: List[Dict]) -> bool:
        """Detecta permanencia prolongada (merodeo)"""
        if len(history) < 50:
            return False

        # Verificar si ha estado en un área pequeña por mucho tiempo
        recent = history[-50:]

        centers = [h['center'] for h in recent]
        x_coords = [c[0] for c in centers]
        y_coords = [c[1] for c in centers]

        # Desviación estándar de posiciones
        x_std = np.std(x_coords)
        y_std = np.std(y_coords)

        # Si la desviación es muy baja, está quieto
        return x_std < 30 and y_std < 30

    def _is_rapid_movement(self, history: List[Dict]) -> bool:
        """Detecta movimiento rápido (corriendo)"""
        if len(history) < 5:
            return False

        recent = history[-5:]

        # Calcular velocidad promedio
        total_distance = 0
        for i in range(1, len(recent)):
            dx = recent[i]['center'][0] - recent[i - 1]['center'][0]
            dy = recent[i]['center'][1] - recent[i - 1]['center'][1]
            distance = np.sqrt(dx ** 2 + dy ** 2)
            total_distance += distance

        avg_speed = total_distance / (len(recent) - 1)

        # Umbral para detectar movimiento rápido
        return avg_speed > 50  # píxeles por frame

    def _is_pacing(self, history: List[Dict]) -> bool:
        """Detecta patrón de ida y vuelta (patrullaje)"""
        if len(history) < 30:
            return False

        # Verificar si hay un patrón de movimiento de ida y vuelta
        x_coords = [h['center'][0] for h in history[-30:]]

        # Detectar reversiones de dirección
        reversals = 0
        for i in range(2, len(x_coords)):
            if ((x_coords[i] - x_coords[i - 1]) * (x_coords[i - 1] - x_coords[i - 2])) < 0:
                reversals += 1

        # Si hay múltiples reversiones, es patrullaje
        return reversals >= 4

    def get_alert_text(self, behaviors: List[str]) -> str:
        """Convierte comportamientos en texto de alerta"""
        messages = {
            'movimiento_errático': '⚠ Comportamiento errático detectado',
            'merodeo': '⚠ Persona merodeando en el área',
            'movimiento_rápido': '⚠ Movimiento rápido detectado',
            'patrullaje': '⚠ Patrón de patrullaje detectado'
        }

        alerts = [messages.get(b, b) for b in behaviors]
        return ' | '.join(alerts) if alerts else ''


class TemporalAnalyzer:
    """
    Analiza patrones temporales de detecciones
    Identifica horarios inusuales, frecuencia de visitas, etc.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def analyze_person_pattern(self, person_id: int, days: int = 30) -> Dict:
        """
        Analiza el patrón de visitas de una persona

        Returns:
            Diccionario con análisis de patrones
        """
        # Obtener detecciones de los últimos N días
        from_date = datetime.now() - timedelta(days=days)

        # Query a la BD (necesitarías agregar este método a DatabaseManager)
        # detecciones = self.db.obtener_detecciones_persona(person_id, from_date)

        # Por ahora, retornamos estructura de ejemplo
        return {
            'person_id': person_id,
            'total_visits': 0,
            'avg_visits_per_day': 0,
            'most_common_hour': None,
            'unusual_hours': [],
            'visit_frequency': 'regular'  # regular, occasional, rare
        }

    def detect_unusual_time(self, timestamp: datetime, person_type: str) -> bool:
        """
        Detecta si una visita es en horario inusual

        Args:
            timestamp: Momento de la detección
            person_type: Tipo de persona (residente, empleado, etc.)
        """
        hour = timestamp.hour

        # Definir horarios normales según tipo
        normal_hours = {
            'residente': range(6, 24),  # 6 AM - 12 AM
            'empleado': range(7, 19),  # 7 AM - 7 PM
            'visitante_autorizado': range(8, 22)  # 8 AM - 10 PM
        }

        allowed = normal_hours.get(person_type, range(0, 24))

        return hour not in allowed


# =============================================================================
# INTEGRACIÓN CON DETECTION SERVICE
# =============================================================================

class AdvancedDetectionService:
    """
    Versión mejorada del DetectionService con features avanzados
    """

    def __init__(self, base_service, enable_counting: bool = True,
                 enable_zones: bool = False, enable_behavior: bool = True):
        """
        Args:
            base_service: Instancia del DetectionService original
            enable_counting: Activar contador de personas
            enable_zones: Activar zonas restringidas
            enable_behavior: Activar análisis de comportamiento
        """
        self.base_service = base_service

        # Features opcionales
        self.counter = PeopleCounter() if enable_counting else None
        self.zones = RestrictedZone() if enable_zones else None
        self.behavior = BehaviorAnalyzer() if enable_behavior else None

        self.stats = {
            'total_alerts': 0,
            'zone_violations': 0,
            'behavior_alerts': 0
        }

    def process_frame_advanced(self, frame: np.ndarray, camera_id: int) -> Dict:
        """
        Procesa frame con features avanzados
        """
        # Procesamiento base
        base_results = self.base_service.process_frame(frame, camera_id)

        face_locations = [r['location'] for r in base_results['recognitions']]

        # Contador de personas
        if self.counter:
            counter_stats = self.counter.update(face_locations, frame.shape)
            base_results['counter'] = counter_stats

        # Zonas restringidas
        if self.zones:
            violations = self.zones.check_violations(base_results['recognitions'])
            base_results['zone_violations'] = violations
            self.stats['zone_violations'] += len(violations)

        # Análisis de comportamiento
        if self.behavior:
            for rec in base_results['recognitions']:
                if rec.get('persona_id'):
                    behaviors = self.behavior.analyze_person(
                        rec['persona_id'],
                        rec['location'],
                        datetime.now()
                    )
                    rec['behaviors'] = behaviors

                    if behaviors:
                        self.stats['behavior_alerts'] += 1

        return base_results

    def draw_advanced_features(self, frame: np.ndarray, results: Dict) -> np.ndarray:
        """Dibuja todos los features avanzados en el frame"""
        display_frame = frame.copy()

        # Contador
        if self.counter and 'counter' in results:
            stats = results['counter']
            y_pos = frame.shape[0] - 100

            cv2.putText(display_frame, f"Personas: {stats['current_count']}",
                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Entradas: {stats['total_entries']}",
                        (10, y_pos + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Salidas: {stats['total_exits']}",
                        (10, y_pos + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            display_frame = self.counter.draw_counting_line(display_frame)

        # Zonas
        if self.zones:
            display_frame = self.zones.draw_zones(display_frame)

        # Comportamientos
        if self.behavior:
            alert_y = 60
            for rec in results.get('recognitions', []):
                if rec.get('behaviors'):
                    alert = self.behavior.get_alert_text(rec['behaviors'])
                    if alert:
                        cv2.putText(display_frame, alert, (10, alert_y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                        alert_y += 25

        return display_frame


if __name__ == '__main__':
    print("Features avanzados de IA cargados correctamente")
    print("\nFeatures disponibles:")
    print("  ✓ PeopleCounter - Contador inteligente de personas")
    print("  ✓ RestrictedZone - Zonas restringidas")
    print("  ✓ BehaviorAnalyzer - Análisis de comportamiento")
    print("  ✓ TemporalAnalyzer - Análisis de patrones temporales")