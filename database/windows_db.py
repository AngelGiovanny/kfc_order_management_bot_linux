import pyodbc
from typing import Optional, Dict, Any
from config.database import DatabaseConfig, StoreDatabaseManager


class WindowsDatabase:
    """Conexión a bases de datos Windows"""

    def __init__(self):
        self.manager = StoreDatabaseManager()

    def get_connection(self, store_code: str) -> Optional[pyodbc.Connection]:
        """Obtiene conexión para tienda Windows"""
        return self.manager.get_connection(store_code, "windows")

    def execute_query(self, store_code: str, query: str, params: tuple = None) -> list:
        """Ejecuta una consulta en Windows"""
        conn = self.get_connection(store_code)
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Obtener nombres de columnas
            columns = [column[0] for column in cursor.description]

            # Obtener resultados
            results = []
            for row in cursor.fetchall():
                result_dict = {}
                for i, col in enumerate(columns):
                    result_dict[col] = row[i]
                results.append(result_dict)

            return results

        except Exception as e:
            print(f"Error ejecutando query: {e}")
            return []
        finally:
            cursor.close()

    def get_order_status(self, store_code: str, order_number: str) -> Optional[Dict[str, Any]]:
        """Obtiene estado de una orden"""
        query = """
        SELECT TOP 1 
            CFAC_ID as order_id,
            CFAC_NUMERO as order_number,
            CFAC_FECHA as order_date,
            CFAC_ESTADO as status,
            CFAC_TOTAL as total,
            CLI_NOMBRE as client_name
        FROM FACTURACION 
        WHERE CFAC_NUMERO = ?
        ORDER BY CFAC_FECHA DESC
        """

        results = self.execute_query(store_code, query, (order_number,))
        return results[0] if results else Nonepython main.pypython main.py