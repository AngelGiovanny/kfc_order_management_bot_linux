import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuración del Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "7405762231:AAGIObeGcSn82xalyCokGKuIUYl9TuJmTS8")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("ADMIN_IDS") else []

# Configuración de Base de Datos
WINDOWS_SERVER = os.getenv("WINDOWS_SERVER", "MAXPOINT")
WINDOWS_INSTANCE = os.getenv("WINDOWS_INSTANCE", "MAXPOINT")
LINUX_SERVER_PREFIX = os.getenv("LINUX_SERVER_PREFIX", "10.101")
DEFAULT_PORT = int(os.getenv("DEFAULT_PORT", "1433"))
DATABASE_PREFIX = os.getenv("DATABASE_PREFIX", "MAXPOINT_")

# Credenciales de base de datos
DB_USERNAME = os.getenv("DB_USERNAME", "sis_tercernivel")
DB_PASSWORD = os.getenv("DB_PASSWORD", "T3rc3rn1*m4x")

# Configuración de Impresión
PRINT_API_URL = os.getenv("PRINT_API_URL", "http://192.168.101.96:5000/api/ImpresionTickets/Impresion")

# Mapeo de impresoras
PRINTER_MAPPING = {
    "domi": "15",
    "lineadomi": "15",
    "caja1": "21",
    "linea": "21",
    "caja2": "22"
}

# Timeouts
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT", "300"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
DETECTION_TIMEOUT = int(os.getenv("DETECTION_TIMEOUT", "10"))

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports_data"
TEMPLATES_DIR = BASE_DIR / "utils" / "templates"
STATIC_DIR = BASE_DIR / "static"

# Crear directorios necesarios
for directory in [LOG_DIR, REPORTS_DIR, TEMPLATES_DIR, STATIC_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuración de logs
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configuración de conexión
USE_TRUSTED_CONNECTION = os.getenv("USE_TRUSTED_CONNECTION", "False").lower() == "true"

# Configuración de detección
ENABLE_PING_DETECTION = os.getenv("ENABLE_PING_DETECTION", "True").lower() == "true"
ENABLE_PORT_SCAN = os.getenv("ENABLE_PORT_SCAN", "True").lower() == "true"
DEFAULT_OS = os.getenv("DEFAULT_OS", "windows")  # windows o linux