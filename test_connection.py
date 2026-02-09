"""
Detector de sistema operativo - MEJORADO con reintentos
"""

import socket
import logging
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class OSDetector:
    """Detecta si la tienda está en Linux o Windows - MEJORADO"""

    # Rangos de IPs comunes
    LINUX_IP_RANGE = "10.101.{store}.20"
    WINDOWS_IP_RANGE = "10.101.{store}.10"

    # Puerto SQL Server
    SQL_PORT = 1433
    # Tiempo de espera
    TIMEOUT = 3  # Aumentado a 3 segundos
    # Reintentos
    MAX_RETRIES = 2

    @staticmethod
    def generate_linux_ip(store_code: str) -> str:
        """Genera IP Linux para una tienda"""
        store_number = store_code[1:].lstrip('0')
        return f"10.101.{store_number}.20"

    @staticmethod
    def generate_windows_ip(store_code: str) -> str:
        """Genera IP Windows para una tienda"""
        store_number = store_code[1:].lstrip('0')
        return f"10.101.{store_number}.10"

    @staticmethod
    def _test_connection_with_retry(ip: str, port: int, retries: int = MAX_RETRIES) -> bool:
        """Prueba conexión con reintentos"""
        for attempt in range(retries):
            try:
                logger.debug(f"Intento {attempt + 1} para {ip}:{port}")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(OSDetector.TIMEOUT)
                result = sock.connect_ex((ip, port))
                sock.close()

                # Si result es 0, el puerto está abierto
                is_open = (result == 0)

                if is_open:
                    logger.debug(f"✅ Puerto {port} abierto en {ip}")
                    return True
                else:
                    logger.debug(f"❌ Puerto {port} cerrado en {ip} (código: {result})")

            except socket.timeout:
                logger.debug(f"⏱️ Timeout en intento {attempt + 1} para {ip}:{port}")
            except socket.gaierror as e:
                logger.debug(f"🌐 Error DNS para {ip}: {e}")
                return False  # Error DNS, no reintentar
            except Exception as e:
                logger.debug(f"⚠️ Error inesperado probando {ip}:{port}: {e}")

            # Esperar antes de reintentar (excepto en el último intento)
            if attempt < retries - 1:
                time.sleep(1)

        return False

    @staticmethod
    def detect_os(store_code: str, quick: bool = True) -> Tuple[str, str]:
        """Detecta el sistema operativo de la tienda - MEJORADO"""
        logger.info(f"Detectando SO para {store_code} (quick={quick})")

        store_number = store_code[1:].lstrip('0')

        # Generar IPs a probar
        linux_ip = OSDetector.generate_linux_ip(store_code)
        windows_ip = OSDetector.generate_windows_ip(store_code)

        logger.info(f"🔍 Probando Linux: {linux_ip}:{OSDetector.SQL_PORT}")
        logger.info(f"🔍 Probando Windows: {windows_ip}:{OSDetector.SQL_PORT}")

        # Intentar conexiones con reintentos
        linux_open = OSDetector._test_connection_with_retry(linux_ip, OSDetector.SQL_PORT)
        windows_open = OSDetector._test_connection_with_retry(windows_ip, OSDetector.SQL_PORT)

        # Evaluar resultados
        if linux_open and not windows_open:
            logger.info(f"{store_code}: ✅ Linux detectado (puerto {OSDetector.SQL_PORT} abierto)")
            return 'linux', linux_ip
        elif windows_open and not linux_open:
            logger.info(f"{store_code}: ✅ Windows detectado (puerto {OSDetector.SQL_PORT} abierto)")
            return 'windows', windows_ip
        elif linux_open and windows_open:
            # Ambos responden, priorizar Linux
            logger.info(f"{store_code}: ⚠️ Ambos sistemas responden, usando Linux")
            return 'linux', linux_ip
        else:
            # Ninguno responde en el puerto 1433, probar puertos alternativos
            logger.info(f"{store_code}: 🔄 Ningún puerto 1433 respondiendo, probando puertos alternativos")

            if quick:
                # En modo rápido, usar heurística simple
                # Por defecto, asumir Linux para K007 y Windows para otras
                if store_code == "K007":
                    logger.info(f"{store_code}: 🎯 Usando Linux por defecto (K007)")
                    return 'linux', linux_ip
                else:
                    logger.info(f"{store_code}: 🎯 Usando Windows por defecto")
                    return 'windows', windows_ip
            else:
                # Modo completo: probar puertos SSH (22) y RDP (3389)
                ssh_open = OSDetector._test_connection_with_retry(linux_ip, 22)
                rdp_open = OSDetector._test_connection_with_retry(windows_ip, 3389)

                if ssh_open and not rdp_open:
                    logger.info(f"{store_code}: 🐧 Linux detectado por puerto SSH (22)")
                    return 'linux', linux_ip
                elif rdp_open and not ssh_open:
                    logger.info(f"{store_code}: 🪟 Windows detectado por puerto RDP (3389)")
                    return 'windows', windows_ip
                else:
                    # Usar estadísticas (más tiendas en Linux)
                    logger.info(f"{store_code}: 🤷 Indeterminado, usando Linux por defecto")
                    return 'linux', linux_ip

    @staticmethod
    def test_connectivity(store_code: str) -> dict:
        """Prueba conectividad completa a una tienda"""
        store_number = store_code[1:].lstrip('0')

        linux_ip = OSDetector.generate_linux_ip(store_code)
        windows_ip = OSDetector.generate_windows_ip(store_code)

        # Puertos a probar
        ports_to_test = {
            'sql': 1433,
            'ssh': 22,
            'rdp': 3389,
            'http': 80,
            'https': 443
        }

        results = {
            'store_code': store_code,
            'linux_ip': linux_ip,
            'windows_ip': windows_ip,
            'linux_ports': {},
            'windows_ports': {},
            'timestamp': time.time()
        }

        # Probar puertos para Linux
        for name, port in ports_to_test.items():
            is_open = OSDetector._test_connection_with_retry(linux_ip, port, retries=1)
            results['linux_ports'][name] = {
                'port': port,
                'open': is_open
            }

        # Probar puertos para Windows
        for name, port in ports_to_test.items():
            is_open = OSDetector._test_connection_with_retry(windows_ip, port, retries=1)
            results['windows_ports'][name] = {
                'port': port,
                'open': is_open
            }

        return results


# Función de compatibilidad
def detect_os(store_code: str, quick: bool = True) -> Tuple[str, str]:
    """Función wrapper para compatibilidad"""
    return OSDetector.detect_os(store_code, quick)