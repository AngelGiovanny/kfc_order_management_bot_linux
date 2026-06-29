"""
Handlers combinados para el menú - Versión telebot - SIN BOTÓN 4-PASOS
VERSIÓN MEJORADA CON ESTRATEGIA DUAL LINUX/WINDOWS - CON PERÍODOS PREDEFINIDOS
"""

import asyncio
import logging
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests
from telebot import types
from config.database import db_manager
from database.queries import QueryManager
from utils.logger import get_logger, usage_logger

logger = get_logger(__name__)

# Variable global para el bot (se asignará desde main.py)
_bot_instance = None


def set_bot_instance(bot):
    """Asigna la instancia del bot para usar en callbacks"""
    global _bot_instance
    _bot_instance = bot


def get_bot():
    """Obtiene la instancia del bot"""
    return _bot_instance


def validate_store_code(store_code: str) -> bool:
    """Valida el código de tienda MULTIMARCA"""
    store_code = store_code.upper().strip()

    # Definir rangos válidos por marca (prefijo: (mínimo, máximo))
    valid_prefixes = {
        'K': (1, 999),  # KFC
        'M': (1, 999),  # Menestras del Negro
        'J': (1, 999),  # Cajun
        'T': (1, 999),  # Tropi
        'G': (1, 999),  # Gus
        'A': (1, 999),  # American Deli
        'E': (1, 999),  # Español
        'V': (1, 999),  # Juan Valdez
        'I': (1, 999),  # Il Cappo
        'R': (1, 999),  # Cara Res
    }

    # Prefijos de dos letras (siempre con 2 letras)
    two_letter_prefixes = {
        'BS': (1, 999),  # Baskin Robbins
        'CN': (1, 999),  # Cinnabon
    }

    # Verificar prefijos de dos letras
    if store_code[:2] in two_letter_prefixes:
        try:
            num_part = store_code[2:]
            if num_part and num_part.isdigit():
                num = int(num_part)
                min_num, max_num = two_letter_prefixes[store_code[:2]]
                return min_num <= num <= max_num
        except:
            pass
        return False

    # Verificar prefijos de una letra
    for prefix, (min_num, max_num) in valid_prefixes.items():
        if store_code.startswith(prefix):
            try:
                num_part = store_code[1:]
                if num_part and num_part.isdigit():
                    num = int(num_part)
                    return min_num <= num <= max_num
            except:
                pass
            return False

    return False


async def show_main_menu(bot, chat_id: int, store_code: str):
    """Muestra el menú principal completo - AHORA CON AUDITORÍA POR RANGO"""

    menu_text = "📋 *SELECCIONE UNA OPCIÓN:*"

    if store_code:
        menu_text = f"🏪 *Tienda:* {store_code}\n\n{menu_text}"

    # Crear teclado completo
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    buttons = [
        types.KeyboardButton("🔍 Verificar orden"),
        types.KeyboardButton("📊 Auditoría"),
        types.KeyboardButton("🖼️ Factura imagen"),
        types.KeyboardButton("📄 Nota crédito"),
        types.KeyboardButton("🍗 Comanda"),
        types.KeyboardButton("🔗 Código asociado"),
        types.KeyboardButton("🖨️ Re-Impresión"),
        types.KeyboardButton("🚚 Asignar Motorizado"),
        types.KeyboardButton("📅 Auditoría por Rango"),
        types.KeyboardButton("🔄 Cambiar tienda"),
        types.KeyboardButton("❌ Salir")
    ]

    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2], buttons[3])
    markup.row(buttons[4], buttons[5])
    markup.row(buttons[6], buttons[7])
    markup.row(buttons[8], buttons[9])
    markup.row(buttons[10])

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=menu_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        await bot.send_message(
            chat_id=chat_id,
            text=menu_text.replace('*', ''),
            reply_markup=markup
        )


async def show_action_buttons(bot, chat_id: int, store_code: str):
    """Muestra botones de acción después de una operación"""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    buttons = [
        types.KeyboardButton("🔍 Nueva consulta"),
        types.KeyboardButton("📅 Auditoría por Rango"),
        types.KeyboardButton("🏠 Menú principal"),
        types.KeyboardButton("🔄 Cambiar tienda"),
        types.KeyboardButton("❌ Salir")
    ]

    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2], buttons[3])
    markup.row(buttons[4])

    await bot.send_message(
        chat_id=chat_id,
        text=f"🏪 *Tienda:* {store_code}\n\n¿Qué desea hacer ahora?",
        reply_markup=markup,
        parse_mode="Markdown"
    )


