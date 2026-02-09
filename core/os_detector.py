"""
Detector de sistema operativo - CORREGIDO
"""

import socket
import logging
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class OSDetector:
    """Detecta si la tienda está en Linux o Windows"""

    # Rangos de IPs comunes
    LINUX_IP_RANGE = "10.101.{store}.20"
    WINDOWS_IP_RANGE = "10.101.{store}.10"

    # Puerto SQL Server
    SQL_PORT = 1433
    # Tiempo de espera
    TIMEOUT = 2

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
    def _test_connection(ip: str, port: int) -> bool:
        """Prueba conexión a un puerto específico"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(OSDetector.TIMEOUT)
            result = sock.connect_ex((ip, port))
            sock.close()

            # Si result es 0, el puerto está abierto
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
        """Detecta el sistema operativo de la tienda - CORREGIDO"""
        logger.info(f"Detectando SO para {store_code} (quick={quick})")

        store_number = store_code[1:].lstrip('0')

        # Generar IPs a probar
        linux_ip = OSDetector.generate_linux_ip(store_code)
        windows_ip = OSDetector.generate_windows_ip(store_code)

        # Intentar conexiones concurrentes
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Programar las pruebas
            future_to_ip = {
                executor.submit(OSDetector._test_connection, linux_ip, OSDetector.SQL_PORT): ('linux', linux_ip),
                executor.submit(OSDetector._test_connection, windows_ip, OSDetector.SQL_PORT): ('windows', windows_ip)
            }

            # Esperar resultados con timeout
            results = {'linux': False, 'windows': False}
            completed = 0

            try:
                for future in as_completed(future_to_ip.keys(), timeout=OSDetector.TIMEOUT * 3):
                    try:
                        is_open = future.result()
                        os_type, ip = future_to_ip[future]
                        results[os_type] = is_open
                        completed += 1

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
            # Ambos responden, priorizar Linux
            logger.info(f"{store_code}: Ambos sistemas responden, usando Linux")
            return 'linux', linux_ip
        else:
            # Ninguno responde, usar heurística
            if quick:
                # Modo rápido: probar solo Linux
                logger.info(f"{store_code}: Probando solo Linux (modo rápido)")
                if OSDetector._test_connection(linux_ip, OSDetector.SQL_PORT):
                    logger.info(f"{store_code}: Linux detectado en modo rápido")
                    return 'linux', linux_ip
                else:
                    logger.info(f"{store_code}: Sin detección -> Windows por defecto")
                    return 'windows', windows_ip
            else:
                # Modo completo: probar puertos adicionales
                logger.info(f"{store_code}: Probando puertos adicionales")

                # Puerto común de Windows (RDP)
                rdp_open = OSDetector._test_connection(windows_ip, 3389)
                # Puerto común de Linux (SSH)
                ssh_open = OSDetector._test_connection(linux_ip, 22)

                if ssh_open and not rdp_open:
                    logger.info(f"{store_code}: Linux detectado por puerto SSH")
                    return 'linux', linux_ip
                elif rdp_open and not ssh_open:
                    logger.info(f"{store_code}: Windows detectado por puerto RDP")
                    return 'windows', windows_ip
                else:
                    # Usar estadísticas (más tiendas en Linux)
                    logger.info(f"{store_code}: Indeterminado, usando Linux por defecto")
                    return 'linux', linux_ip

    @staticmethod
    def get_windows_address() -> str:
        """Obtiene dirección de servidor Windows"""
        return "10.101.0.10"  # Servidor central Windows

    @staticmethod
    def get_linux_address() -> str:
        """Obtiene dirección de servidor Linux"""
        return "10.101.0.20"  # Servidor central Linux


# Función de compatibilidad
def detect_os(store_code: str, quick: bool = True) -> Tuple[str, str]:
    """Función wrapper para compatibilidad"""
    return OSDetector.detect_os(store_code, quick)