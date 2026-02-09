"""
config/database.py - Gestión de conexiones a bases de datos
"""

import pyodbc
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Gestor de conexiones a bases de datos SQL Server"""

    def __init__(self):
        self.connections = {}
        self.connection_info_cache = {}
        logger.info("DatabaseManager inicializado")

    def get_connection_string(self, store_code: str, os_type: str = "linux") -> str:
        """Genera la cadena de conexión para una tienda específica"""
        try:
            # Extraer número de tienda
            if store_code.startswith('K') and len(store_code) >= 2:
                store_number = store_code[1:].lstrip('0')
            else:
                store_number = store_code.lstrip('0')

            if not store_number:
                store_number = "0"

            # Configurar según sistema operativo
            if os_type.lower() == "linux":
                server = f"10.101.{store_number}.30"
            else:  # windows
                server = f"10.101.{store_number}.20"

            database = f"MAXPOINT_{store_code}"

            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID=sis_tercernivel;"
                f"PWD=T3rc3rn1*m4x;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=5;"
            )

            logger.debug(f"Cadena de conexión para {store_code} ({os_type}): {server}/{database}")
            return connection_string

        except Exception as e:
            logger.error(f"Error generando cadena de conexión para {store_code}: {e}")
            return ""

    def get_connection(self, store_code: str, os_type: Optional[str] = None) -> Optional[pyodbc.Connection]:
        """Obtiene una conexión a la base de datos de la tienda"""
        try:
            if not store_code:
                logger.error("Código de tienda no proporcionado")
                return None

            # Usar la conexión existente si está disponible
            cache_key = f"{store_code}_{os_type}" if os_type else store_code
            if cache_key in self.connections:
                try:
                    # Verificar que la conexión aún sea válida
                    conn = self.connections[cache_key]
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    logger.debug(f"Usando conexión existente para {store_code}")
                    return conn
                except Exception:
                    # La conexión se cerró, removerla
                    del self.connections[cache_key]

            # Si no se especifica OS, intentar ambos
            os_types_to_try = []
            if os_type:
                os_types_to_try.append(os_type)
            else:
                # Intentar Linux primero (más común)
                os_types_to_try = ["linux", "windows"]

            for current_os in os_types_to_try:
                try:
                    conn_str = self.get_connection_string(store_code, current_os)
                    if not conn_str:
                        continue

                    logger.info(f"Intentando conexión con {store_code} ({current_os})")
                    conn = pyodbc.connect(conn_str, timeout=5)

                    # Almacenar en caché la conexión exitosa
                    self.connections[cache_key] = conn
                    self.connection_info_cache[store_code] = {
                        'os_type': current_os,
                        'database': f"MAXPOINT_{store_code}"
                    }

                    logger.info(f"Conexión establecida con {store_code} ({current_os})")
                    return conn

                except pyodbc.OperationalError as op_err:
                    logger.warning(f"No se pudo conectar a {store_code} ({current_os}): {op_err}")
                    continue
                except Exception as e:
                    logger.error(f"Error conectando a {store_code} ({current_os}): {e}")
                    continue

            logger.error(f"No se pudo establecer conexión con {store_code}")
            return None

        except Exception as e:
            logger.error(f"Error en get_connection para {store_code}: {e}")
            return None

    def get_connection_info(self, store_code: str) -> Dict[str, Any]:
        """Obtiene información sobre la conexión recomendada"""
        try:
            # Primero intentar Linux
            linux_conn_str = self.get_connection_string(store_code, "linux")

            # Verificar si Linux es viable
            recommended_os = None
            database_name = f"MAXPOINT_{store_code}"

            # Intentar Linux primero
            try:
                pyodbc.connect(linux_conn_str, timeout=3)
                recommended_os = "linux"
            except:
                # Intentar Windows
                try:
                    windows_conn_str = self.get_connection_string(store_code, "windows")
                    pyodbc.connect(windows_conn_str, timeout=3)
                    recommended_os = "windows"
                except:
                    # Ninguno funciona
                    recommended_os = None

            return {
                'store_code': store_code,
                'recommended_os': recommended_os,
                'database_name': database_name,
                'linux_connection_string': linux_conn_str,
                'windows_connection_string': self.get_connection_string(store_code, "windows")
            }

        except Exception as e:
            logger.error(f"Error obteniendo información de conexión para {store_code}: {e}")
            return {
                'store_code': store_code,
                'recommended_os': None,
                'database_name': f"MAXPOINT_{store_code}",
                'linux_connection_string': "",
                'windows_connection_string': ""
            }

    def test_connection(self, store_code: str, os_type: str) -> bool:
        """Prueba una conexión específica"""
        try:
            conn_str = self.get_connection_string(store_code, os_type)
            if not conn_str:
                return False

            conn = pyodbc.connect(conn_str, timeout=3)
            conn.close()
            return True

        except Exception as e:
            logger.debug(f"Conexión fallida {store_code} ({os_type}): {e}")
            return False

    def close_connection(self, store_code: str, os_type: Optional[str] = None):
        """Cierra una conexión específica"""
        try:
            cache_key = f"{store_code}_{os_type}" if os_type else store_code
            if cache_key in self.connections:
                self.connections[cache_key].close()
                del self.connections[cache_key]
                logger.info(f"Conexión cerrada para {store_code}")
        except Exception as e:
            logger.error(f"Error cerrando conexión para {store_code}: {e}")

    def close_all_connections(self):
        """Cierra todas las conexiones activas"""
        try:
            for store_code, conn in list(self.connections.items()):
                try:
                    conn.close()
                    logger.debug(f"Conexión cerrada para {store_code}")
                except Exception as e:
                    logger.error(f"Error cerrando conexión {store_code}: {e}")

            self.connections.clear()
            logger.info("Todas las conexiones cerradas")
        except Exception as e:
            logger.error(f"Error cerrando todas las conexiones: {e}")


# Instancia global del gestor de base de datos
db_manager = DatabaseManager()