async def handle_invoice_image(bot, chat_id: int, store_code: str, cfac_id: str, is_credit_note: bool = False):
    """Maneja generación de imagen de factura o nota de crédito"""
    try:
        doc_type = "Nota de Crédito" if is_credit_note else "Factura"

        await bot.send_message(
            chat_id=chat_id,
            text=f"🖼️ *Generando {doc_type} {cfac_id}...*\n\n"
                 f"🏪 Tienda: {store_code}\n"
                 f"⏳ Esto puede tomar unos segundos...",
            parse_mode="Markdown"
        )

        usage_logger.log_action(
            user_id=None,
            username="",
            action=f"{doc_type.upper().replace(' ', '_')}_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {cfac_id}"
        )

        from core.image_service import image_service

        if not image_service.is_available():
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ *Servicio de imágenes no disponible*\n\n"
                     f"El servicio no está disponible en este momento.\n"
                     f"Por favor, intente más tarde.",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        try:
            if is_credit_note:
                image_bytes = await image_service.generate_invoice_image(
                    store_code=store_code,
                    invoice_id=cfac_id,
                    is_credit_note=True
                )
            else:
                image_bytes = await image_service.generate_invoice_image(
                    store_code=store_code,
                    invoice_id=cfac_id,
                    is_credit_note=False
                )

            if image_bytes:
                caption = (
                    f"📄 *{doc_type} {cfac_id}*\n"
                    f"🏪 Tienda: {store_code}\n"
                    f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )

                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_bytes,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ {doc_type} generada exitosamente para {cfac_id}")
                except Exception as send_error:
                    logger.error(f"Error enviando foto: {send_error}")
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ *{doc_type} generada exitosamente*\n\n"
                             f"Documento: {cfac_id}\n"
                             f"Tienda: {store_code}\n"
                             f"📏 Tamaño: {len(image_bytes):,} bytes",
                        parse_mode="Markdown"
                    )
            else:
                await _show_invoice_fallback(bot, chat_id, store_code, cfac_id, doc_type)

        except Exception as img_error:
            logger.error(f"Error generando imagen: {img_error}")
            await _show_invoice_fallback(bot, chat_id, store_code, cfac_id, doc_type, img_error)

    except Exception as e:
        logger.error(f"Error en proceso de factura: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error en el proceso:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def _show_invoice_fallback(bot, chat_id: int, store_code: str,
                               cfac_id: str, doc_type: str,
                               error: Optional[Exception] = None):
    """Muestra datos de factura como fallback"""
    try:
        from config.database import db_manager

        await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ *No se pudo generar imagen de la {doc_type.lower()}*\n\n"
                 f"Buscando datos básicos del documento...",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error de conexión*\n\n"
                     f"No se pudo conectar a la base de datos de la tienda {store_code}.",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()
        try:
            cursor.execute("""
                SELECT TOP 1 
                    COALESCE(cfac_id, id, numero_factura) as numero,
                    COALESCE(cli_nombre, 'Cliente') as cliente,
                    COALESCE(cfac_fecha, fecha, GETDATE()) as fecha,
                    COALESCE(total, 0) as total
                FROM Cabecera_Factura 
                WHERE cfac_id = ? OR id = ? OR numero_factura = ?
            """, (cfac_id, cfac_id, cfac_id))

            result = cursor.fetchone()
            if result:
                fecha_str = result[2].strftime('%d/%m/%Y %H:%M') if hasattr(result[2], 'strftime') else str(result[2])

                response = (
                    f"📄 *{doc_type} encontrada*\n\n"
                    f"🔢 *Número:* {result[0]}\n"
                    f"👤 *Cliente:* {result[1]}\n"
                    f"📅 *Fecha:* {fecha_str}\n"
                    f"💰 *Total:* ${float(result[3]):,.2f}\n\n"
                    f"🏪 *Tienda:* {store_code}\n"
                    f"⚠️ *Nota:* La imagen no pudo generarse, mostrando datos básicos."
                )

                if error:
                    response += f"\n\n📋 *Error:* `{str(error)[:150]}`"

            else:
                response = (
                    f"❌ *{doc_type} no encontrada*\n\n"
                    f"No se encontró información para {cfac_id} en la tienda {store_code}.\n\n"
                    f"📋 *Posibles causas:*\n"
                    f"• El documento no existe\n"
                    f"• Error de conexión con la base de datos\n"
                    f"• Formato de ID incorrecto"
                )

            await bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="Markdown"
            )

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        logger.error(f"Error en fallback de factura: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error obteniendo datos de {doc_type.lower()}*\n\n"
                 f"Por favor, verifique el ID e intente nuevamente.",
            parse_mode="Markdown"
        )


