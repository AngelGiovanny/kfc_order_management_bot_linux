"""
Cliente para la API integrada de imágenes
"""

import aiohttp
import asyncio
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class IntegratedImageAPIClient:
    """Cliente para consumir la API integrada de imágenes"""

    def __init__(self, base_url: str = "http://localhost:5010"):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=30)
        logger.info(f"Cliente de API integrada inicializado: {self.base_url}")

    async def generate_invoice_image(self, store_code: str, cfac_id: str,
                                     is_credit_note: bool = False) -> Optional[bytes]:
        """Genera imagen de factura usando la API integrada"""
        try:
            url = f"{self.base_url}/generate/invoice"

            payload = {
                'store_code': store_code,
                'cfac_id': cfac_id,
                'is_credit_note': is_credit_note
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.info(f"✅ Imagen generada: {'NC' if is_credit_note else 'FAC'} {cfac_id}")
                        return image_data
                    else:
                        logger.error(f"❌ Error API: {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"⏱️  Timeout generando imagen de {cfac_id}")
            return None
        except aiohttp.ClientConnectorError:
            logger.error(f"🔌 No se pudo conectar a la API en {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Error generando imagen de {cfac_id}: {e}")
            return None

    async def generate_comanda_image(self, store_code: str, cfac_id: str) -> Optional[bytes]:
        """Genera imagen de comanda usando la API integrada"""
        try:
            url = f"{self.base_url}/generate/comanda"

            payload = {
                'store_code': store_code,
                'cfac_id': cfac_id
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.info(f"✅ Comanda generada para {cfac_id}")
                        return image_data
                    else:
                        logger.error(f"❌ Error API comanda: {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"⏱️  Timeout generando comanda {cfac_id}")
            return None
        except aiohttp.ClientConnectorError:
            logger.error(f"🔌 No se pudo conectar a la API en {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Error generando comanda {cfac_id}: {e}")
            return None

    async def test_connection(self) -> bool:
        """Prueba la conexión con la API"""
        try:
            url = f"{self.base_url}/health"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    return response.status == 200

        except Exception:
            return False


# Instancia global
integrated_api_client = IntegratedImageAPIClient()