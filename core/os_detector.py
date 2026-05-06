"""
Detector de sistema operativo - MULTIMARCA CORREGIDO
Soporta: KFC(K), Menestras del Negro(M), Cajun(J), Tropi(T), Gus(G),
American Deli(A), Español(E), Juan Valdez(V), Baskin(BS), Cinnabon(CN),
Il Cappo(I), Cara Res(R)
"""

import socket
import logging
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class OSDetector:
    """Detecta si la tienda está en Linux o Windows - MULTIMARCA"""

    # Puerto SQL Server
    SQL_PORT = 1433
    # Tiempo de espera
    TIMEOUT = 2

    # Configuración de red por marca (segundo octeto de la IP)
    # Formato de IP: 10.{segundo_octeto}.{numero_tienda}.{20/30}
    BRAND_NETWORK_CONFIG = {
        'K': 101,   # KFC
        'M': 106,   # Menestras del Negro
        'J': 110,   # Cajun
        'T': 103,   # Tropi
        'G': 102,   # Gus
        'A': 105,   # American Deli
        'E': 104,   # Español
        'V': 115,   # Juan Valdez
        'BS': 107,  # Baskin Robbins
        'CN': 107,  # Cinnabon
        'I': 118,   # Il Cappo
        'R': 112,   # Cara Res
    }

    @staticmethod
    def extract_brand_and_number(store_code: str) -> tuple:
        """
        Extrae la marca y el número de tienda del código
        Ejemplos:
            K096 -> ('K', '096', 96)
            M012 -> ('M', '012', 12)
            J030 -> ('J', '030', 30)
            T045 -> ('T', '045', 45)
            G078 -> ('G', '078', 78)
            A012 -> ('A', '012', 12)
            E056 -> ('E', '056', 56)
            V010 -> ('V', '010', 10)
            I089 -> ('I', '089', 89)
            R034 -> ('R', '034', 34)
            BS05 -> ('BS', '05', 5)
            CN12 -> ('CN', '12', 12)
        """
        store_code = store_code.upper().strip()

        # Prefijos de dos letras
        if store_code.startswith(('BS', 'CN')):
            brand = store_code[:2]
            number_str = store_code[2:]
        else:
            brand = store_code[0]
            number_str = store_code[1:]

        # Limpiar número (remover ceros a la izquierda)
        number_str_clean = number_str.lstrip('0')
        number = int(number_str_clean) if number_str_clean else 0

        return brand, number_str, number

    @staticmethod
    def get_second_octet(store_code: str) -> int:
        """Obtiene el segundo octeto de la IP según la marca"""
        brand, _, _ = OSDetector.extract_brand_and_number(store_code)
        return OSDetector.BRAND_NETWORK_CONFIG.get(brand, 101)

    @staticmethod
    def get_store_number(store_code: str) -> int:
        """Obtiene el número de tienda (como entero)"""
        _, _, number = OSDetector.extract_brand_and_number(store_code)
        return number

    @staticmethod
    def generate_linux_ip(store_code: str) -> str:
        """Genera IP Linux para una tienda MULTIMARCA"""
        second_octet = OSDetector.get_second_octet(store_code)
        store_number = OSDetector.get_store_number(store_code)
        return f"10.{second_octet}.{store_number}.30"

    @staticmethod
    def generate_windows_ip(store_code: str) -> str:
        """Genera IP Windows para una tienda MULTIMARCA"""
        second_octet = OSDetector.get_second_octet(store_code)
        store_number = OSDetector.get_store_number(store_code)
        return f"10.{second_octet}.{store_number}.20"

    @staticmethod
    def _test_connection(ip: str, port: int) -> bool:
        """Prueba conexión a un puerto específico"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(OSDetector.TIMEOUT)
            result = sock.connect_ex((ip, port))
            sock.close()

            is_open = (result == 0)

            if is_open:
                logger.debug(f"Conexión exitosa a {ip}:{port}")
            else:
                logger.debug(f"Conexión fallida a {ip}:{port} (código: {result})")

            return is_open

        except socket.timeout:
            logger.debug(f"Timeout conectando a {ip}:{port}")
            return False
        except socket.gaierror as e:
            logger.debug(f"Error de resolución DNS para {ip}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error inesperado probando {ip}:{port}: {e}")
            return False

    @staticmethod
    def detect_os(store_code: str, quick: bool = True) -> Tuple[str, str]:
        """Detecta el sistema operativo de la tienda - MULTIMARCA"""
        logger.info(f"Detectando SO para {store_code} (quick={quick})")

        # Generar IPs según la marca
        linux_ip = OSDetector.generate_linux_ip(store_code)
        windows_ip = OSDetector.generate_windows_ip(store_code)

        second_octet = OSDetector.get_second_octet(store_code)
        store_number = OSDetector.get_store_number(store_code)

        logger.info(f"{store_code}: IP Windows={windows_ip}, IP Linux={linux_ip}")
        logger.info(f"{store_code}: Segundo octeto={second_octet}, Número tienda={store_number}")

        # Intentar conexiones concurrentes
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_ip = {
                executor.submit(OSDetector._test_connection, linux_ip, OSDetector.SQL_PORT): ('linux', linux_ip),
                executor.submit(OSDetector._test_connection, windows_ip, OSDetector.SQL_PORT): ('windows', windows_ip)
            }

            results = {'linux': False, 'windows': False}

            try:
                for future in as_completed(future_to_ip.keys(), timeout=OSDetector.TIMEOUT * 3):
                    try:
                        is_open = future.result()
                        os_type, ip = future_to_ip[future]
                        results[os_type] = is_open

                        if is_open:
                            logger.info(f"{store_code}: Puerto {OSDetector.SQL_PORT} abierto en {ip} -> {os_type.upper()}")
                    except Exception as e:
                        logger.error(f"Error en prueba de conexión: {e}")
            except Exception as e:
                logger.warning(f"Timeout en detección para {store_code}: {e}")

        # Evaluar resultados
        if results['linux'] and not results['windows']:
            logger.info(f"{store_code}: Linux detectado")
            return 'linux', linux_ip
        elif results['windows'] and not results['linux']:
            logger.info(f"{store_code}: Windows detectado")
            return 'windows', windows_ip
        elif results['linux'] and results['windows']:
            logger.info(f"{store_code}: Ambos sistemas responden, usando Windows (por defecto)")
            return 'windows', windows_ip
        else:
            if quick:
                logger.info(f"{store_code}: Probando solo Windows (modo rápido)")
                if OSDetector._test_connection(windows_ip, OSDetector.SQL_PORT):
                    logger.info(f"{store_code}: Windows detectado en modo rápido")
                    return 'windows', windows_ip
                else:
                    logger.info(f"{store_code}: Sin detección -> Windows por defecto")
                    return 'windows', windows_ip
            else:
                logger.info(f"{store_code}: Probando puertos adicionales")
                rdp_open = OSDetector._test_connection(windows_ip, 3389)
                ssh_open = OSDetector._test_connection(linux_ip, 22)

                if ssh_open and not rdp_open:
                    logger.info(f"{store_code}: Linux detectado por puerto SSH")
                    return 'linux', linux_ip
                elif rdp_open and not ssh_open:
                    logger.info(f"{store_code}: Windows detectado por puerto RDP")
                    return 'windows', windows_ip
                else:
                    logger.info(f"{store_code}: Indeterminado, usando Windows por defecto")
                    return 'windows', windows_ip

    @staticmethod
    def get_connection_info(store_code: str) -> dict:
        """Obtiene información de conexión completa para una tienda MULTIMARCA"""
        second_octet = OSDetector.get_second_octet(store_code)
        store_number = OSDetector.get_store_number(store_code)

        windows_ip = f"10.{second_octet}.{store_number}.20"
        linux_ip = f"10.{second_octet}.{store_number}.30"

        windows_port = OSDetector._test_connection(windows_ip, OSDetector.SQL_PORT)
        linux_port = OSDetector._test_connection(linux_ip, OSDetector.SQL_PORT)

        recommended_os = None
        if windows_port:
            recommended_os = "windows"
        elif linux_port:
            recommended_os = "linux"

        brand, _, _ = OSDetector.extract_brand_and_number(store_code)

        return {
            'store_code': store_code,
            'brand': brand,
            'store_number': store_number,
            'second_octet': second_octet,
            'windows_ip': windows_ip,
            'linux_ip': linux_ip,
            'windows_port_open': windows_port,
            'linux_port_open': linux_port,
            'recommended_os': recommended_os
        }

    @staticmethod
    def test_database_connection(store_code: str, os_type: str = "windows") -> dict:
        """Prueba la conexión a la base de datos y devuelve información detallada"""
        from config.database import db_manager

        result = {
            'success': False,
            'store_code': store_code,
            'os_type': os_type,
            'error': None,
            'details': None
        }

        try:
            conn = db_manager.get_connection(store_code, os_type)
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DB_NAME() as db_name, @@VERSION as version")
                row = cursor.fetchone()
                result['success'] = True
                result['details'] = {
                    'database': row[0] if row else 'Unknown',
                    'version': row[1][:100] if row and row[1] else 'Unknown'
                }
                cursor.close()
                conn.close()
            else:
                result['error'] = "No se pudo obtener conexión"
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error probando conexión a BD para {store_code}: {e}")

        return result

    @staticmethod
    def get_windows_address() -> str:
        """Obtiene dirección de servidor Windows"""
        return "10.101.0.10"

    @staticmethod
    def get_linux_address() -> str:
        """Obtiene dirección de servidor Linux"""
        return "10.101.0.20"


# Función de compatibilidad
def detect_os(store_code: str, quick: bool = True) -> Tuple[str, str]:
    """Función wrapper para compatibilidad"""
    return OSDetector.detect_os(store_code, quick)