async def handle_comanda(bot, chat_id: int, store_code: str, cfac_id: str):
    """Maneja generación de comanda"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🍗 *Buscando comanda para factura {cfac_id}...*\n\n"
                 f"🏪 Tienda: {store_code}\n"
                 f"⏳ Esto puede tomar unos segundos...",
            parse_mode="Markdown"
        )

        usage_logger.log_action(
            user_id=None,
            username="",
            action="COMANDA_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {cfac_id}"
        )

        from core.image_service import image_service

        if not image_service.is_available():
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ *Servicio de imágenes no disponible*\n\n"
                     f"Por favor, intente más tarde.",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        try:
            image_bytes = await image_service.generate_comanda_image(
                store_code=store_code,
                invoice_id=cfac_id
            )

            if image_bytes:
                caption = (
                    f"🍗 *Comanda para factura {cfac_id}*\n"
                    f"🏪 Tienda: {store_code}\n"
                    f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )

                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_bytes,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Comanda generada exitosamente para factura {cfac_id}")
                except Exception as send_error:
                    logger.error(f"Error enviando foto: {send_error}")
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ *Comanda generada exitosamente*\n\n"
                             f"Factura: {cfac_id}\n"
                             f"Tienda: {store_code}\n"
                             f"📏 Tamaño: {len(image_bytes):,} bytes",
                        parse_mode="Markdown"
                    )
            else:
                await _show_comanda_fallback(bot, chat_id, store_code, cfac_id)

        except Exception as img_error:
            logger.error(f"Error generando comanda: {img_error}")
            await _show_comanda_fallback(bot, chat_id, store_code, cfac_id, img_error)

    except Exception as e:
        logger.error(f"Error en proceso de comanda: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error en el proceso:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def _show_comanda_fallback(bot, chat_id: int, store_code: str,
                               cfac_id: str, error: Optional[Exception] = None):
    """Muestra datos de comanda como fallback"""
    try:
        from config.database import db_manager

        await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ *No se pudo generar imagen de la comanda*\n\n"
                 f"Buscando datos básicos...",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error de conexión*\n\n"
                     f"No se pudo conectar a la base de datos.",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()
        try:
            cursor.execute("""
                SELECT TOP 1 
                    COALESCE(o.odp_id, o.id, o.numero_orden) as comanda_id,
                    COALESCE(o.fecha_creacion, GETDATE()) as fecha,
                    COALESCE(o.estado, 'Pendiente') as estado
                FROM Cabecera_OrdenPedido o
                INNER JOIN Cabecera_Factura f ON o.IDCabeceraOrdenPedido = f.IDCabeceraOrdenPedido
                WHERE f.cfac_id = ? OR f.id = ?
            """, (cfac_id, cfac_id))

            result = cursor.fetchone()
            if result:
                fecha_str = result[1].strftime('%d/%m/%Y %H:%M') if hasattr(result[1], 'strftime') else str(result[1])

                response = (
                    f"🍗 *Comanda encontrada*\n\n"
                    f"📄 *Factura asociada:* {cfac_id}\n"
                    f"🔢 *Comanda ID:* {result[0]}\n"
                    f"📅 *Fecha:* {fecha_str}\n"
                    f"📊 *Estado:* {result[2]}\n\n"
                    f"🏪 *Tienda:* {store_code}\n"
                    f"⚠️ *Nota:* La imagen no pudo generarse."
                )

                cursor.execute("""
                    SELECT TOP 5 
                        COALESCE(producto_desc, 'Producto') as producto,
                        COALESCE(cantidad, 1) as cantidad
                    FROM Detalle_OrdenPedido 
                    WHERE odp_id = ? OR id_orden = ?
                """, (result[0], result[0]))

                items = cursor.fetchall()
                if items:
                    response += "\n\n📋 *Items:*"
                    for idx, item in enumerate(items, 1):
                        response += f"\n{idx}. {item[0]} (x{item[1]})"
            else:
                response = (
                    f"❌ *Comanda no encontrada*\n\n"
                    f"No se encontró comanda para la factura {cfac_id}.\n\n"
                    f"📋 *Posibles causas:*\n"
                    f"• La factura no tiene comanda asociada\n"
                    f"• La comanda fue eliminada\n"
                    f"• La factura es de mostrador (sin comanda)"
                )

            if error:
                response += f"\n\n📋 *Error:* `{str(error)[:150]}`"

            await bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="Markdown"
            )

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        logger.error(f"Error en fallback de comanda: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error obteniendo datos de comanda*\n\n"
                 f"Por favor, verifique el ID e intente nuevamente.",
            parse_mode="Markdown"
        )


# ============================================================================
# AUDITORÍA POR RANGO - VERSIÓN CORREGIDA (CON STORE_CODE EN CALLBACKS)
# ============================================================================

async def handle_auditoria_rango(bot, chat_id: int, store_code: str):
    """Maneja auditoría por rango de fechas"""
    try:
        markup = types.InlineKeyboardMarkup(row_width=2)

        # Incluir store_code en cada callback
        buttons = [
            types.InlineKeyboardButton("📅 Día actual", callback_data=f"rango:hoy:{store_code}"),
            types.InlineKeyboardButton("⬅️ Día de ayer", callback_data=f"rango:ayer:{store_code}"),
            types.InlineKeyboardButton("2️⃣ Últimos 2 días", callback_data=f"rango:2dias:{store_code}"),
            types.InlineKeyboardButton("3️⃣ Últimos 3 días", callback_data=f"rango:3dias:{store_code}"),
            types.InlineKeyboardButton("🔍 Selección manual", callback_data=f"rango:manual:{store_code}"),
            types.InlineKeyboardButton("❌ Cancelar", callback_data=f"rango:cancelar:{store_code}")
        ]

        markup.row(buttons[0], buttons[1])
        markup.row(buttons[2], buttons[3])
        markup.row(buttons[4], buttons[5])

        await bot.send_message(
            chat_id=chat_id,
            text=f"📊 *AUDITORÍA POR RANGO - {store_code}*\n\n"
                 f"Seleccione el rango de fechas:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en auditoría por rango: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error iniciando auditoría:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )
        await show_action_buttons(bot, chat_id, store_code)


async def handle_rango_seleccion(bot, call, store_code: str, user_sessions):
    """Maneja la selección de rango de fechas - CON store_code desde callback"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    # Extraer store_code del callback si es necesario
    parts = call.data.split(':')
    if len(parts) >= 3:
        store_code = parts[2]

    fecha_fin = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if call.data.startswith('rango:hoy'):
        fecha_inicio = fecha_fin
        await mostrar_opciones_periodo(bot, chat_id, store_code, fecha_inicio, fecha_fin, user_sessions, user_id)

    elif call.data.startswith('rango:ayer'):
        fecha_inicio = fecha_fin - timedelta(days=1)
        fecha_fin = fecha_inicio
        await mostrar_opciones_periodo(bot, chat_id, store_code, fecha_inicio, fecha_fin, user_sessions, user_id)

    elif call.data.startswith('rango:2dias'):
        fecha_inicio = fecha_fin - timedelta(days=2)
        await mostrar_opciones_periodo(bot, chat_id, store_code, fecha_inicio, fecha_fin, user_sessions, user_id)

    elif call.data.startswith('rango:3dias'):
        fecha_inicio = fecha_fin - timedelta(days=3)
        await mostrar_opciones_periodo(bot, chat_id, store_code, fecha_inicio, fecha_fin, user_sessions, user_id)

    elif call.data.startswith('rango:manual'):
        if user_id in user_sessions:
            user_sessions[user_id]['state'] = 'WAITING_RANGO_FECHA_INICIO'
            user_sessions[user_id]['rango_store'] = store_code

        await bot.send_message(
            chat_id=chat_id,
            text=f"📅 *Ingrese la fecha de inicio* (formato YYYY-MM-DD):\n\n"
                 f"Ejemplo: `2026-03-19`",
            parse_mode="Markdown"
        )

    elif call.data.startswith('rango:cancelar'):
        await bot.send_message(
            chat_id=chat_id,
            text="❌ *Operación cancelada*",
            parse_mode="Markdown"
        )
        await show_action_buttons(bot, chat_id, store_code)

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass


async def mostrar_opciones_periodo(bot, chat_id: int, store_code: str, fecha_inicio, fecha_fin, user_sessions, user_id):
    """Muestra las opciones de período - CON store_code en callbacks"""
    # Guardar fechas en sesión (solo por si acaso, pero no serán necesarias)
    if user_id in user_sessions:
        user_sessions[user_id]['rango_fecha_inicio'] = fecha_inicio.date()
        user_sessions[user_id]['rango_fecha_fin'] = fecha_fin.date()
        user_sessions[user_id]['rango_store'] = store_code

    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')

    markup = types.InlineKeyboardMarkup(row_width=2)

    # Incluir store_code y fechas en los callbacks
    buttons = [
        types.InlineKeyboardButton("🌅 Mañana (01:00 - 15:59)",
                                 callback_data=f"periodo:manana:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("🌙 Tarde/Noche (16:00 - 23:59)",
                                 callback_data=f"periodo:tarde:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("📅 Todo el día (00:00 - 23:59)",
                                 callback_data=f"periodo:completo:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("❌ Cancelar",
                                 callback_data=f"periodo:cancelar:{store_code}")
    ]

    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2])
    markup.row(buttons[3])

    await bot.send_message(
        chat_id=chat_id,
        text=f"📅 *Rango seleccionado:* {fecha_inicio_str} al {fecha_fin_str}\n\n"
             f"⏰ *Seleccione el período del día:*",
        reply_markup=markup,
        parse_mode="Markdown"
    )


