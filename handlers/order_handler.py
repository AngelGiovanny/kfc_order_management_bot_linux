"""
Handler para comandos de órdenes - Integra con tu bot existente
"""

import os
from typing import Optional, Dict, Any
from core.image_service import image_service
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderHandler:
    """
    Handler para comandos relacionados con documentos
    Se integra con tu bot principal sin modificar funcionalidades existentes
    """

    def __init__(self):
        self.image_service = image_service
        logger.info("OrderHandler inicializado (compatible)")

    async def handle_factura_command(self, store_code: str, cfac_id: str,
                                     chat_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Maneja comando /factura - Usa flujo 4-pasos

        Args:
            store_code: Código de tienda (ej: K016)
            cfac_id: ID de factura
            chat_data: Datos adicionales del chat (opcional)

        Returns:
            Dict con resultado de la operación
        """
        try:
            logger.info(f"📄 Comando FACTURA recibido: {store_code} - {cfac_id}")

            # Validar
            if not store_code or not cfac_id:
                return {
                    "success": False,
                    "message": "❌ Se requiere código de tienda y número de factura",
                    "command": "factura"
                }

            # Usar flujo 4-pasos NUEVO
            image_path = await self.image_service.generate_factura_4step(store_code, cfac_id)

            if image_path and os.path.exists(image_path):
                file_size = os.path.getsize(image_path)

                response = {
                    "success": True,
                    "message": f"✅ Factura {cfac_id} generada exitosamente",
                    "command": "factura",
                    "store_code": store_code,
                    "cfac_id": cfac_id,
                    "image_path": image_path,
                    "file_size": file_size,
                    "file_type": "image/png"
                }

                # Agregar datos de chat si están disponibles
                if chat_data:
                    response.update({
                        "chat_id": chat_data.get("chat_id"),
                        "user_id": chat_data.get("user_id"),
                        "message_id": chat_data.get("message_id")
                    })

                logger.info(f"✅ Factura generada: {image_path} ({file_size} bytes)")
                return response

            else:
                # Fallback: intentar con método antiguo para compatibilidad
                logger.info("🔄 Intentando método antiguo como fallback...")
                image_bytes = await self.image_service.generate_invoice_image(store_code, cfac_id)

                if image_bytes:
                    # Guardar bytes temporalmente
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                        f.write(image_bytes)
                        temp_path = f.name

                    response = {
                        "success": True,
                        "message": f"✅ Factura {cfac_id} generada (método antiguo)",
                        "command": "factura",
                        "store_code": store_code,
                        "cfac_id": cfac_id,
                        "image_path": temp_path,
                        "file_size": len(image_bytes),
                        "file_type": "image/png",
                        "method": "legacy"
                    }

                    logger.info(f"✅ Factura generada con método antiguo: {temp_path}")
                    return response

                return {
                    "success": False,
                    "message": f"❌ No se pudo generar la factura {cfac_id}",
                    "command": "factura",
                    "store_code": store_code,
                    "cfac_id": cfac_id
                }

        except Exception as e:
            logger.error(f"💥 Error en handle_factura_command: {e}")
            return {
                "success": False,
                "message": f"❌ Error interno: {str(e)}",
                "command": "factura",
                "error": str(e)
            }

    async def handle_comanda_command(self, store_code: str, cfac_id: str,
                                     chat_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Maneja comando /comanda - Usa flujo 4-pasos
        """
        try:
            logger.info(f"🍗 Comando COMANDA recibido: {store_code} - {cfac_id}")

            if not store_code or not cfac_id:
                return {
                    "success": False,
                    "message": "❌ Se requiere código de tienda y número de factura",
                    "command": "comanda"
                }

            # Usar flujo 4-pasos NUEVO
            image_path = await self.image_service.generate_comanda_4step(store_code, cfac_id)

            if image_path and os.path.exists(image_path):
                file_size = os.path.getsize(image_path)

                response = {
                    "success": True,
                    "message": f"✅ Comanda {cfac_id} generada exitosamente",
                    "command": "comanda",
                    "store_code": store_code,
                    "cfac_id": cfac_id,
                    "image_path": image_path,
                    "file_size": file_size,
                    "file_type": "image/png"
                }

                if chat_data:
                    response.update({
                        "chat_id": chat_data.get("chat_id"),
                        "user_id": chat_data.get("user_id"),
                        "message_id": chat_data.get("message_id")
                    })

                logger.info(f"✅ Comanda generada: {image_path} ({file_size} bytes)")
                return response

            else:
                # Fallback con método antiguo
                logger.info("🔄 Intentando método antiguo para comanda...")
                image_bytes = await self.image_service.generate_comanda_image(store_code, cfac_id)

                if image_bytes:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                        f.write(image_bytes)
                        temp_path = f.name

                    response = {
                        "success": True,
                        "message": f"✅ Comanda {cfac_id} generada (método antiguo)",
                        "command": "comanda",
                        "store_code": store_code,
                        "cfac_id": cfac_id,
                        "image_path": temp_path,
                        "file_size": len(image_bytes),
                        "file_type": "image/png",
                        "method": "legacy"
                    }

                    logger.info(f"✅ Comanda generada con método antiguo: {temp_path}")
                    return response

                return {
                    "success": False,
                    "message": f"❌ No se pudo generar la comanda {cfac_id}",
                    "command": "comanda",
                    "store_code": store_code,
                    "cfac_id": cfac_id
                }

        except Exception as e:
            logger.error(f"💥 Error en handle_comanda_command: {e}")
            return {
                "success": False,
                "message": f"❌ Error interno: {str(e)}",
                "command": "comanda",
                "error": str(e)
            }

    async def handle_nota_credito_command(self, store_code: str, cfac_id: str,
                                          chat_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Maneja comando /notacredito - Usa flujo 4-pasos
        """
        try:
            logger.info(f"📋 Comando NOTA CRÉDITO recibido: {store_code} - {cfac_id}")

            # Usar flujo 4-pasos
            image_path = await self.image_service.generate_nota_credito_4step(store_code, cfac_id)

            if image_path:
                return {
                    "success": True,
                    "message": f"✅ Nota de crédito {cfac_id} generada",
                    "command": "nota_credito",
                    "store_code": store_code,
                    "cfac_id": cfac_id,
                    "image_path": image_path
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ No se pudo generar la nota de crédito {cfac_id}",
                    "command": "nota_credito"
                }

        except Exception as e:
            logger.error(f"Error en handle_nota_credito_command: {e}")
            return {
                "success": False,
                "message": f"❌ Error: {str(e)}",
                "command": "nota_credito"
            }

    async def cleanup_temp_files(self):
        """Limpia archivos temporales"""
        try:
            self.image_service.cleanup_generated_files()
            logger.info("Archivos temporales limpiados")
        except Exception as e:
            logger.error(f"Error limpiando archivos: {e}")


# Instancia global para uso fácil
order_handler = OrderHandler()