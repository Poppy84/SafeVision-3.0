# api/app.py
"""
API REST Backend para el Dashboard de Videovigilancia
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
from pathlib import Path
import base64
import cv2
import numpy as np
from datetime import datetime, timedelta
import json

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from config import Config

# Inicializar Flask
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)  # Habilitar CORS para desarrollo

# Inicializar componentes del sistema
db = DatabaseManager(Config.DB_PATH)
detector = FaceDetector(model='hog')
recognizer = FaceRecognizer(db, tolerance=0.6)


# =============================================================================
# ENDPOINTS - DASHBOARD Y ESTADÍSTICAS
# =============================================================================

@app.route('/')
def index():
    """Página principal del dashboard"""
    return send_from_directory('static', 'index.html')


@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Obtiene estadísticas generales del dashboard"""
    try:
        # Estadísticas del día
        stats_hoy = db.obtener_estadisticas_hoy()

        # Personas registradas
        personas = db.obtener_personas_activas()

        # Eventos pendientes
        eventos = db.obtener_eventos_no_resueltos()

        # Detecciones recientes (últimas 24h)
        detecciones_recientes = db.obtener_detecciones_recientes(limit=100)

        # Calcular tendencias
        conocidos_hoy = stats_hoy['personas_unicas_hoy']
        desconocidos_hoy = stats_hoy['desconocidos_hoy']

        return jsonify({
            'success': True,
            'data': {
                'personas_registradas': len(personas),
                'detecciones_hoy': stats_hoy['detecciones_hoy'],
                'personas_unicas_hoy': conocidos_hoy,
                'desconocidos_hoy': desconocidos_hoy,
                'eventos_pendientes': stats_hoy['eventos_pendientes'],
                'eventos_criticos': len([e for e in eventos if e['severidad'] == 'alta']),
                'camaras_activas': len(db.obtener_camaras_activas()),
                'ultima_actualizacion': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/dashboard/activity', methods=['GET'])
def get_activity_timeline():
    """Obtiene línea de tiempo de actividad reciente"""
    try:
        days = int(request.args.get('days', 7))

        detecciones = db.obtener_detecciones_recientes(limit=1000)

        # Agrupar por día
        activity_by_day = {}
        for det in detecciones:
            fecha = det['timestamp'].split()[0]  # Solo la fecha
            if fecha not in activity_by_day:
                activity_by_day[fecha] = {
                    'conocidos': 0,
                    'desconocidos': 0,
                    'total': 0
                }

            activity_by_day[fecha]['total'] += 1
            if det['es_desconocido']:
                activity_by_day[fecha]['desconocidos'] += 1
            else:
                activity_by_day[fecha]['conocidos'] += 1

        # Convertir a lista ordenada
        activity_list = []
        for fecha, data in sorted(activity_by_day.items(), reverse=True)[:days]:
            activity_list.append({
                'fecha': fecha,
                **data
            })

        return jsonify({
            'success': True,
            'data': activity_list
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ENDPOINTS - PERSONAS
# =============================================================================

@app.route('/api/personas', methods=['GET'])
def get_personas():
    """Obtiene lista de todas las personas registradas"""
    try:
        personas = db.obtener_personas_activas()

        # Formatear respuesta
        personas_data = []
        for p in personas:
            persona_info = db.obtener_persona(p['id'])
            personas_data.append({
                'id': p['id'],
                'nombre': p['nombre'],
                'apellido': p['apellido'],
                'nombre_completo': f"{p['nombre']} {p['apellido'] or ''}".strip(),
                'tipo': p['tipo'],
                'foto_referencia': p['foto_referencia'],
                'activo': persona_info.get('activo', True),
                'fecha_registro': persona_info.get('fecha_registro', 'N/A')
            })

        return jsonify({
            'success': True,
            'data': personas_data,
            'total': len(personas_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/personas/<int:persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Obtiene detalles de una persona específica"""
    try:
        persona = db.obtener_persona(persona_id)

        if not persona:
            return jsonify({
                'success': False,
                'error': 'Persona no encontrada'
            }), 404

        # Obtener estadísticas de detecciones
        # (necesitarías agregar este método al DatabaseManager)

        return jsonify({
            'success': True,
            'data': {
                'id': persona['id'],
                'nombre': persona['nombre'],
                'apellido': persona['apellido'],
                'tipo': persona['tipo'],
                'foto_referencia': persona['foto_referencia'],
                'activo': persona['activo'],
                'notas': persona['notas'],
                'fecha_registro': 'N/A'  # Agregar desde BD
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/personas', methods=['POST'])
def create_persona():
    """Crea una nueva persona (desde formulario o imagen)"""
    try:
        data = request.get_json()

        nombre = data.get('nombre')
        apellido = data.get('apellido', '')
        tipo = data.get('tipo', 'residente')
        notas = data.get('notas', '')

        # Si viene una imagen en base64
        image_data = data.get('imagen')

        if not nombre:
            return jsonify({
                'success': False,
                'error': 'El nombre es obligatorio'
            }), 400

        if image_data:
            # Decodificar imagen base64
            img_bytes = base64.b64decode(image_data.split(',')[1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Detectar rostro
            detections = detector.detect_and_encode(frame, scale_factor=1.0)

            if len(detections) != 1:
                return jsonify({
                    'success': False,
                    'error': f'Se detectaron {len(detections)} rostros. Debe haber exactamente uno.'
                }), 400

            encoding = detections[0]['encoding']

            # Guardar foto de referencia
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{nombre.lower()}_{apellido.lower()}_{timestamp}.jpg"
            foto_path = Config.KNOWN_FACES_DIR / filename
            cv2.imwrite(str(foto_path), frame)

            # Agregar a la base de datos
            persona_id = recognizer.add_new_person(
                nombre=nombre,
                apellido=apellido,
                face_encoding=encoding,
                tipo=tipo,
                foto_referencia=str(foto_path),
                notas=notas
            )

            return jsonify({
                'success': True,
                'data': {
                    'id': persona_id,
                    'nombre': nombre,
                    'apellido': apellido
                },
                'message': 'Persona registrada exitosamente'
            }), 201

        else:
            return jsonify({
                'success': False,
                'error': 'Se requiere una imagen para registrar'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/personas/<int:persona_id>', methods=['PUT'])
def update_persona(persona_id):
    """Actualiza información de una persona"""
    try:
        data = request.get_json()

        # Actualizar campos permitidos
        db.actualizar_persona(persona_id, **data)

        return jsonify({
            'success': True,
            'message': 'Persona actualizada exitosamente'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/personas/<int:persona_id>', methods=['DELETE'])
def delete_persona(persona_id):
    """Elimina (desactiva) una persona"""
    try:
        db.eliminar_persona(persona_id, soft_delete=True)
        recognizer.reload_known_faces()

        return jsonify({
            'success': True,
            'message': 'Persona eliminada exitosamente'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ENDPOINTS - DETECCIONES
# =============================================================================

@app.route('/api/detecciones', methods=['GET'])
def get_detecciones():
    """Obtiene historial de detecciones"""
    try:
        limit = int(request.args.get('limit', 50))
        camera_id = request.args.get('camera_id')

        if camera_id:
            detecciones = db.obtener_detecciones_recientes(
                limit=limit,
                camara_id=int(camera_id)
            )
        else:
            detecciones = db.obtener_detecciones_recientes(limit=limit)

        # Formatear detecciones
        detecciones_data = []
        for det in detecciones:
            detecciones_data.append({
                'id': det['id'],
                'timestamp': det['timestamp'],
                'persona_id': det['persona_id'],
                'nombre': det['nombre'] if det['nombre'] else 'Desconocido',
                'apellido': det['apellido'] if det['apellido'] else '',
                'camara_nombre': det['camara_nombre'],
                'confianza': det['confianza'],
                'es_desconocido': bool(det['es_desconocido']),
                'imagen_captura': det['imagen_captura']
            })

        return jsonify({
            'success': True,
            'data': detecciones_data,
            'total': len(detecciones_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ENDPOINTS - EVENTOS
# =============================================================================

@app.route('/api/eventos', methods=['GET'])
def get_eventos():
    """Obtiene eventos y alertas"""
    try:
        resueltos = request.args.get('resueltos', 'false').lower() == 'true'

        if resueltos:
            # Necesitarías agregar método para obtener eventos resueltos
            eventos = []
        else:
            eventos = db.obtener_eventos_no_resueltos(limit=100)

        eventos_data = []
        for evento in eventos:
            eventos_data.append({
                'id': evento['id'],
                'tipo': evento['tipo'],
                'severidad': evento['severidad'],
                'descripcion': evento['descripcion'],
                'timestamp': evento['timestamp'],
                'camara_nombre': evento.get('camara_nombre', 'N/A'),
                'resuelto': bool(evento['resuelto'])
            })

        return jsonify({
            'success': True,
            'data': eventos_data,
            'total': len(eventos_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/eventos/<int:evento_id>/resolver', methods=['POST'])
def resolver_evento(evento_id):
    """Marca un evento como resuelto"""
    try:
        data = request.get_json()
        notas = data.get('notas', '')

        db.resolver_evento(evento_id, notas)

        return jsonify({
            'success': True,
            'message': 'Evento resuelto exitosamente'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ENDPOINTS - CÁMARAS
# =============================================================================

@app.route('/api/camaras', methods=['GET'])
def get_camaras():
    """Obtiene lista de cámaras"""
    try:
        camaras = db.obtener_camaras_activas()

        return jsonify({
            'success': True,
            'data': camaras,
            'total': len(camaras)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ENDPOINTS - CONFIGURACIÓN
# =============================================================================

@app.route('/api/configuracion', methods=['GET'])
def get_configuracion():
    """Obtiene configuración del sistema"""
    try:
        config_data = {
            'umbral_confianza': float(db.obtener_configuracion('umbral_confianza') or 0.6),
            'activar_alertas': db.obtener_configuracion('activar_alertas') == '1',
            'guardar_frames': db.obtener_configuracion('guardar_frames') == '1',
            'dias_retencion_imagenes': int(db.obtener_configuracion('dias_retencion_imagenes') or 30)
        }

        return jsonify({
            'success': True,
            'data': config_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/configuracion', methods=['POST'])
def update_configuracion():
    """Actualiza configuración del sistema"""
    try:
        data = request.get_json()

        for key, value in data.items():
            db.actualizar_configuracion(key, str(value))

        # Recargar configuración en el sistema
        if 'umbral_confianza' in data:
            recognizer.update_tolerance(float(data['umbral_confianza']))

        return jsonify({
            'success': True,
            'message': 'Configuración actualizada exitosamente'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# INICIAR SERVIDOR
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("SERVIDOR API - DASHBOARD DE VIDEOVIGILANCIA")
    print("=" * 70)
    print(f"\n✓ API iniciada en: http://localhost:5000")
    print(f"✓ Dashboard: http://localhost:5000")
    print("\nEndpoints disponibles:")
    print("  GET  /api/dashboard/stats")
    print("  GET  /api/personas")
    print("  POST /api/personas")
    print("  GET  /api/detecciones")
    print("  GET  /api/eventos")
    print("  GET  /api/camaras")
    print("\nPresiona Ctrl+C para detener")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)