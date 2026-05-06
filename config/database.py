"""
config/database.py - Gestión de conexiones a bases de datos MULTIMARCA
Soporta: KFC(K), Menestras del Negro(M), Cajun(J), Tropi(T), Gus(G),
American Deli(A), Español(E), Juan Valdez(V), Baskin(BS), Cinnabon(CN),
Il Cappo(I), Cara Res(R)

NOTA: Para Juan Valdez, busca TODAS las variantes: MAXPOINT_Vxxx, MAXPOINT_JVxxx, etc.
"""

import pyodbc
from typing import Optional, Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Gestor de conexiones a bases de datos SQL Server MULTIMARCA"""

    def __init__(self):
        self.connections = {}
        self.connection_info_cache = {}

        # Configuración de red por marca (segundo octeto de la IP)
        # Formato: 10.{segundo_octeto}.{tienda}.{30 para Linux, 20 para Windows}
        self.BRAND_NETWORK_CONFIG = {
            'K': 101,   # KFC
            'M': 106,   # Menestras del Negro
            'J': 110,   # Cajun
            'T': 103,   # Tropi
            'G': 102,   # Gus
            'A': 105,   # American Deli
            'E': 104,   # Español (E)
            'V': 115,   # Juan Valdez
            'BS': 107,  # Baskin Robbins
            'CN': 107,  # Cinnabon (misma red que Baskin)
            'I': 118,   # Il Cappo
            'R': 112,   # Cara Res
        }

        # Rangos válidos por marca
        self.BRAND_RANGES = {
            'K': ('K001', 'K999'),
            'M': ('M001', 'M999'),
            'J': ('J001', 'J999'),
            'T': ('T001', 'T999'),
            'G': ('G001', 'G999'),
            'A': ('A001', 'A999'),
            'E': ('E001', 'E999'),
            'V': ('V001', 'V999'),
            'BS': ('BS01', 'BS999'),
            'CN': ('CN01', 'CN999'),
            'I': ('I001', 'I999'),
            'R': ('R001', 'R999'),
        }

        logger.info("DatabaseManager MULTIMARCA inicializado")

    def extract_brand_and_number(self, store_code: str) -> tuple:
        """
        Extrae la marca y el número de tienda del código
        Ejemplos:
            K096 -> ('K', '096', 96)
            BS05 -> ('BS', '05', 5)
            CN12 -> ('CN', '12', 12)
            V010 -> ('V', '010', 10)
        """
        store_code = store_code.upper().strip()

        # Prefijos de dos letras
        if store_code.startswith(('BS', 'CN')):
            brand = store_code[:2]
            number_str = store_code[2:]
        else:
            brand = store_code[0]
            number_str = store_code[1:]

        # Limpiar número (remover ceros a la izquierda para el cálculo)
        number_str_clean = number_str.lstrip('0')
        number = int(number_str_clean) if number_str_clean else 0

        return brand, number_str, number

    def get_second_octet(self, store_code: str) -> int:
        """Obtiene el segundo octeto de la IP según la marca"""
        brand, _, _ = self.extract_brand_and_number(store_code)
        return self.BRAND_NETWORK_CONFIG.get(brand, 101)  # Default a KFC

    def validate_store_code(self, store_code: str) -> bool:
        """Valida si el código de tienda está en los rangos permitidos"""
        store_code = store_code.upper().strip()

        for brand, (min_code, max_code) in self.BRAND_RANGES.items():
            if min_code <= store_code <= max_code:
                return True
        return False

    def get_database_names(self, store_code: str) -> List[str]:
        """
        Genera posibles nombres de base de datos para una tienda MULTIMARCA

        Para Juan Valdez (Vxxx) prueba TODAS las variantes:
            - MAXPOINT_V010
            - MAXPOINT_JV010
            - MAXPOINT_JV_010
            - MAXPOINT_V_010
            - JV010
            - V010

        Para otras marcas prueba el formato estándar
        """
        prefix = self.get_database_prefix()
        store_code_upper = store_code.upper().strip()
        names = [f"{prefix}{store_code_upper}"]  # MAXPOINT_V010

        # Para Juan Valdez (V), probar TODAS las variantes posibles
        if store_code_upper.startswith('V'):
            number_part = store_code_upper[1:]  # ej: "010"

            # Todas las variantes posibles para Juan Valdez
            variants = [
                f"{prefix}JV{number_part}",      # MAXPOINT_JV010
                f"{prefix}JV_{number_part}",     # MAXPOINT_JV_010
                f"{prefix}V_{number_part}",      # MAXPOINT_V_010
                f"JV{number_part}",              # JV010
                f"V{number_part}",               # V010
            ]
            names.extend(variants)
            logger.info(f"Juan Valdez {store_code_upper}: Probando {len(variants)} variantes: {variants}")

        # Para Baskin Robbins (BS) y Cinnabon (CN)
        elif store_code_upper.startswith(('BS', 'CN')):
            number_part = store_code_upper[2:]  # ej: "05"
            variants = [
                f"{prefix}{store_code_upper[0]}{number_part}",  # MAXPOINT_B05
            ]
            names.extend(variants)

        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names

    def get_connection_string(self, store_code: str, os_type: str = "windows", db_name_override: str = None) -> str:
        """
        Genera la cadena de conexión para una tienda específica MULTIMARCA

        Formato IP: 10.{segundo_octeto}.{numero_tienda}.{20/30}
        - Segundo octeto depende de la marca
        - Windows usa terminación .20
        - Linux usa terminación .30
        """
        try:
            if not self.validate_store_code(store_code):
                logger.error(f"Código de tienda inválido: {store_code}")
                return ""

            # Extraer marca y número
            brand, number_str, number = self.extract_brand_and_number(store_code)

            # Obtener segundo octeto según la marca
            second_octet = self.get_second_octet(store_code)

            # Configurar terminación según sistema operativo
            if os_type.lower() == "linux":
                termination = "30"
            else:  # windows
                termination = "20"

            # Construir IP: 10.{segundo_octeto}.{número_tienda}.{terminación}
            server = f"10.{second_octet}.{number}.{termination}"

            # Usar nombre de base de datos proporcionado o el estándar
            if db_name_override:
                database = db_name_override
            else:
                database = f"{self.get_database_prefix()}{store_code}"

            # Obtener puerto desde settings
            from config.settings import DEFAULT_PORT
            port = DEFAULT_PORT

            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server},{port};"
                f"DATABASE={database};"
                f"UID=sis_tercernivel;"
                f"PWD=T3rc3rn1*m4x;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=10;"
            )

            logger.debug(f"Cadena de conexión: SERVER={server},{port}, DATABASE={database}")
            return connection_string

        except Exception as e:
            logger.error(f"Error generando cadena de conexión para {store_code}: {e}")
            return ""

    def get_database_prefix(self) -> str:
        """Obtiene el prefijo de la base de datos"""
        from config.settings import DATABASE_PREFIX
        return DATABASE_PREFIX

    def get_connection(self, store_code: str, os_type: Optional[str] = None) -> Optional[pyodbc.Connection]:
        """Obtiene una conexión a la base de datos de la tienda MULTIMARCA"""
        try:
            if not store_code:
                logger.error("Código de tienda no proporcionado")
                return None

            if not self.validate_store_code(store_code):
                logger.error(f"Código de tienda no válido: {store_code}")
                return None

            # Usar la conexión existente si está disponible
            cache_key = f"{store_code}_{os_type}" if os_type else store_code
            if cache_key in self.connections:
                try:
                    conn = self.connections[cache_key]
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    logger.debug(f"Usando conexión existente para {store_code}")
                    return conn
                except Exception:
                    del self.connections[cache_key]

            # Obtener posibles nombres de base de datos
            possible_db_names = self.get_database_names(store_code)
            logger.info(f"Buscando conexión para {store_code}. Probando {len(possible_db_names)} nombre(s) de BD: {possible_db_names}")

            # Si no se especifica OS, intentar el detectado primero
            os_types_to_try = []
            if os_type:
                os_types_to_try = [os_type, "windows" if os_type == "linux" else "linux"]
            else:
                os_types_to_try = ["windows", "linux"]

            logger.info(f"OS types a probar para {store_code}: {os_types_to_try}")

            for current_os in os_types_to_try:
                for db_name in possible_db_names:
                    try:
                        conn_str = self.get_connection_string(store_code, current_os, db_name_override=db_name)
                        if not conn_str:
                            continue

                        logger.info(f"🔍 PROBANDO: {store_code} ({current_os}) - BD: {db_name}")
                        conn = pyodbc.connect(conn_str, timeout=15)

                        # Almacenar en caché la conexión exitosa
                        self.connections[cache_key] = conn

                        brand, _, number = self.extract_brand_and_number(store_code)
                        self.connection_info_cache[store_code] = {
                            'os_type': current_os,
                            'database': db_name,
                            'brand': brand,
                            'second_octet': self.get_second_octet(store_code),
                            'store_number': number
                        }

                        logger.info(f"✅ CONEXIÓN EXITOSA: {store_code} ({current_os}) - BD: {db_name}")
                        return conn

                    except pyodbc.OperationalError as op_err:
                        logger.warning(f"Falló: {store_code} ({current_os}) - BD: {db_name}: {op_err}")
                        continue
                    except Exception as e:
                        logger.error(f"Error: {store_code} ({current_os}) - BD: {db_name}: {e}")
                        continue

            logger.error(f"❌ No se pudo conectar a {store_code} - Probados: {possible_db_names}")
            return None

        except Exception as e:
            logger.error(f"Error en get_connection para {store_code}: {e}")
            return None

    def get_connection_info(self, store_code: str) -> Dict[str, Any]:
        """Obtiene información sobre la conexión recomendada MULTIMARCA"""
        try:
            if not self.validate_store_code(store_code):
                return {
                    'store_code': store_code,
                    'recommended_os': None,
                    'database_name': f"{self.get_database_prefix()}{store_code}",
                    'possible_databases': self.get_database_names(store_code),
                    'linux_connection_string': "",
                    'windows_connection_string': "",
                    'brand': None,
                    'valid': False,
                    'error': f"Código de tienda {store_code} no válido"
                }

            brand, _, number = self.extract_brand_and_number(store_code)
            second_octet = self.get_second_octet(store_code)
            possible_dbs = self.get_database_names(store_code)
            database_name = possible_dbs[0] if possible_dbs else f"{self.get_database_prefix()}{store_code}"

            from config.settings import DEFAULT_PORT
            port = DEFAULT_PORT

            # Construir cadenas de conexión
            linux_server = f"10.{second_octet}.{number}.30"
            windows_server = f"10.{second_octet}.{number}.20"

            linux_conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={linux_server},{port};"
                f"DATABASE={database_name};"
                f"UID=sis_tercernivel;"
                f"PWD=T3rc3rn1*m4x;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=5;"
            )

            windows_conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={windows_server},{port};"
                f"DATABASE={database_name};"
                f"UID=sis_tercernivel;"
                f"PWD=T3rc3rn1*m4x;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=5;"
            )

            # Verificar qué sistema operativo funciona
            recommended_os = None
            linux_works = False
            windows_works = False

            try:
                conn = pyodbc.connect(linux_conn_str, timeout=5)
                conn.close()
                linux_works = True
                recommended_os = "linux"
            except:
                pass

            try:
                conn = pyodbc.connect(windows_conn_str, timeout=5)
                conn.close()
                windows_works = True
                if not recommended_os:
                    recommended_os = "windows"
            except:
                pass

            return {
                'store_code': store_code,
                'recommended_os': recommended_os,
                'database_name': database_name,
                'possible_databases': possible_dbs,
                'linux_connection_string': linux_conn_str,
                'windows_connection_string': windows_conn_str,
                'linux_test': {'success': linux_works, 'server': linux_server},
                'windows_test': {'success': windows_works, 'server': windows_server},
                'brand': brand,
                'brand_name': self.get_brand_name(brand),
                'second_octet': second_octet,
                'store_number': number,
                'valid': True
            }

        except Exception as e:
            logger.error(f"Error obteniendo información de conexión para {store_code}: {e}")
            return {
                'store_code': store_code,
                'recommended_os': None,
                'database_name': f"{self.get_database_prefix()}{store_code}",
                'possible_databases': self.get_database_names(store_code),
                'linux_connection_string': "",
                'windows_connection_string': "",
                'linux_test': {'success': False, 'error': str(e)},
                'windows_test': {'success': False, 'error': str(e)},
                'brand': None,
                'valid': False,
                'error': str(e)
            }

    def get_brand_name(self, brand: str) -> str:
        """Obtiene el nombre completo de la marca"""
        brand_names = {
            'K': 'KFC',
            'M': 'Menestras del Negro',
            'J': 'Cajun',
            'T': 'Tropi',
            'G': 'Gus',
            'A': 'American Deli',
            'E': 'Español',
            'V': 'Juan Valdez',
            'BS': 'Baskin Robbins',
            'CN': 'Cinnabon',
            'I': 'Il Cappo',
            'R': 'Cara Res'
        }
        return brand_names.get(brand, brand)

    def test_connection(self, store_code: str, os_type: str) -> bool:
        """Prueba una conexión específica MULTIMARCA"""
        try:
            possible_dbs = self.get_database_names(store_code)
            for db_name in possible_dbs:
                conn_str = self.get_connection_string(store_code, os_type, db_name_override=db_name)
                if conn_str:
                    try:
                        conn = pyodbc.connect(conn_str, timeout=5)
                        conn.close()
                        logger.info(f"Test exitoso para {store_code} ({os_type}) - BD: {db_name}")
                        return True
                    except:
                        continue
            return False
        except Exception as e:
            logger.debug(f"Test fallido {store_code} ({os_type}): {e}")
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


# Función helper para validar código de tienda desde cualquier parte del código
def validate_store_code(store_code: str) -> bool:
    """Función global para validar código de tienda MULTIMARCA"""
    return db_manager.validate_store_code(store_code)


# Función helper para obtener información de la marca
def get_brand_info(store_code: str) -> Dict[str, Any]:
    """Obtiene información de la marca para un código de tienda"""
    if not db_manager.validate_store_code(store_code):
        return {'valid': False, 'error': 'Código inválido'}

    brand, number_str, number = db_manager.extract_brand_and_number(store_code)
    return {
        'valid': True,
        'store_code': store_code,
        'brand': brand,
        'brand_name': db_manager.get_brand_name(brand),
        'store_number': number,
        'store_number_str': number_str,
        'second_octet': db_manager.get_second_octet(store_code),
        'linux_ip': f"10.{db_manager.get_second_octet(store_code)}.{number}.30",
        'windows_ip': f"10.{db_manager.get_second_octet(store_code)}.{number}.20",
        'possible_databases': db_manager.get_database_names(store_code)
    }