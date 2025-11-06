# database/db_manager.py

import sqlite3
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json


class DatabaseManager:
    """Gestor centralizado de la base de datos SQLite"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """Inicializa la base de datos y crea las tablas si no existen"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre

        # Leer y ejecutar el schema SQL
        schema_path = Path(__file__).parent / 'schema.sql'
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.conn.executescript(f.read())
        else:
            self._create_tables_inline()

        self.conn.commit()

    def _create_tables_inline(self):
        """Crea las tablas directamente (por si schema.sql no existe)"""
        cursor = self.conn.cursor()

        # Tabla personas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100),
                tipo VARCHAR(20) DEFAULT 'residente',
                encoding BLOB NOT NULL,
                foto_referencia VARCHAR(255),
                activo BOOLEAN DEFAULT 1,
                notas TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla cámaras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS camaras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(100) NOT NULL,
                ubicacion VARCHAR(200),
                tipo VARCHAR(20),
                url_stream VARCHAR(255),
                activa BOOLEAN DEFAULT 1,
                configuracion TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla detecciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camara_id INTEGER NOT NULL,
                persona_id INTEGER,
                confianza FLOAT,
                es_desconocido BOOLEAN DEFAULT 0,
                imagen_captura VARCHAR(255),
                imagen_frame VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camara_id) REFERENCES camaras(id),
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            )
        ''')

        # Tabla eventos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo VARCHAR(50) NOT NULL,
                severidad VARCHAR(20) DEFAULT 'media',
                descripcion TEXT,
                deteccion_id INTEGER,
                camara_id INTEGER NOT NULL,
                resuelto BOOLEAN DEFAULT 0,
                notas_resolucion TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_resolucion TIMESTAMP,
                FOREIGN KEY (deteccion_id) REFERENCES detecciones(id),
                FOREIGN KEY (camara_id) REFERENCES camaras(id)
            )
        ''')

        self.conn.commit()

    # =========================================================================
    # MÉTODOS PARA PERSONAS
    # =========================================================================

    def agregar_persona(self, nombre: str, apellido: str, encoding: bytes,
                        tipo: str = 'residente', foto_referencia: str = None,
                        notas: str = None) -> int:
        """Agrega una nueva persona al sistema"""
        cursor = self.conn.cursor()

        # Serializar el encoding
        encoding_blob = pickle.dumps(encoding)

        cursor.execute('''
            INSERT INTO personas (nombre, apellido, tipo, encoding, foto_referencia, notas)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, tipo, encoding_blob, foto_referencia, notas))

        self.conn.commit()
        return cursor.lastrowid

    def obtener_personas_activas(self) -> List[Dict]:
        """Obtiene todas las personas activas del sistema"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, nombre, apellido, tipo, encoding, foto_referencia
            FROM personas
            WHERE activo = 1
        ''')

        personas = []
        for row in cursor.fetchall():
            personas.append({
                'id': row['id'],
                'nombre': row['nombre'],
                'apellido': row['apellido'],
                'tipo': row['tipo'],
                'encoding': pickle.loads(row['encoding']),
                'foto_referencia': row['foto_referencia']
            })

        return personas

    def obtener_persona(self, persona_id: int) -> Optional[Dict]:
        """Obtiene una persona específica por ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM personas WHERE id = ?
        ''', (persona_id,))

        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'nombre': row['nombre'],
                'apellido': row['apellido'],
                'tipo': row['tipo'],
                'encoding': pickle.loads(row['encoding']),
                'foto_referencia': row['foto_referencia'],
                'activo': row['activo'],
                'notas': row['notas']
            }
        return None

    def actualizar_persona(self, persona_id: int, **kwargs):
        """Actualiza los datos de una persona"""
        campos_validos = ['nombre', 'apellido', 'tipo', 'foto_referencia', 'activo', 'notas']
        campos = []
        valores = []

        for campo, valor in kwargs.items():
            if campo in campos_validos:
                campos.append(f"{campo} = ?")
                valores.append(valor)

        if campos:
            campos.append("ultima_modificacion = ?")
            valores.append(datetime.now())
            valores.append(persona_id)

            query = f"UPDATE personas SET {', '.join(campos)} WHERE id = ?"
            self.conn.execute(query, valores)
            self.conn.commit()

    def eliminar_persona(self, persona_id: int, soft_delete: bool = True):
        """Elimina una persona (por defecto soft delete)"""
        if soft_delete:
            self.conn.execute('UPDATE personas SET activo = 0 WHERE id = ?', (persona_id,))
        else:
            self.conn.execute('DELETE FROM personas WHERE id = ?', (persona_id,))
        self.conn.commit()

    # =========================================================================
    # MÉTODOS PARA CÁMARAS
    # =========================================================================

    def agregar_camara(self, nombre: str, ubicacion: str = None,
                       tipo: str = 'webcam', url_stream: str = None,
                       configuracion: dict = None) -> int:
        """Agrega una nueva cámara al sistema"""
        cursor = self.conn.cursor()
        config_json = json.dumps(configuracion) if configuracion else None

        cursor.execute('''
            INSERT INTO camaras (nombre, ubicacion, tipo, url_stream, configuracion)
            VALUES (?, ?, ?, ?, ?)
        ''', (nombre, ubicacion, tipo, url_stream, config_json))

        self.conn.commit()
        return cursor.lastrowid

    def obtener_camaras_activas(self) -> List[Dict]:
        """Obtiene todas las cámaras activas"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM camaras WHERE activa = 1')

        return [dict(row) for row in cursor.fetchall()]

    def obtener_camara(self, camara_id: int) -> Optional[Dict]:
        """Obtiene una cámara específica"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM camaras WHERE id = ?', (camara_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    # =========================================================================
    # MÉTODOS PARA DETECCIONES
    # =========================================================================

    def registrar_deteccion(self, camara_id: int, persona_id: Optional[int] = None,
                            confianza: float = None, es_desconocido: bool = False,
                            imagen_captura: str = None, imagen_frame: str = None) -> int:
        """Registra una nueva detección"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO detecciones 
            (camara_id, persona_id, confianza, es_desconocido, imagen_captura, imagen_frame)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (camara_id, persona_id, confianza, es_desconocido, imagen_captura, imagen_frame))

        self.conn.commit()
        return cursor.lastrowid

    def obtener_detecciones_recientes(self, limit: int = 50,
                                      camara_id: int = None) -> List[Dict]:
        """Obtiene las detecciones más recientes"""
        cursor = self.conn.cursor()

        query = '''
            SELECT d.*, p.nombre, p.apellido, c.nombre as camara_nombre
            FROM detecciones d
            LEFT JOIN personas p ON d.persona_id = p.id
            LEFT JOIN camaras c ON d.camara_id = c.id
        '''

        if camara_id:
            query += ' WHERE d.camara_id = ?'
            cursor.execute(query + ' ORDER BY d.timestamp DESC LIMIT ?', (camara_id, limit))
        else:
            cursor.execute(query + ' ORDER BY d.timestamp DESC LIMIT ?', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def obtener_ultima_deteccion_persona(self, persona_id: int,
                                         camara_id: int) -> Optional[Dict]:
        """Obtiene la última detección de una persona en una cámara específica"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM detecciones
            WHERE persona_id = ? AND camara_id = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (persona_id, camara_id))

        row = cursor.fetchone()
        return dict(row) if row else None

    # =========================================================================
    # MÉTODOS PARA EVENTOS
    # =========================================================================

    def crear_evento(self, tipo: str, camara_id: int, severidad: str = 'media',
                     descripcion: str = None, deteccion_id: int = None) -> int:
        """Crea un nuevo evento"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO eventos (tipo, severidad, descripcion, deteccion_id, camara_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (tipo, severidad, descripcion, deteccion_id, camara_id))

        self.conn.commit()
        return cursor.lastrowid

    def obtener_eventos_no_resueltos(self, limit: int = 100) -> List[Dict]:
        """Obtiene eventos pendientes de resolución"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.*, c.nombre as camara_nombre, d.persona_id
            FROM eventos e
            LEFT JOIN camaras c ON e.camara_id = c.id
            LEFT JOIN detecciones d ON e.deteccion_id = d.id
            WHERE e.resuelto = 0
            ORDER BY e.timestamp DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def resolver_evento(self, evento_id: int, notas: str = None):
        """Marca un evento como resuelto"""
        self.conn.execute('''
            UPDATE eventos 
            SET resuelto = 1, fecha_resolucion = ?, notas_resolucion = ?
            WHERE id = ?
        ''', (datetime.now(), notas, evento_id))
        self.conn.commit()

    # =========================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # =========================================================================

    def obtener_configuracion(self, clave: str) -> Optional[str]:
        """Obtiene un valor de configuración"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))

        row = cursor.fetchone()
        return row['valor'] if row else None

    def actualizar_configuracion(self, clave: str, valor: str):
        """Actualiza o crea un valor de configuración"""
        self.conn.execute('''
            INSERT OR REPLACE INTO configuracion (clave, valor, fecha_modificacion)
            VALUES (?, ?, ?)
        ''', (clave, valor, datetime.now()))
        self.conn.commit()

    # =========================================================================
    # MÉTODOS DE ESTADÍSTICAS
    # =========================================================================

    def obtener_estadisticas_hoy(self) -> Dict:
        """Obtiene estadísticas del día actual"""
        cursor = self.conn.cursor()
        hoy = datetime.now().date()

        stats = {}

        # Total de detecciones hoy
        cursor.execute('''
            SELECT COUNT(*) as total FROM detecciones
            WHERE DATE(timestamp) = ?
        ''', (hoy,))
        stats['detecciones_hoy'] = cursor.fetchone()['total']

        # Personas únicas detectadas hoy
        cursor.execute('''
            SELECT COUNT(DISTINCT persona_id) as total FROM detecciones
            WHERE DATE(timestamp) = ? AND persona_id IS NOT NULL
        ''', (hoy,))
        stats['personas_unicas_hoy'] = cursor.fetchone()['total']

        # Desconocidos detectados hoy
        cursor.execute('''
            SELECT COUNT(*) as total FROM detecciones
            WHERE DATE(timestamp) = ? AND es_desconocido = 1
        ''', (hoy,))
        stats['desconocidos_hoy'] = cursor.fetchone()['total']

        # Eventos pendientes
        cursor.execute('SELECT COUNT(*) as total FROM eventos WHERE resuelto = 0')
        stats['eventos_pendientes'] = cursor.fetchone()['total']

        return stats

    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()