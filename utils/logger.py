# utils/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


def setup_logger(name: str,
                 log_file: str = None,
                 level: str = 'INFO',
                 log_to_console: bool = True,
                 log_to_file: bool = True,
                 max_bytes: int = 10485760,  # 10MB
                 backup_count: int = 5) -> logging.Logger:
    """
    Configura un logger profesional para el sistema

    Args:
        name: Nombre del logger (usualmente __name__)
        log_file: Ruta del archivo de log (None = auto-generar)
        level: Nivel de logging ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_to_console: Mostrar logs en consola
        log_to_file: Guardar logs en archivo
        max_bytes: Tamaño máximo del archivo antes de rotar
        backup_count: Número de archivos de backup a mantener

    Returns:
        Logger configurado
    """
    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger

    # Formato de los mensajes
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Handler para consola
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    # Handler para archivo
    if log_to_file:
        # Generar nombre de archivo si no se especificó
        if log_file is None:
            from config import Config
            log_dir = Config.LOGS_DIR
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"videovigilancia_{timestamp}.log"

        # Asegurar que el directorio existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (rota cuando alcanza tamaño máximo)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def setup_daily_logger(name: str, log_dir: Path = None) -> logging.Logger:
    """
    Configura un logger que rota diariamente (útil para producción)

    Args:
        name: Nombre del logger
        log_dir: Directorio donde guardar los logs

    Returns:
        Logger configurado
    """
    from config import Config

    if log_dir is None:
        log_dir = Config.LOGS_DIR

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    # Formato detallado
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler que rota a medianoche
    log_file = log_dir / "videovigilancia.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Mantener 30 días de logs
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y%m%d"
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


class PerformanceLogger:
    """
    Logger especializado para medir performance del sistema
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics = {}

    def start_timer(self, operation: str):
        """Inicia un timer para una operación"""
        self.metrics[operation] = {
            'start': datetime.now(),
            'count': self.metrics.get(operation, {}).get('count', 0) + 1
        }

    def end_timer(self, operation: str):
        """Finaliza un timer y registra la duración"""
        if operation not in self.metrics or 'start' not in self.metrics[operation]:
            self.logger.warning(f"Timer '{operation}' no fue iniciado")
            return

        start = self.metrics[operation]['start']
        duration = (datetime.now() - start).total_seconds()

        # Actualizar métricas
        if 'durations' not in self.metrics[operation]:
            self.metrics[operation]['durations'] = []

        self.metrics[operation]['durations'].append(duration)

        # Log
        self.logger.debug(f"Performance | {operation} | {duration:.4f}s")

        return duration

    def log_summary(self):
        """Registra un resumen de todas las métricas"""
        self.logger.info("=" * 70)
        self.logger.info("RESUMEN DE PERFORMANCE")
        self.logger.info("=" * 70)

        for operation, data in self.metrics.items():
            if 'durations' in data and data['durations']:
                durations = data['durations']
                avg = sum(durations) / len(durations)
                min_dur = min(durations)
                max_dur = max(durations)
                count = data.get('count', 0)

                self.logger.info(
                    f"{operation:30} | Count: {count:5} | "
                    f"Avg: {avg:.4f}s | Min: {min_dur:.4f}s | Max: {max_dur:.4f}s"
                )

        self.logger.info("=" * 70)

    def reset_metrics(self):
        """Reinicia todas las métricas"""
        self.metrics = {}


# =============================================================================
# DECORADOR PARA LOGGING AUTOMÁTICO
# =============================================================================

def log_execution(logger: logging.Logger):
    """
    Decorador para loggear automáticamente la ejecución de funciones

    Uso:
        @log_execution(logger)
        def mi_funcion():
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Ejecutando {func.__name__}...")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"✓ {func.__name__} completado")
                return result
            except Exception as e:
                logger.error(f"✗ Error en {func.__name__}: {e}", exc_info=True)
                raise

        return wrapper

    return decorator


# =============================================================================
# LOGGER GLOBAL PARA EL SISTEMA
# =============================================================================

# Instancia global del logger principal
_system_logger = None


def get_system_logger() -> logging.Logger:
    """Obtiene el logger principal del sistema (singleton)"""
    global _system_logger

    if _system_logger is None:
        _system_logger = setup_logger(
            name='videovigilancia',
            level='INFO',
            log_to_console=True,
            log_to_file=True
        )

    return _system_logger


# =============================================================================
# UTILIDADES DE LOGGING
# =============================================================================

def log_system_info(logger: logging.Logger):
    """Registra información del sistema al inicio"""
    import platform
    import cv2
    import face_recognition

    logger.info("=" * 70)
    logger.info("SISTEMA DE VIDEOVIGILANCIA INTELIGENTE")
    logger.info("=" * 70)
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"OpenCV version: {cv2.__version__}")
    logger.info(f"face_recognition version: {face_recognition.__version__}")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 70)


def log_detection_event(logger: logging.Logger, detection_result: dict):
    """Registra un evento de detección de manera formateada"""
    nombre = detection_result.get('nombre', 'Desconocido')
    confianza = detection_result.get('confianza', 0)
    es_desconocido = detection_result.get('es_desconocido', False)

    if es_desconocido:
        logger.warning(f"⚠ DESCONOCIDO detectado")
    else:
        logger.info(f"✓ Detectado: {nombre} (confianza: {confianza:.2%})")


def log_error_with_context(logger: logging.Logger, error: Exception, context: dict):
    """Registra un error con contexto adicional"""
    logger.error(f"Error: {str(error)}")
    logger.error(f"Contexto: {context}")
    logger.error("Traceback:", exc_info=True)


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    # Ejemplo 1: Logger básico
    logger = setup_logger('test_logger')

    logger.debug("Este es un mensaje DEBUG")
    logger.info("Este es un mensaje INFO")
    logger.warning("Este es un mensaje WARNING")
    logger.error("Este es un mensaje ERROR")
    logger.critical("Este es un mensaje CRITICAL")

    print("\n" + "=" * 70 + "\n")

    # Ejemplo 2: Logger de performance
    perf_logger = PerformanceLogger(logger)

    import time

    for i in range(3):
        perf_logger.start_timer('test_operation')
        time.sleep(0.1)  # Simular operación
        perf_logger.end_timer('test_operation')

    perf_logger.log_summary()

    print("\n" + "=" * 70 + "\n")


    # Ejemplo 3: Decorador
    @log_execution(logger)
    def funcion_ejemplo():
        logger.info("Ejecutando lógica de la función...")
        return "resultado"


    resultado = funcion_ejemplo()

    print("\n✓ Revisa los archivos de log en data/logs/")