async def procesar_periodo_seleccion(bot, call, user_sessions):
    """Procesa la selección del período - USA DATOS DEL CALLBACK, no de la sesión"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Extraer datos del callback
    parts = call.data.split(':')
    if len(parts) < 3:
        await bot.answer_callback_query(call.id, "Error en formato de datos")
        return

    periodo = parts[1]
    store_code = parts[2]

    if periodo == "cancelar":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ *Operación cancelada*",
            parse_mode="Markdown"
        )
        await show_action_buttons(bot, chat_id, store_code)
        await bot.answer_callback_query(call.id)
        return

    # Obtener fechas del callback
    if len(parts) >= 5:
        fecha_inicio_str = parts[3]
        fecha_fin_str = parts[4]
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    else:
        await bot.answer_callback_query(call.id, "Error: Fechas no disponibles")
        return

    # Definir horas según período
    if periodo == "manana":
        hora_inicio = "01:00:00"
        hora_fin = "15:59:59"
        periodo_texto = "🌅 MAÑANA (01:00 - 15:59)"
        periodo_nombre = "manana"
    elif periodo == "tarde":
        hora_inicio = "16:00:00"
        hora_fin = "23:59:59"
        periodo_texto = "🌙 TARDE/NOCHE (16:00 - 23:59)"
        periodo_nombre = "tarde"
    else:  # completo
        hora_inicio = "00:00:00"
        hora_fin = "23:59:59"
        periodo_texto = "📅 TODO EL DÍA"
        periodo_nombre = "completo"

    # Mensaje de procesamiento
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"⏳ *Generando reporte Excel...*\n\n"
             f"📅 Fecha: {fecha_inicio} al {fecha_fin}\n"
             f"⏰ Período: {periodo_texto}\n"
             f"🏪 Tienda: {store_code}\n\n"
             f"Esto puede tomar unos segundos...",
        parse_mode="Markdown"
    )

    try:
        from reports.excel_reporter import generar_excel_auditoria
        from database.queries import consultar_pedidos_por_rango_simple

        datos = await consultar_pedidos_por_rango_simple(
            store_code=store_code,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )

        if not datos:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ *No se encontraron datos*\n\n"
                     f"Para: {fecha_inicio} al {fecha_fin}\n"
                     f"Período: {periodo_texto}",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            await bot.answer_callback_query(call.id)
            return

        archivo_excel = await generar_excel_auditoria(datos, store_code, fecha_inicio, hora_inicio)

        if not archivo_excel:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error generando archivo Excel*",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            await bot.answer_callback_query(call.id)
            return

        with open(archivo_excel, 'rb') as file:
            await bot.send_document(
                chat_id=chat_id,
                document=file,
                visible_file_name=f"auditoria_{store_code}_{fecha_inicio}_{periodo_nombre}.xlsx",
                caption=f"✅ *Reporte generado exitosamente*\n\n"
                        f"📊 *{len(datos)} registros*\n"
                        f"📅 {fecha_inicio} al {fecha_fin}\n"
                        f"⏰ {periodo_texto}\n"
                        f"🏪 {store_code}"
            )

        await show_action_buttons(bot, chat_id, store_code)

    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error generando reporte:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )
        await show_action_buttons(bot, chat_id, store_code)

    await bot.answer_callback_query(call.id)


async def procesar_hora_inicio_rango(bot, chat_id: int, texto: str, user_sessions):
    """Procesa la hora de inicio ingresada - RECIBE user_sessions como parámetro"""
    user_id = chat_id

    try:
        hora_valida = datetime.strptime(texto.strip(), "%H:%M").time()

        if user_id in user_sessions:
            user_sessions[user_id]['rango_hora_inicio'] = hora_valida
            user_sessions[user_id]['state'] = 'WAITING_RANGO_HORA_FIN'

        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Hora de inicio: {texto}\n\n"
                 f"⏰ *Ingrese la hora de fin* (formato HH:MM):\n\n"
                 f"Ejemplo: `23:00`",
            parse_mode="Markdown"
        )

    except ValueError:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Formato incorrecto*\n\n"
                 f"Use el formato HH:MM (ejemplo: 20:00)",
            parse_mode="Markdown"
        )


async def procesar_hora_fin_rango(bot, chat_id: int, texto: str, user_sessions):
    """Procesa la hora de fin - RECIBE user_sessions como parámetro"""
    user_id = chat_id

    try:
        hora_fin = datetime.strptime(texto.strip(), "%H:%M").time()

        if user_id not in user_sessions:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de sesión*\n\nPor favor, inicie nuevamente.",
                parse_mode="Markdown"
            )
            return

        session = user_sessions[user_id]
        hora_inicio = session.get('rango_hora_inicio')
        fecha_inicio = session.get('rango_fecha_inicio')
        fecha_fin = session.get('rango_fecha_fin')
        store_code = session.get('store_code')

        if not fecha_inicio or not fecha_fin:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error: Fechas no encontradas*\n\nPor favor, inicie nuevamente.",
                parse_mode="Markdown"
            )
            return

        if hora_fin <= hora_inicio:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *La hora de fin debe ser mayor que la de inicio*\n\n"
                     f"Hora inicio: {hora_inicio.strftime('%H:%M')}\n"
                     f"Intente nuevamente:",
                parse_mode="Markdown"
            )
            return

        progress_msg = await bot.send_message(
            chat_id=chat_id,
            text=f"⏳ *Generando reporte Excel...*\n\n"
                 f"📅 Fecha: {fecha_inicio} al {fecha_fin}\n"
                 f"⏰ Horas: {hora_inicio.strftime('%H:%M')} a {hora_fin.strftime('%H:%M')}\n"
                 f"🏪 Tienda: {store_code}\n\n"
                 f"Esto puede tomar unos segundos...",
            parse_mode="Markdown"
        )

        from reports.excel_reporter import generar_excel_auditoria
        from database.queries import consultar_pedidos_por_rango

        datos = await consultar_pedidos_por_rango(
            store_code=store_code,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )

        if not datos:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=f"⚠️ *No se encontraron datos*\n\n"
                     f"Para el rango: {fecha_inicio} {hora_inicio.strftime('%H:%M')} - {fecha_fin} {hora_fin.strftime('%H:%M')}",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        archivo_excel = await generar_excel_auditoria(datos, store_code, fecha_inicio, hora_inicio)

        with open(archivo_excel, 'rb') as file:
            await bot.send_document(
                chat_id=chat_id,
                document=file,
                visible_file_name=f"auditoria_{store_code}_{fecha_inicio}_{hora_inicio.strftime('%H-%M')}.xlsx",
                caption=f"✅ *Reporte generado exitosamente*\n\n"
                        f"📊 *{len(datos)} registros*\n"
                        f"📅 {fecha_inicio} {hora_inicio.strftime('%H:%M')} - {fecha_fin} {hora_fin.strftime('%H:%M')}\n"
                        f"🏪 {store_code}"
            )

        await bot.delete_message(chat_id=chat_id, message_id=progress_msg.message_id)

        session.pop('rango_fecha_inicio', None)
        session.pop('rango_fecha_fin', None)
        session.pop('rango_hora_inicio', None)
        session['state'] = 'in_menu'

        await show_action_buttons(bot, chat_id, store_code)

    except ValueError:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Formato incorrecto*\n\n"
                 f"Use el formato HH:MM (ejemplo: 23:00)",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error generando reporte:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )
        if store_code:
            await show_action_buttons(bot, chat_id, store_code)


async def procesar_fecha_manual_rango(bot, chat_id: int, texto: str, user_sessions):
    """Procesa la fecha manual ingresada y muestra opciones de período - VERSIÓN CORREGIDA"""
    user_id = chat_id

    try:
        # Validar formato de fecha
        fecha = datetime.strptime(texto.strip(), "%Y-%m-%d").date()

        if user_id in user_sessions:
            session = user_sessions[user_id]
            state = session.get('state')
            store_code = session.get('store_code')

            if state == 'WAITING_RANGO_FECHA_INICIO':
                session['rango_fecha_inicio'] = fecha
                session['state'] = 'WAITING_RANGO_FECHA_FIN'

                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Fecha inicio: {fecha}\n\n"
                         f"📅 *Ingrese la fecha de fin* (formato YYYY-MM-DD):\n\n"
                         f"Ejemplo: `2026-03-20`",
                    parse_mode="Markdown"
                )
                return

            elif state == 'WAITING_RANGO_FECHA_FIN':
                fecha_inicio = session.get('rango_fecha_inicio')

                if fecha < fecha_inicio:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ *La fecha de fin debe ser mayor o igual a la de inicio*\n\n"
                             f"Fecha inicio: {fecha_inicio}\n"
                             f"Intente nuevamente:",
                        parse_mode="Markdown"
                    )
                    return

                # Guardar fecha fin
                session['rango_fecha_fin'] = fecha

                # Limpiar estado ANTES de mostrar los botones
                session['state'] = 'in_menu'

                # Convertir fechas a objetos datetime
                fecha_inicio_obj = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
                fecha_fin_obj = datetime.strptime(str(fecha), '%Y-%m-%d')

                # Mostrar botones de período
                await mostrar_opciones_periodo_desde_manual(
                    bot, chat_id, store_code,
                    fecha_inicio_obj, fecha_fin_obj
                )
                return

    except ValueError:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Formato incorrecto*\n\n"
                 f"Use el formato YYYY-MM-DD (ejemplo: 2026-03-19)",
            parse_mode="Markdown"
        )
        return


async def mostrar_opciones_periodo_desde_manual(bot, chat_id: int, store_code: str, fecha_inicio, fecha_fin):
    """Muestra las opciones de período para fechas ingresadas manualmente - SIN DEPENDER DE SESIÓN"""

    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')

    markup = types.InlineKeyboardMarkup(row_width=2)

    # Incluir store_code y fechas en los callbacks
    buttons = [
        types.InlineKeyboardButton("🌅 Mañana (01:00 - 15:59)",
                                 callback_data=f"periodo:manana:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("🌙 Tarde/Noche (16:00 - 23:59)",
                                 callback_data=f"periodo:tarde:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("📅 Todo el día (00:00 - 23:59)",
                                 callback_data=f"periodo:completo:{store_code}:{fecha_inicio_str}:{fecha_fin_str}"),
        types.InlineKeyboardButton("❌ Cancelar",
                                 callback_data=f"periodo:cancelar:{store_code}")
    ]

    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2])
    markup.row(buttons[3])

    await bot.send_message(
        chat_id=chat_id,
        text=f"📅 *Rango seleccionado manualmente:* {fecha_inicio_str} al {fecha_fin_str}\n\n"
             f"⏰ *Seleccione el período del día:*",
        reply_markup=markup,
        parse_mode="Markdown"
    )


# ============================================================================
# HANDLERS EXISTENTES
# ============================================================================

async def handle_order_verification(bot, chat_id: int, store_code: str, order_number: str):
    """Maneja verificación de estado de orden"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔍 *Buscando orden {order_number}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        cursor = connection.cursor()

        try:
            query = QueryManager.get_order_status_query()
            cursor.execute(query, (order_number, order_number, order_number))
            results = cursor.fetchall()

            if results:
                row = results[0]
                response = f"""
✅ *ORDEN ENCONTRADA*

📦 *Código:* `{row[0]}`
📋 *Estado:* {row[1]}
🔢 *CFAC ID:* `{row[2] or 'N/A'}`
🚚 *Medio:* {row[3] or 'N/A'}
📅 *Fecha:* {row[4].strftime('%d/%m/%Y %H:%M') if row[4] else 'N/A'}
🏍️ *Motorizado:* {row[5] or 'N/A'}

🏪 *Tienda:* {store_code}
⏰ *Consulta:* {datetime.now().strftime('%H:%M:%S')}
                """
            else:
                response = f"""
❌ *ORDEN NO ENCONTRADA*

No se encontró la orden `{order_number}` en la tienda {store_code}.
                """

            await bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error en consulta: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error en la consulta:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en verificación: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error en el proceso:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def handle_order_audit(bot, chat_id: int, store_code: str, order_pattern: str):
    """Maneja auditoría de órdenes"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"📊 *Auditoría para patrón {order_pattern}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de conexión*",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        cursor = connection.cursor()

        try:
            query = QueryManager.get_order_audit_query()
            search_pattern = f"%{order_pattern}%"
            cursor.execute(query, (search_pattern,))
            results = cursor.fetchall()

            if results:
                response = f"""
