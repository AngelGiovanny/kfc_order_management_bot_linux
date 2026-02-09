"""
Handler especializado para manejo de imágenes
"""

import asyncio
import io
import logging
from typing import Optional
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from utils.logger import get_logger
from core.query_service import QueryService
from core.selenium_service import selenium_service
from core.linux_image_generator import KFCImageGenerator

logger = get_logger(__name__)


class ImageHandler:
    """Manejador de imágenes para facturas y comandas"""

    def __init__(self):
        self.image_generator = KFCImageGenerator()

    async def handle_invoice_image_request(self, bot: AsyncTeleBot, chat_id: int,
                                           store_code: str, invoice_id: str,
                                           is_credit_note: bool = False) -> bool:
        """Maneja la solicitud de imagen de factura"""
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔄 *Generando imagen para factura {invoice_id}...*",
                parse_mode="Markdown"
            )

            # 1. Intentar con Selenium primero
            selenium_image = None
            try:
                selenium_image = await selenium_service.capture_invoice_image(
                    store_code, invoice_id
                )
            except Exception as e:
                logger.warning(f"Selenium falló para factura {invoice_id}: {e}")

            # 2. Si Selenium falló, generar imagen local
            if not selenium_image:
                logger.info(f"Generando imagen local para factura {invoice_id}")

                # Obtener datos de la factura
                invoice_data = await QueryService.get_invoice_data(store_code, invoice_id)

                if invoice_data:
                    # Generar imagen con datos reales
                    image_bytes = await self.image_generator.generate_invoice_image_from_data(invoice_data)
                else:
                    # Generar imagen simple con datos mínimos
                    image_bytes = await self.image_generator.generate_simple_invoice_image(invoice_id, store_code)

                if image_bytes:
                    # Enviar imagen generada
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_bytes,
                        caption=f"📄 *Factura {invoice_id}* - Tienda {store_code}\n_Generado por el sistema_",
                        parse_mode="Markdown"
                    )

                    # Mostrar botones de acción
                    await self._show_action_buttons(bot, chat_id, store_code)
                    return True
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ *No se pudo generar la imagen de la factura {invoice_id}*",
                        parse_mode="Markdown"
                    )
                    return False
            else:
                # Enviar imagen de Selenium
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(selenium_image),
                    caption=f"📄 *Factura {invoice_id}* - Tienda {store_code}\n_Capturado del sistema_",
                    parse_mode="Markdown"
                )

                await self._show_action_buttons(bot, chat_id, store_code)
                return True

        except Exception as e:
            logger.error(f"Error en handle_invoice_image_request: {e}", exc_info=True)

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error generando imagen:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
            return False

    async def handle_comanda_image_request(self, bot: AsyncTeleBot, chat_id: int,
                                           store_code: str, invoice_id: str) -> bool:
        """Maneja la solicitud de imagen de comanda - MODIFICADO para usar nueva lógica"""
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔄 *Buscando comanda para factura {invoice_id}...*",
                parse_mode="Markdown"
            )

            # 1. Obtener datos de la comanda usando QueryService
            comanda_data = await QueryService.get_comanda_data(store_code, invoice_id)

            if not comanda_data:
                # Mostrar mensaje informativo con URL si existe ID de orden
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ *Comanda no encontrada*\n\n"
                         f"• Factura: `{invoice_id}`\n"
                         f"• Tienda: {store_code}\n\n"
                         f"_La factura puede no tener una orden asociada._",
                    parse_mode="Markdown"
                )
                await self._show_action_buttons(bot, chat_id, store_code)
                return False

            comanda_id = comanda_data.get('comanda_id', f"ORD-{invoice_id}")
            id_orden = comanda_data.get('id_orden')

            # 2. Generar URL de impresión si hay ID de orden
            url = ""
            if id_orden:
                url = await QueryService.generate_comanda_url(comanda_data)

            # 3. Intentar con Selenium primero para capturar imagen
            selenium_image = None
            if id_orden:  # Solo intentar con Selenium si hay ID de orden
                try:
                    selenium_image = await selenium_service.capture_comanda_image(
                        store_code, id_orden
                    )
                except Exception as e:
                    logger.warning(f"Selenium falló para comanda {comanda_id}: {e}")

            # 4. Procesar según el resultado
            if selenium_image:
                # Enviar imagen capturada por Selenium
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(selenium_image),
                    caption=f"🍗 *Comanda {comanda_id}* - Factura {invoice_id}\nTienda: {store_code}",
                    parse_mode="Markdown"
                )

                # Mostrar URL si existe
                if url:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"🔗 *URL de impresión:*\n`{url}`\n\n"
                             f"📋 Puede copiar la URL y abrirla en el navegador",
                        parse_mode="Markdown"
                    )

            else:
                # No hay imagen de Selenium, generar localmente o mostrar información
                if comanda_data:
                    # Generar imagen local si es posible
                    try:
                        image_bytes = await self.image_generator.generate_comanda_image_from_data(comanda_data)
                        if image_bytes:
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=image_bytes,
                                caption=f"🍗 *Comanda {comanda_id}* - Factura {invoice_id}\nTienda: {store_code}",
                                parse_mode="Markdown"
                            )
                    except Exception as e:
                        logger.warning(f"No se pudo generar imagen local: {e}")

                # Mostrar información de la comanda
                info_text = f"✅ *Comanda encontrada*\n\n"
                info_text += f"• Factura: `{invoice_id}`\n"
                info_text += f"• Tienda: {store_code}\n"
                info_text += f"• Comanda ID: `{comanda_id}`\n"
                info_text += f"• Cliente: {comanda_data.get('cliente', 'N/A')}\n"
                info_text += f"• Total: ${float(comanda_data.get('total', '0.00')):,.2f}\n"
                info_text += f"• Estado: {comanda_data.get('estado', 'N/A')}\n"
                info_text += f"• Fecha: {comanda_data.get('fecha', 'N/A')}\n"

                if url:
                    info_text += f"\n🔗 *URL de impresión:*\n`{url}`\n\n"
                    info_text += "📋 Puede copiar la URL y abrirla en el navegador"
                else:
                    info_text += f"\n⚠️ *No se encontró orden asociada para generar URL*"

                await bot.send_message(
                    chat_id=chat_id,
                    text=info_text,
                    parse_mode="Markdown"
                )

            await self._show_action_buttons(bot, chat_id, store_code)
            return True

        except Exception as e:
            logger.error(f"Error en handle_comanda_image_request: {e}", exc_info=True)

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error procesando comanda:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )

            await self._show_action_buttons(bot, chat_id, store_code)
            return False

    async def _show_action_buttons(self, bot: AsyncTeleBot, chat_id: int, store_code: str):
        """Muestra botones de acción después de generar imagen"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        buttons = [
            types.KeyboardButton("🖼️ Factura imagen"),
            types.KeyboardButton("🍗 Comanda"),
            types.KeyboardButton("🔍 Nueva consulta"),
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