"""
Logger mejorado para registrar uso detallado - COMPLETO ACTUALIZADO
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


class EnhancedUsageLogger:
    """Logger mejorado para estadísticas de uso"""

    def __init__(self):
        self.logs_dir = "logs"
        self.usage_file = os.path.join(self.logs_dir, "bot_usage.log")
        self.connections_file = os.path.join(self.logs_dir, "connections.log")
        self.errors_file = os.path.join(self.logs_dir, "errors.log")
        self._ensure_logs_dir()

    def _ensure_logs_dir(self):
        """Asegura que el directorio de logs exista"""
        os.makedirs(self.logs_dir, exist_ok=True)

        # Crear archivos si no existen
        for filepath in [self.usage_file, self.connections_file, self.errors_file]:
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Archivo de log creado: {datetime.now()}\n")

    def log_action(self, user_id: int, username: str, action: str, store: str = "", details: str = ""):
        """Registra acción del usuario con más detalles"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] USER:{user_id} NAME:{username} ACTION:{action} STORE:{store} DETAILS:{details}\n"

            with open(self.usage_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # También registrar en el log general si es importante
            if action in ["STORE_SETUP", "REPORT_COMMAND", "ERROR"]:
                logger = logging.getLogger("usage_tracker")
                logger.info(f"{username} ({user_id}) - {action} - {store} - {details}")

        except Exception as e:
            print(f"Error registrando acción: {e}")

    def log_connection(self, store_code: str, os_type: str, ip_address: str, status: str):
        """Registra eventos de conexión"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] STORE:{store_code} OS:{os_type} IP:{ip_address} STATUS:{status}\n"

            with open(self.connections_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Error registrando conexión: {e}")

    def log_error(self, error_type: str, error_message: str, user_id: str = "", store: str = ""):
        """Registra errores del sistema"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] TYPE:{error_type} USER:{user_id} STORE:{store} MESSAGE:{error_message}\n"

            with open(self.errors_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Error registrando error: {e}")


class ConnectionFilter(logging.Filter):
    """Filtro para logs de conexión"""

    def filter(self, record):
        message = record.getMessage().lower()
        connection_keywords = ['conexión', 'conectado', 'connected', 'connection', 'conectar']
        return any(keyword in message for keyword in connection_keywords)


class ErrorFilter(logging.Filter):
    """Filtro para logs de error"""

    def filter(self, record):
        return record.levelno >= logging.ERROR


class UsageFilter(logging.Filter):
    """Filtro para logs de uso"""

    def filter(self, record):
        message = record.getMessage().lower()
        usage_keywords = ['user', 'acción', 'action', 'store', 'tienda', 'reporte']
        return any(keyword in message for keyword in usage_keywords)


def setup_logging():
    """Configura el sistema de logging completo"""
    # Crear directorio de logs
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Configurar formato
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    formatter = logging.Formatter(log_format, date_format)

    # Configurar nivel raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler para archivo principal
    main_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'bot_main.log'),
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_file_handler.setLevel(logging.INFO)
    main_file_handler.setFormatter(formatter)
    root_logger.addHandler(main_file_handler)

    # Handler específico para conexiones
    connection_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'bot_connections.log'),
        maxBytes=5242880,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    connection_file_handler.setLevel(logging.INFO)
    connection_file_handler.setFormatter(formatter)
    connection_file_handler.addFilter(ConnectionFilter())
    root_logger.addHandler(connection_file_handler)

    # Handler específico para errores
    error_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'bot_errors.log'),
        maxBytes=5242880,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.addFilter(ErrorFilter())
    root_logger.addHandler(error_file_handler)

    # Handler específico para uso
    usage_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'bot_usage_detailed.log'),
        maxBytes=5242880,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    usage_file_handler.setLevel(logging.INFO)
    usage_file_handler.setFormatter(formatter)
    usage_file_handler.addFilter(UsageFilter())
    root_logger.addHandler(usage_file_handler)

    # Logger para seguimiento de uso
    usage_logger = logging.getLogger("usage_tracker")
    usage_logger.setLevel(logging.INFO)

    usage_tracker_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'usage_tracker.log'),
        maxBytes=5242880,
        backupCount=3,
        encoding='utf-8'
    )
    usage_tracker_handler.setFormatter(formatter)
    usage_logger.addHandler(usage_tracker_handler)

    # Logger para database
    db_logger = logging.getLogger("database")
    db_logger.setLevel(logging.INFO)

    # Crear instancia del logger de uso mejorado
    enhanced_logger = EnhancedUsageLogger()

    return enhanced_logger


def get_logger(name: str):
    """Obtiene un logger con el nombre especificado"""
    return logging.getLogger(name)


# Configurar logging al importar
usage_logger = setup_logging()

# Crear algunos loggers útiles predefinidos
main_logger = get_logger("main_bot")
db_logger = get_logger("database")
image_logger = get_logger("image_service")
print_logger = get_logger("print_service")