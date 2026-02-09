"""
Servicio de imágenes que usa la API integrada
"""

import asyncio
from typing import Optional
from utils.logger import get_logger
from core.image_api_client import integrated_api_client

logger = get_logger(__name__)


class APIImageService:
    """Servicio de imágenes que consume la API integrada"""

    def __init__(self):
        self.api_available = False
        self._test_api_connection()

    def _test_api_connection(self):
        """Prueba la conexión con la API"""
        try:
            # Esto se hará en async, pero para inicialización hacemos sync
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.api_available = loop.run_until_complete(
                integrated_api_client.test_connection()
            )
            loop.close()

            if self.api_available:
                logger.info("✅ Conexión con API integrada establecida")
            else:
                logger.warning("⚠️ No se pudo conectar a la API integrada")

        except Exception as e:
            logger.error(f"❌ Error probando conexión API: {e}")
            self.api_available = False

    async def generate_invoice_image(self, store_code: str, invoice_id: str,
                                     is_credit_note: bool = False) -> Optional[bytes]:
        """Genera imagen de factura usando la API"""
        try:
            if not self.api_available:
                logger.warning("API no disponible, usando fallback")
                return await self._generate_fallback_invoice_image(store_code, invoice_id, is_credit_note)

            image_bytes = await integrated_api_client.generate_invoice_image(
                store_code=store_code,
                cfac_id=invoice_id,
                is_credit_note=is_credit_note
            )

            if image_bytes:
                return image_bytes
            else:
                # Fallback si la API falla
                return await self._generate_fallback_invoice_image(store_code, invoice_id, is_credit_note)

        except Exception as e:
            logger.error(f"Error en generate_invoice_image: {e}")
            return await self._generate_fallback_invoice_image(store_code, invoice_id, is_credit_note)

    async def generate_comanda_image(self, store_code: str, invoice_id: str) -> Optional[bytes]:
        """Genera imagen de comanda usando la API"""
        try:
            if not self.api_available:
                logger.warning("API no disponible, usando fallback")
                return await self._generate_fallback_comanda_image(store_code, invoice_id)

            image_bytes = await integrated_api_client.generate_comanda_image(
                store_code=store_code,
                cfac_id=invoice_id
            )

            if image_bytes:
                return image_bytes
            else:
                # Fallback si la API falla
                return await self._generate_fallback_comanda_image(store_code, invoice_id)

        except Exception as e:
            logger.error(f"Error en generate_comanda_image: {e}")
            return await self._generate_fallback_comanda_image(store_code, invoice_id)

    async def _generate_fallback_invoice_image(self, store_code: str, invoice_id: str,
                                               is_credit_note: bool = False) -> Optional[bytes]:
        """Genera imagen de factura de fallback"""
        try:
            logger.info(
                f"Generando imagen de fallback para {'nota crédito' if is_credit_note else 'factura'} {invoice_id}")

            # Usar Selenium directamente como fallback
            from core.selenium_service import selenium_service

            image_bytes = await selenium_service.capture_invoice_image(
                store_code=store_code,
                invoice_id=invoice_id,
                is_credit_note=is_credit_note
            )

            return image_bytes

        except Exception as e:
            logger.error(f"Error en fallback invoice image: {e}")
            return None

    async def _generate_fallback_comanda_image(self, store_code: str, invoice_id: str) -> Optional[bytes]:
        """Genera imagen de comanda de fallback"""
        try:
            logger.info(f"Generando comanda de fallback para {invoice_id}")

            # Usar Selenium directamente como fallback
            from core.selenium_service import selenium_service

            image_bytes = await selenium_service.capture_comanda_image_by_invoice(
                store_code=store_code,
                invoice_id=invoice_id
            )

            return image_bytes

        except Exception as e:
            logger.error(f"Error en fallback comanda image: {e}")
            return None


# Instancia global
api_image_service = APIImageService()