📊 *AUDITORÍA DE ÓRDENES*

*Patrón buscado:* `{order_pattern}`
*Encontradas:* {len(results)} órdenes

*Resultados (máximo 10):*
"""
                for idx, row in enumerate(results[:10], 1):
                    response += f"\n{idx}. *Orden:* `{row[0]}`\n"
                    response += f"   • Estado: {row[1]}\n"
                    response += f"   • Fecha: {row[2].strftime('%d/%m/%Y %H:%M') if row[2] else 'N/A'}\n"
                    response += f"   • Motorizado: {row[3]}\n"

                if len(results) > 10:
                    response += f"\n... y {len(results) - 10} más"

                response += f"\n🏪 *Tienda:* {store_code}"
                response += f"\n⏰ *Consulta:* {datetime.now().strftime('%H:%M:%S')}"

            else:
                response = f"""
❌ *AUDITORÍA SIN RESULTADOS*

No se encontraron órdenes con el patrón: `{order_pattern}`
                """

            await bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error en auditoría: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error en auditoría:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en proceso de auditoría: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="❌ *Error en proceso*",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def handle_associated_code(bot, chat_id: int, store_code: str, cfac_id: str):
    """Maneja obtención de código asociado"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔗 *Buscando código asociado para {cfac_id}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de conexión*",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        cursor = connection.cursor()

        try:
            query = QueryManager.get_associated_code_query()
            cursor.execute(query, (cfac_id, cfac_id))
            results = cursor.fetchall()

            if results:
                response = f"""
🔗 *CÓDIGOS ASOCIADOS - {cfac_id}*

*Encontrados {len(results)} códigos:*
"""
                for idx, row in enumerate(results, 1):
                    response += f"{idx}. `{row[0]}`\n"

                response += f"\n🏪 *Tienda:* {store_code}"
                response += f"\n⏰ *Consulta:* {datetime.now().strftime('%H:%M:%S')}"

            else:
                response = f"""
❌ *SIN CÓDIGOS ASOCIADOS*

No se encontraron códigos asociados para: `{cfac_id}`
                """

            await bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error buscando código asociado: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Error buscando código asociado:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en proceso de código asociado: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="❌ *Error en proceso*",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def handle_reprint_3attempts(bot, chat_id: int, store_code: str, reprint_type: str, document_id: str):
    """Maneja re-impresión con 3 intentos"""
    try:
        if reprint_type not in ["factura", "nota_credito", "comanda"]:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Tipo de re-impresión no válido*",
                parse_mode="Markdown"
            )
            await show_action_buttons(bot, chat_id, store_code)
            return

        doc_names = {
            "factura": "Factura",
            "nota_credito": "Nota de Crédito",
            "comanda": "Comanda"
        }

        doc_name = doc_names.get(reprint_type, "Documento")

        await bot.send_message(
            chat_id=chat_id,
            text=f"🖨️ *Iniciando re-impresión de {doc_name} {document_id}...*\n\n*Tienda:* {store_code}",
            parse_mode="Markdown"
        )

        from core.print_service_3attempts import PrintService3Attempts

        print_service = PrintService3Attempts(store_code)
        result = await print_service.print_document(bot, chat_id, reprint_type, document_id)

        if result.get("success"):
            final_message = f"✅ *Re-impresión completada exitosamente*\n\n{result['message']}"
        else:
            final_message = f"❌ *Re-impresión fallida después de 3 intentos*\n\n{result['message']}"

        await bot.send_message(
            chat_id=chat_id,
            text=final_message,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en re-impresión: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error en re-impresión:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


# ============================================================================
# FUNCIONES PARA ASIGNACIÓN DE MOTORIZADO
# ============================================================================

# Diccionario global para almacenar estados de motorizado
motorizado_temp = {}


async def handle_motorizado_order_search(bot, chat_id: int, codigo_app: str, store_code: str, user_sessions: dict):
    """Busca la orden para asignar motorizado (PASO 1)"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔍 *Buscando orden {codigo_app}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        query = """
            SELECT 
                m.IDMotorolo,
                m.nombres,
                m.apellidos, 
                m.empresa_motorolo,
                m.TipoMotorolo,
                m.telefono,
                m.documento,
                ca.codigo_app,
                ca.estado as estado_app
            FROM Cabecera_App ca
            LEFT JOIN Motorolo m ON ca.IDMotorolo = m.IDMotorolo
            WHERE ca.codigo_app = ?
        """

        cursor.execute(query, (codigo_app,))
        orden = cursor.fetchone()
        cursor.close()

        if not orden:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Intentar con otro código", callback_data='asignar_motorizado'))
            markup.add(types.InlineKeyboardButton("🏠 Volver al menú", callback_data='menu_principal'))

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *ORDEN NO ENCONTRADA*\n\nNo se encontró la orden `{codigo_app}` en la tienda {store_code}.",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        # Guardar en sesión temporal motorizado_temp
        user_id = None
        for uid, session in user_sessions.items():
            if session.get('store_code') == store_code:
                user_id = uid
                break

        if user_id:
            motorizado_temp[user_id] = {
                'store_code': store_code,
                'codigo_app': codigo_app,
                'orden_data': orden,
                'step': 'waiting_document'
            }

        motorizado_nombre = f"{orden[1] or ''} {orden[2] or ''}".strip() or "No asignado"
        empresa = orden[3] or "N/A"
        tipo = orden[4] or "N/A"
        telefono = orden[5] or "No registrado"
        documento = orden[6] or "No registrado"
        estado_app = orden[8]

        mensaje = f"""
📋 *INFORMACIÓN DE LA ORDEN*

🔢 *Código:* `{codigo_app}`
📊 *Estado App:* {estado_app}

👤 *MOTORIZADO ACTUAL:*
• Nombre: {motorizado_nombre}
• Empresa: {empresa}
• Tipo: {tipo}
• Teléfono: {telefono}
• Documento: {documento}

{'=' * 30}

🚚 *PASO 2/3 - BUSCAR NUEVO MOTORIZADO*

📝 *Ingrese el número de documento del nuevo motorizado:*
        """

        await bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en handle_motorizado_order_search: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error:* `{str(e)[:200]}`",
            parse_mode="Markdown"
        )


async def handle_motorizado_document_search(bot, chat_id: int, documento: str, user_id: int, user_sessions: dict):
    """Busca motorizados por número de documento (PASO 2) - RECIBE user_id DIRECTAMENTE"""

    logger.info(f"handle_motorizado_document_search - user_id recibido: {user_id}")
    logger.info(f"motorizado_temp keys: {list(motorizado_temp.keys())}")

    if user_id not in motorizado_temp:
        logger.error(f"❌ Sesión expirada - user_id={user_id} no en motorizado_temp")
        await bot.send_message(
            chat_id=chat_id,
            text="❌ *Sesión expirada*\n\nPor favor inicie nuevamente desde el menú principal.",
            parse_mode="Markdown"
        )
        return

    store_code = motorizado_temp[user_id].get('store_code')
    codigo_app = motorizado_temp[user_id].get('codigo_app')

    if not store_code or not codigo_app:
        logger.error(f"❌ Datos incompletos en motorizado_temp para user_id {user_id}")
        await bot.send_message(
            chat_id=chat_id,
            text="❌ *Datos incompletos*\n\nPor favor inicie nuevamente desde el menú principal.",
            parse_mode="Markdown"
        )
        if user_id in motorizado_temp:
            del motorizado_temp[user_id]
        return

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔍 Buscando motorizados con documento que contenga `{documento}`...",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error de conexión*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()
        query = """
            SELECT IDMotorolo, nombres, apellidos, empresa_motorolo, 
                   TipoMotorolo, telefono, documento
            FROM motorolo 
            WHERE documento LIKE ?
            ORDER BY nombres, apellidos
        """
        cursor.execute(query, (f'%{documento}%',))
        motorizados = cursor.fetchall()
        cursor.close()

        if not motorizados:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Intentar con otro documento", callback_data='asignar_motorizado'))
            markup.add(types.InlineKeyboardButton("🏠 Volver al menú", callback_data='menu_principal'))

            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ *NO SE ENCONTRARON MOTORIZADOS*\n\nDocumento: `{documento}`\nOrden: `{codigo_app}`",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        motorizado_temp[user_id]['motorizados'] = motorizados
        motorizado_temp[user_id]['step'] = 'select_motorizado'

        # Guardar usando índice numérico para callback simple
        motorizado_temp[user_id]['temp_ids'] = {}

        markup = types.InlineKeyboardMarkup(row_width=1)

        for idx, m in enumerate(motorizados):
            id_motorolo = m[0]
            nombres = m[1] or ""
            apellidos = m[2] or ""
            empresa = m[3] or "N/A"
            tipo = m[4] or "N/A"
            nombre_completo = f"{nombres} {apellidos}".strip()
            btn_text = f"👤 {nombre_completo} - {empresa} ({tipo})"

            motorizado_temp[user_id]['temp_ids'][str(idx)] = {
                'id_motorolo': id_motorolo,
                'codigo_app': codigo_app
            }
            callback_data = f"ms_{idx}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))

        markup.add(types.InlineKeyboardButton("🔙 Cancelar", callback_data='menu_principal'))

        mensaje = f"✅ *MOTORIZADOS ENCONTRADOS:* {len(motorizados)}\n\n📦 *Orden:* `{codigo_app}`\n\nSeleccione el motorizado:"

        await bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode="Markdown",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Error en handle_motorizado_document_search: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error:* `{str(e)[:200]}`",
            parse_mode="Markdown"
        )


# ============================================================
# ✅ FUNCIÓN CORREGIDA - handle_motorizado_select_callback
# ============================================================
async def handle_motorizado_select_callback(call, idx: str):
    """Maneja la selección de motorizado (PASO 3 - Confirmación)"""
    from telebot import types

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_instance = get_bot()

    logger.info(f"=== handle_motorizado_select_callback ===")
    logger.info(f"user_id: {user_id}")
    logger.info(f"idx recibido: {idx}")
    logger.info(f"motorizado_temp keys: {list(motorizado_temp.keys())}")

    if user_id not in motorizado_temp:
        await bot_instance.edit_message_text(
            text="❌ *Sesión expirada*",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        return

    logger.info(f"temp_ids disponibles: {list(motorizado_temp[user_id].get('temp_ids', {}).keys())}")

    temp_data = motorizado_temp[user_id].get('temp_ids', {}).get(idx)
    if not temp_data:
        await bot_instance.edit_message_text(
            text="❌ *Error: No se encontró el motorizado*",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        return

    id_motorolo = temp_data['id_motorolo']
    codigo_app = temp_data['codigo_app']

    logger.info(f"id_motorolo encontrado: {id_motorolo}")
    logger.info(f"codigo_app: {codigo_app}")

    motorizados = motorizado_temp[user_id].get('motorizados', [])
    motorizado_seleccionado = None
    for m in motorizados:
        if m[0] == id_motorolo:
            motorizado_seleccionado = m
            break

    if not motorizado_seleccionado:
        await bot_instance.edit_message_text(
            text="❌ Error: No se encontró el motorizado seleccionado",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        return

    # ✅ GUARDAR EN LA SESIÓN CORRECTAMENTE
    motorizado_temp[user_id]['selected_motorizado'] = motorizado_seleccionado
    motorizado_temp[user_id]['selected_id_motorolo'] = id_motorolo
    # ✅ IMPORTANTE: Asegurar que store_code esté en la sesión
    if 'store_code' not in motorizado_temp[user_id]:
        motorizado_temp[user_id]['store_code'] = motorizado_temp[user_id].get('store_code')

    logger.info(f"✅ Motorizado guardado en sesión: {motorizado_seleccionado[1]} {motorizado_seleccionado[2]}")
    logger.info(f"✅ Sesión actual: {motorizado_temp[user_id].keys()}")

    nombres = motorizado_seleccionado[1] or ""
    apellidos = motorizado_seleccionado[2] or ""
    empresa = motorizado_seleccionado[3] or "N/A"
    tipo = motorizado_seleccionado[4] or "N/A"
    telefono = motorizado_seleccionado[5] or "N/A"
    documento = motorizado_seleccionado[6] or "N/A"

    orden_data = motorizado_temp[user_id].get('orden_data')
    motorizado_actual = "No asignado"
    if orden_data and orden_data[1]:
        motorizado_actual = f"{orden_data[1]} {orden_data[2]}".strip()

    mensaje = f"""
⚠️ *CONFIRMAR ASIGNACIÓN*

📦 *Orden:* `{codigo_app}`

👤 *Actual:* {motorizado_actual}

{'=' * 30}

👤 *Nuevo Motorizado:*
• {nombres} {apellidos}
• Documento: {documento}
• Empresa: {empresa}
• Tipo: {tipo}
• Teléfono: {telefono}

¿Confirmar asignación?
"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Sí", callback_data=f"mc_{id_motorolo}_{codigo_app}"),
        types.InlineKeyboardButton("❌ No", callback_data='menu_principal')
    )
    markup.add(types.InlineKeyboardButton("🔄 Buscar otro", callback_data='asignar_motorizado'))

    await bot_instance.edit_message_text(
        text=mensaje,
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )


