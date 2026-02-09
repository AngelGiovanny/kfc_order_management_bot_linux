"""
Handlers combinados para el menú - Versión telebot - SIN BOTÓN 4-PASOS
VERSIÓN MEJORADA CON ESTRATEGIA DUAL LINUX/WINDOWS
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from telebot import types
from config.database import db_manager
from database.queries import QueryManager
from utils.logger import get_logger, usage_logger

logger = get_logger(__name__)


def validate_store_code(store_code: str) -> bool:
    """Valida el código de tienda K001 a K999"""
    store_code = store_code.upper().strip()

    if not store_code.startswith('K'):
        return False

    try:
        store_num = int(store_code[1:])
        return 1 <= store_num <= 999
    except:
        return False


async def show_main_menu(bot, chat_id: int, store_code: str):
    """Muestra el menú principal completo - SIN BOTÓN FLUJO 4-PASOS"""

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
        types.KeyboardButton("🔧 Diagnóstico"),
        types.KeyboardButton("🔄 Cambiar tienda"),
        types.KeyboardButton("❌ Salir")
    ]

    # Organizar botones
    markup.row(buttons[0], buttons[1])  # Verificar, Auditoría
    markup.row(buttons[2], buttons[3])  # Factura, Nota crédito
    markup.row(buttons[4], buttons[5])  # Comanda, Código asociado
    markup.row(buttons[6], buttons[7])  # Re-Impresión, Diagnóstico
    markup.row(buttons[8], buttons[9])  # Cambiar tienda, Salir

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
        types.KeyboardButton("🔧 Diagnóstico"),
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
    """Maneja generación de imagen de factura o nota de crédito - VERSIÓN MEJORADA"""
    try:
        doc_type = "Nota de Crédito" if is_credit_note else "Factura"

        # Mensaje inicial
        await bot.send_message(
            chat_id=chat_id,
            text=f"🖼️ *Generando {doc_type} {cfac_id}...*\n\n"
                 f"🏪 Tienda: {store_code}\n"
                 f"⏳ Esto puede tomar unos segundos...",
            parse_mode="Markdown"
        )

        # Registrar uso
        usage_logger.log_action(
            user_id=None,
            username="",
            action=f"{doc_type.upper().replace(' ', '_')}_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {cfac_id}"
        )

        # Usar el image_service mejorado
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
            # Generar imagen
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
                # Enviar imagen generada
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
                    # Si hay error enviando la foto, enviar mensaje de éxito
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
                # Intentar obtener datos básicos como fallback
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
    """Muestra datos de factura como fallback cuando no se puede generar imagen"""
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
    """Maneja generación de comanda - VERSIÓN MEJORADA"""
    try:
        # Mensaje inicial
        await bot.send_message(
            chat_id=chat_id,
            text=f"🍗 *Buscando comanda para factura {cfac_id}...*\n\n"
                 f"🏪 Tienda: {store_code}\n"
                 f"⏳ Esto puede tomar unos segundos...",
            parse_mode="Markdown"
        )

        # Registrar uso
        usage_logger.log_action(
            user_id=None,
            username="",
            action="COMANDA_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {cfac_id}"
        )

        # Usar el image_service mejorado
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
            # Generar imagen de comanda
            image_bytes = await image_service.generate_comanda_image(
                store_code=store_code,
                invoice_id=cfac_id
            )

            if image_bytes:
                # Enviar imagen generada
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
                # Intentar obtener datos básicos como fallback
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
            # Buscar comanda asociada
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

                # Obtener items de la comanda
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
# HANDLERS EXISTENTES (SOLO CAMBIO EN handle_order_verification)
# ============================================================================

async def handle_order_verification(bot, chat_id: int, store_code: str, order_number: str):
    """Maneja verificación de estado de orden - CON pickup_cabecera_pedidos"""
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
            # SOLO CAMBIO: Usar la nueva query que incluye pickup_cabecera_pedidos
            query = QueryManager.get_order_status_query()

            # IMPORTANTE: Ahora necesita 3 parámetros en lugar de 2
            # (Cabecera_App, kiosko_cabecera_pedidos, pickup_cabecera_pedidos)
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


async def handle_diagnostic(bot, chat_id: int, store_code: str):
    """Maneja diagnóstico completo del sistema"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔬 *INICIANDO DIAGNÓSTICO COMPLETO - {store_code}*",
            parse_mode="Markdown"
        )

        # Obtener información de conexión
        connection_info = db_manager.get_connection_info(store_code)

        # Construir diagnóstico
        diagnostic_text = f"""
🔍 *DIAGNÓSTICO DEL SISTEMA - {store_code}*

📊 *INFORMACIÓN GENERAL:*
• Base de datos: `{connection_info['database_name']}`
• Sistema recomendado: {connection_info['recommended_os'].upper() if connection_info['recommended_os'] else 'NO DISPONIBLE'}

🔌 *PRUEBAS DE CONEXIÓN:*
"""

        # Linux
        linux_test = connection_info['linux_test']
        linux_status = "✅ CONECTADO" if linux_test['success'] else "❌ FALLIDO"
        diagnostic_text += f"• Linux: {linux_status}\n"

        # Windows
        windows_test = connection_info['windows_test']
        windows_status = "✅ CONECTADO" if windows_test['success'] else "❌ FALLIDO"
        diagnostic_text += f"• Windows: {windows_status}\n"

        # Servicios
        try:
            from core.image_service import image_service
            diagnostic_text += f"\n🖼️ *SERVICIO DE IMÁGENES:*\n"
            diagnostic_text += f"• Estado: {'✅ DISPONIBLE' if image_service.is_available() else '❌ NO DISPONIBLE'}\n"
            diagnostic_text += f"• Sistema: {image_service.system}\n"
            diagnostic_text += f"• Selenium: {'✅ DISPONIBLE' if image_service.is_selenium_available() else '❌ NO DISPONIBLE'}\n"
        except Exception as img_error:
            diagnostic_text += f"\n🖼️ *SERVICIO DE IMÁGENES:*\n• Estado: ⚠️ NO VERIFICADO\n"

        diagnostic_text += f"\n🕒 *Diagnóstico realizado:* {datetime.now().strftime('%H:%M:%S')}"

        await bot.send_message(
            chat_id=chat_id,
            text=diagnostic_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}")
        error_msg = str(e).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error en diagnóstico:*\n`{error_msg[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(bot, chat_id, store_code)


async def handle_reprint_3attempts(bot, chat_id: int, store_code: str, reprint_type: str, document_id: str):
    """Maneja re-impresión con 3 intentos"""
    try:
        # Validar tipo
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

        # Importar el servicio de impresión dinámicamente
        from core.print_service_3attempts import PrintService3Attempts

        # Crear servicio y ejecutar
        print_service = PrintService3Attempts(store_code)
        result = await print_service.print_document(bot, chat_id, reprint_type, document_id)

        # Mostrar resultado final
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