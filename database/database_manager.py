"""
Gestor de conexiones a base de datos
"""

import pyodbc
from typing import Optional, Dict
from config.settings import WINDOWS_SERVER, LINUX_SERVER_PREFIX, DEFAULT_PORT, DATABASE_NAME
from core.os_detector import OSDetector


class DatabaseManager:
    """Gestor de conexiones a bases de datos"""

    def __init__(self):
        self.connections: Dict[str, pyodbc.Connection] = {}

    def get_connection(self, store_code: str, os_type: str) -> Optional[pyodbc.Connection]:
        """Obtiene conexión a la base de datos"""
        connection_key = f"{store_code}_{os_type}"

        # Reutilizar conexión si existe
        if connection_key in self.connections:
            try:
                # Verificar que la conexión sigue activa
                conn = self.connections[connection_key]
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return conn
            except:
                # Si hay error, cerrar y crear nueva
                try:
                    self.connections[connection_key].close()
                except:
                    pass
                del self.connections[connection_key]

        # Crear nueva conexión
        try:
            if os_type == "windows":
                connection_string = self._get_windows_connection_string(store_code)
            else:
                connection_string = self._get_linux_connection_string(store_code)

            conn = pyodbc.connect(connection_string, timeout=30)
            self.connections[connection_key] = conn
            return conn

        except Exception as e:
            print(f"❌ Error conectando a {store_code} ({os_type}): {e}")
            return None

    def _get_windows_connection_string(self, store_code: str) -> str:
        """Genera string de conexión para Windows"""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={WINDOWS_SERVER}\\MAXPOINT;"
            f"DATABASE={DATABASE_NAME};"
            f"Trusted_Connection=yes;"
            f"Timeout=30;"
        )

    def _get_linux_connection_string(self, store_code: str) -> str:
        """Genera string de conexión para Linux"""
        store_number = store_code[1:]  # Eliminar 'K'
        ip_address = f"{LINUX_SERVER_PREFIX}.{store_number}.20"

        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={ip_address},{DEFAULT_PORT};"
            f"DATABASE={DATABASE_NAME};"
            f"UID=sa;"
            f"PWD=YourPassword;"
            f"Timeout=30;"
        )

    def close_all_connections(self):
        """Cierra todas las conexiones activas"""
        for key, conn in list(self.connections.items()):
            try:
                conn.close()
            except:
                pass
        self.connections.clear()


# Instancia global
db_manager = DatabaseManager()