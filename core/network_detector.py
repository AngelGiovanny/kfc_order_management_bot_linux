"""
Detector de red mejorado
"""

import socket
import logging
from typing import Optional, Dict, Any
import concurrent.futures

logger = logging.getLogger(__name__)


class NetworkDetector:
    """Detector de disponibilidad de red"""

    @staticmethod
    def test_port(host: str, port: int, timeout: float = 2.0) -> bool:
        """Prueba si un puerto está abierto"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception as e:
            logger.debug(f"Error probando {host}:{port}: {e}")
            return False

    @staticmethod
    def detect_store_os(store_code: str) -> Dict[str, Any]:
        """Detecta el sistema operativo de una tienda"""
        store_number = store_code[1:].lstrip('0')

        # IPs a probar
        ips_to_test = {
            'linux': f"10.101.{store_number}.20",
            'windows': f"10.101.{store_number}.10"
        }

        results = {}

        # Probar conexiones concurrentemente
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_ip = {}

            for os_type, ip in ips_to_test.items():
                future = executor.submit(NetworkDetector.test_port, ip, 1433, 3.0)
                future_to_ip[future] = (os_type, ip)

            for future in concurrent.futures.as_completed(future_to_ip.keys()):
                os_type, ip = future_to_ip[future]
                try:
                    is_open = future.result()
                    results[os_type] = {
                        'ip': ip,
                        'open': is_open,
                        'port': 1433
                    }

                    if is_open:
                        logger.info(f"{store_code}: {os_type.upper()} disponible en {ip}")
                except Exception as e:
                    logger.error(f"Error probando {ip}: {e}")
                    results[os_type] = {
                        'ip': ip,
                        'open': False,
                        'error': str(e)
                    }

        # Determinar resultado
        linux_open = results.get('linux', {}).get('open', False)
        windows_open = results.get('windows', {}).get('open', False)

        if linux_open and not windows_open:
            recommended = 'linux'
        elif windows_open and not linux_open:
            recommended = 'windows'
        elif linux_open and windows_open:
            recommended = 'linux'  # Preferir Linux si ambos responden
        else:
            # Ninguno responde, probar puertos secundarios
            recommended = NetworkDetector._fallback_detection(ips_to_test)

        return {
            'store_code': store_code,
            'results': results,
            'recommended_os': recommended,
            'detection_time': time.time() if 'time' in locals() else None
        }

    @staticmethod
    def _fallback_detection(ips_to_test: Dict) -> str:
        """Detección de fallback cuando el puerto 1433 no responde"""
        try:
            # Probar puertos comunes de cada SO
            common_ports = {
                'linux': [22, 80, 443],  # SSH, HTTP, HTTPS
                'windows': [3389, 445, 139]  # RDP, SMB, NetBIOS
            }

            results = {'linux': 0, 'windows': 0}

            for os_type, ports in common_ports.items():
                ip = ips_to_test[os_type]
                for port in ports:
                    if NetworkDetector.test_port(ip, port, 1.0):
                        results[os_type] += 1

            if results['linux'] > results['windows']:
                return 'linux'
            elif results['windows'] > results['linux']:
                return 'windows'
            else:
                return 'linux'  # Default a Linux

        except Exception as e:
            logger.error(f"Error en detección de fallback: {e}")
            return 'linux'  # Default a Linux