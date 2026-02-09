"""
Handler especializado para manejo de imágenes
Usando el servicio de API integrada
"""

import asyncio
import io
import logging
from typing import Optional
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from utils.logger import get_logger
from services.api_image_service import api_image_service  # CAMBIADO

logger = get_logger(__name__)


class ImageHandler:
    """Manejador de imágenes para facturas y comandas"""

    def __init__(self):
        pass

    async def handle_invoice_image_request(self, bot: AsyncTeleBot, chat_id: int,
                                           store_code: str, invoice_id: str,
                                           is_credit_note: bool = False) -> bool:
        """Maneja la solicitud de imagen de factura usando API integrada"""
        try:
            tipo = "nota de crédito" if is_credit_note else "factura"

            # Enviar mensaje de procesamiento
            processing_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"🔄 *Generando imagen de {tipo} {invoice_id}...*",
                parse_mode="Markdown"
            )

            # Usar el servicio de API
            image_bytes = await api_image_service.generate_invoice_image(
                store_code, invoice_id, is_credit_note
            )

            if image_bytes:
                # Enviar imagen
                tipo_text = "Nota de Crédito" if is_credit_note else "Factura"
                caption = f"📄 *{tipo_text} {invoice_id}* - Tienda {store_code}"

                await bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(image_bytes),
                    caption=caption,
                    parse_mode="Markdown"
                )

                # Eliminar mensaje de procesamiento
                await bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)

                await self._show_action_buttons(bot, chat_id, store_code)
                return True
            else:
                # Actualizar mensaje de error
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text=f"❌ *No se pudo generar la imagen de la {tipo} {invoice_id}*",
                    parse_mode="Markdown"
                )
                return False

        except Exception as e:
            logger.error(f"Error en handle_invoice_image_request: {e}", exc_info=True)

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error procesando la solicitud:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
            return False

    async def handle_comanda_image_request(self, bot: AsyncTeleBot, chat_id: int,
                                           store_code: str, invoice_id: str) -> bool:
        """Maneja la solicitud de imagen de comanda usando API integrada"""
        try:
            # Enviar mensaje de procesamiento
            processing_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"🔄 *Generando imagen de comanda para factura {invoice_id}...*",
                parse_mode="Markdown"
            )

            # Usar el servicio de API
            image_bytes = await api_image_service.generate_comanda_image(store_code, invoice_id)

            if image_bytes:
                # Enviar imagen
                caption = f"🍗 *Comanda* - Factura {invoice_id}\nTienda: {store_code}"

                await bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(image_bytes),
                    caption=caption,
                    parse_mode="Markdown"
                )

                # Eliminar mensaje de procesamiento
                await bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)

                await self._show_action_buttons(bot, chat_id, store_code)
                return True
            else:
                # Actualizar mensaje de error
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text=f"❌ *No se pudo generar la imagen de comanda para {invoice_id}*",
                    parse_mode="Markdown"
                )
                return False

        except Exception as e:
            logger.error(f"Error en handle_comanda_image_request: {e}", exc_info=True)

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error procesando la solicitud:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
            return False

    async def _show_action_buttons(self, bot: AsyncTeleBot, chat_id: int, store_code: str):
        """Muestra botones de acción después de generar imagen"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        buttons = [
            types.KeyboardButton("🖼️ Factura imagen"),
            types.KeyboardButton("🍗 Comanda"),
            types.KeyboardButton("📄 Nota crédito"),
            types.KeyboardButton("🏠 Menú principal")
        ]

        markup.row(buttons[0], buttons[1])
        markup.row(buttons[2], buttons[3])

        await bot.send_message(
            chat_id=chat_id,
            text=f"🏪 *Tienda:* {store_code}\n\n¿Qué desea hacer ahora?",
            reply_markup=markup,
            parse_mode="Markdown"
        )


# Instancia global
image_handler = ImageHandler()