# ============================================================
# ✅ FUNCIÓN CORREGIDA - handle_motorizado_confirm_callback
# ============================================================
async def handle_motorizado_confirm_callback(call, id_motorolo: str, codigo_app: str):
    """Ejecuta la asignación del motorizado (PASO 4 - Final)"""
    from telebot import types

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_instance = get_bot()

    logger.info(f"=== handle_motorizado_confirm_callback ===")
    logger.info(f"user_id: {user_id}")
    logger.info(f"id_motorolo: {id_motorolo}")
    logger.info(f"codigo_app: {codigo_app}")

    # Verificar sesión
    if user_id not in motorizado_temp:
        await bot_instance.edit_message_text(
            text="❌ *Sesión expirada*",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        return

    # ✅ OBTENER DATOS DE LA SESIÓN
    session = motorizado_temp[user_id]
    store_code = session.get('store_code')
    motorizado_seleccionado = session.get('selected_motorizado')

    logger.info(f"store_code: {store_code}")
    logger.info(f"motorizado_seleccionado: {motorizado_seleccionado}")

    if not store_code:
        await bot_instance.edit_message_text(
            text="❌ *Error: No se encontró la tienda*\n\n"
                 f"Datos en sesión: {list(session.keys())}",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        return

    if not motorizado_seleccionado:
        await bot_instance.edit_message_text(
            text="❌ *Error: No se encontró el motorizado seleccionado*\n\n"
                 f"Verifique que haya seleccionado un motorizado correctamente.",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        # Limpiar sesión si hay error
        if user_id in motorizado_temp:
            del motorizado_temp[user_id]
        return

    try:
        # Mostrar mensaje de procesamiento
        await bot_instance.edit_message_text(
            text="⏳ *Procesando asignación...*\n\n"
                 f"📦 Orden: `{codigo_app}`\n"
                 f"👤 Motorizado: `{motorizado_seleccionado[1]} {motorizado_seleccionado[2]}`",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )

        # ✅ CONEXIÓN DIRECTA A BD
        from core.os_detector import OSDetector

        os_type, _ = OSDetector.detect_os(store_code, quick=True)
        logger.info(f"Conectando a {store_code} con OS: {os_type}")

        connection = db_manager.get_connection(store_code, os_type)
        if not connection:
            await bot_instance.edit_message_text(
                text="❌ *Error de conexión a la base de datos*\n\n"
                     f"No se pudo conectar a la tienda {store_code}",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        # ✅ PASO 1: VERIFICAR QUE LA ORDEN EXISTE
        logger.info(f"Verificando orden: {codigo_app}")
        cursor.execute(
            "SELECT codigo_app, IDMotorolo FROM Cabecera_App WHERE codigo_app = ?",
            (codigo_app,)
        )
        orden_actual = cursor.fetchone()

        if not orden_actual:
            await bot_instance.edit_message_text(
                text=f"❌ *Error:* No se encontró la orden `{codigo_app}`\n\n"
                     f"Verifique el código e intente nuevamente.",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown"
            )
            cursor.close()
            connection.close()
            if user_id in motorizado_temp:
                del motorizado_temp[user_id]
            return

        logger.info(f"Orden encontrada: IDMotorolo actual = {orden_actual[1] if orden_actual[1] else 'NULL'}")

        # ✅ PASO 2: EJECUTAR UPDATE
        update_query = "UPDATE Cabecera_App SET IDMotorolo = ? WHERE codigo_app = ?"
        cursor.execute(update_query, (id_motorolo, codigo_app))
        connection.commit()

        filas_afectadas = cursor.rowcount
        logger.info(f"Filas afectadas: {filas_afectadas}")

        cursor.close()
        connection.close()

        # ✅ PASO 3: VERIFICAR RESULTADO
        if filas_afectadas > 0:
            nombres = motorizado_seleccionado[1] or ""
            apellidos = motorizado_seleccionado[2] or ""
            empresa = motorizado_seleccionado[3] or "N/A"
            telefono = motorizado_seleccionado[5] or "N/A"

            mensaje = f"""
✅ *¡MOTORIZADO ASIGNADO CON ÉXITO!*

📦 *Orden:* `{codigo_app}`
👤 *Motorizado:* {nombres} {apellidos}
🏢 *Empresa:* {empresa}
📞 *Teléfono:* {telefono}

✅ La orden ha sido actualizada correctamente.
"""
            usage_logger.log_action(
                user_id=user_id,
                username=call.from_user.username or call.from_user.first_name,
                action="MOTORIZADO_ASIGNADO",
                store=store_code,
                details=f"Orden: {codigo_app}, Motorizado ID: {id_motorolo}"
            )
        else:
            mensaje = f"""
⚠️ *NO SE PUDO ACTUALIZAR LA ORDEN*

📦 *Orden:* `{codigo_app}`
👤 *Motorizado:* {motorizado_seleccionado[1]} {motorizado_seleccionado[2]}

**Posibles causas:**
• La orden ya fue entregada
• La orden no existe en la base de datos
• El ID del motorizado no es válido

Verifique el estado de la orden e intente nuevamente.
"""

        # Limpiar sesión temporal
        if user_id in motorizado_temp:
            del motorizado_temp[user_id]

        # Mostrar mensaje final con opciones
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚚 Nueva Asignación", callback_data='asignar_motorizado'),
            types.InlineKeyboardButton("🏠 Menú Principal", callback_data='menu_principal')
        )

        await bot_instance.edit_message_text(
            text=mensaje,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Error en handle_motorizado_confirm_callback: {e}", exc_info=True)
        error_msg = str(e)[:200]
        await bot_instance.edit_message_text(
            text=f"❌ *Error al asignar motorizado:*\n\n"
                 f"`{error_msg}`\n\n"
                 f"Por favor, verifique los logs para más detalles.",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        # Limpiar sesión en caso de error
        if user_id in motorizado_temp:
            del motorizado_temp[user_id]