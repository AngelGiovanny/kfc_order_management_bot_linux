"""
main.py - Bot principal de gestión KFC
"""

import asyncio
import os
import sys
from datetime import datetime
import traceback

import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import BOT_TOKEN
from utils.logger import get_logger, usage_logger
from core.os_detector import OSDetector
from config.database import db_manager
from handlers.menu_handler_combined import (
    show_main_menu, show_action_buttons, handle_order_verification,
    handle_order_audit, handle_invoice_image, handle_comanda,
    handle_associated_code, handle_auditoria_rango,
    validate_store_code, handle_reprint_3attempts,
    handle_rango_seleccion, procesar_hora_inicio_rango,
    procesar_hora_fin_rango, procesar_fecha_manual_rango,
    procesar_periodo_seleccion
)
from handlers.report_handler import handle_report_command
from core.image_service import image_service

logger = get_logger("main_bot")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN no configurado")
    sys.exit(1)

bot = AsyncTeleBot(BOT_TOKEN)
user_sessions = {}


class UserState:
    WAITING_STORE = "waiting_store"
    WAITING_ORDER = "waiting_order"
    WAITING_AUDIT = "waiting_audit"
    WAITING_INVOICE = "waiting_invoice"
    WAITING_CREDIT_NOTE = "waiting_credit_note"
    WAITING_COMANDA = "waiting_comanda"
    WAITING_ASSOCIATED_CODE = "waiting_associated_code"
    WAITING_REPRINT = "waiting_reprint"
    WAITING_REPRINT_TYPE = "waiting_reprint_type"
    IN_MENU = "in_menu"
    DIAGNOSTIC = "diagnostic"
    WAITING_RANGO_FECHA_INICIO = "waiting_rango_fecha_inicio"
    WAITING_RANGO_FECHA_FIN = "waiting_rango_fecha_fin"
    WAITING_RANGO_HORA_INICIO = "waiting_rango_hora_inicio"
    WAITING_RANGO_HORA_FIN = "waiting_rango_hora_fin"


async def handle_store_setup(bot, chat_id: int, store_code: str, user_id: int, username: str):
    """Maneja la configuración inicial de una tienda"""
    try:
        os_type, address = OSDetector.detect_os(store_code, quick=True)
        connection_info = db_manager.get_connection_info(store_code)

        if connection_info['recommended_os']:
            usage_logger.log_action(
                user_id=user_id,
                username=username,
                action="STORE_SETUP_SUCCESS",
                store=store_code,
                details=f"Sistema: {os_type}, Dirección: {address}, BD: {connection_info['database_name']}"
            )
            return connection_info['recommended_os']
        else:
            usage_logger.log_action(
                user_id=user_id,
                username=username,
                action="STORE_SETUP_FAILED",
                store=store_code,
                details=f"Error: No se pudo conectar. OS detectado: {os_type}"
            )
            return None

    except Exception as e:
        logger.error(f"Error en setup de tienda: {e}")
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="STORE_SETUP_ERROR",
            store=store_code,
            details=f"Exception: {str(e)[:100]}"
        )
        return None


async def show_reprint_menu(bot, chat_id: int, store_code: str):
    """Muestra menú de re-impresión"""
    menu_text = f"🏪 *Tienda:* {store_code}\n\n🖨️ *SELECCIONE TIPO DE RE-IMPRESIÓN:*"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton("📄 Re-imprimir Factura"),
        types.KeyboardButton("📋 Re-imprimir Nota Crédito"),
        types.KeyboardButton("🍗 Re-imprimir Comanda"),
        types.KeyboardButton("🔙 Volver al menú")
    ]
    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2], buttons[3])
    await bot.send_message(
        chat_id=chat_id,
        text=menu_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )


def validate_cfac_id(cfac_id: str) -> bool:
    """Valida si un CFAC_ID tiene formato válido"""
    if not cfac_id:
        return False
    if len(cfac_id) < 10:
        return False
    if not cfac_id.startswith('K'):
        return False
    if cfac_id[4] not in ['F', 'N']:
        return False
    return True


@bot.message_handler(commands=['start', 'inicio', 'help', 'ayuda'])
async def start_command(message):
    """Maneja el comando /start"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name

    logger.info(f"Comando /start de usuario {user_id} ({username})")

    usage_logger.log_action(
        user_id=user_id,
        username=username,
        action="START_COMMAND"
    )

    if user_id in user_sessions:
        del user_sessions[user_id]

    user_sessions[user_id] = {
        'state': UserState.WAITING_STORE,
        'store_code': None,
        'last_activity': datetime.now(),
        'username': username
    }

    welcome_text = """
🍗 *SISTEMA KFC - GESTIÓN DE ÓRDENES*

📋 *Por favor, ingrese el código de la tienda:*

• Formato: K seguido de 3 números
• Ejemplo: K025, K180, K004

⚠️ _Puede tomar unos segundos la primera vez_
    """

    await bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['reportes'])
async def report_command(message):
    """Maneja el comando /reportes"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    logger.info(f"Comando /reportes de usuario {user_id} ({username})")
    usage_logger.log_action(
        user_id=user_id,
        username=username,
        action="REPORT_COMMAND"
    )
    await handle_report_command(bot, message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('periodo:'))
async def handle_periodo_callback(call):
    """Maneja la selección de período"""
    await procesar_periodo_seleccion(bot, call, user_sessions)


@bot.callback_query_handler(func=lambda call: True)
async def handle_callback_query(call):
    """Maneja las consultas de callback generales"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    logger.info(f"Callback general de usuario {user_id}: {call.data}")

    session = user_sessions.get(user_id)
    if not session:
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ *Sesión no encontrada*\n\nUse /start para iniciar",
            parse_mode="Markdown"
        )
        await bot.answer_callback_query(call.id)
        return

    store_code = session.get('store_code')

    if call.data.startswith('rango:'):
        await handle_rango_seleccion(bot, call, store_code, user_sessions)

    await bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: True)
async def handle_all_messages(message):
    """Maneja todos los mensajes"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text.strip()

    logger.info(f"Mensaje de {user_id} ({username}): {text}")

    session = user_sessions.get(user_id)
    if not session:
        await start_command(message)
        return

    current_state = session.get('state')
    store_code = session.get('store_code')

    session['last_activity'] = datetime.now()

    # ============================================
    # ESTADOS DE AUDITORÍA POR RANGO (DEBEN IR PRIMERO)
    # ============================================
    if current_state == UserState.WAITING_RANGO_FECHA_INICIO:
        logger.info(f"Procesando fecha inicio manual: {text}")
        await procesar_fecha_manual_rango(bot, chat_id, text, user_sessions)
        return

    if current_state == UserState.WAITING_RANGO_FECHA_FIN:
        logger.info(f"Procesando fecha fin manual: {text}")
        await procesar_fecha_manual_rango(bot, chat_id, text, user_sessions)
        return

    if current_state == UserState.WAITING_RANGO_HORA_INICIO:
        logger.info(f"Procesando hora inicio: {text}")
        await procesar_hora_inicio_rango(bot, chat_id, text, user_sessions)
        return

    if current_state == UserState.WAITING_RANGO_HORA_FIN:
        logger.info(f"Procesando hora fin: {text}")
        await procesar_hora_fin_rango(bot, chat_id, text, user_sessions)
        return

    # ============================================
    # WAITING_STORE
    # ============================================
    if current_state == UserState.WAITING_STORE:
        if validate_store_code(text):
            store_code = text.upper()
            session['store_code'] = store_code

            setup_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Configurando tienda {store_code}...",
                parse_mode="Markdown"
            )

            recommended_os = await handle_store_setup(bot, chat_id, store_code, user_id, username)

            if recommended_os:
                await bot.delete_message(chat_id=chat_id, message_id=setup_msg.message_id)
                session['state'] = UserState.IN_MENU
                await show_main_menu(bot, chat_id, store_code)
            else:
                markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                markup.row(
                    types.KeyboardButton("🔧 Reintentar"),
                    types.KeyboardButton("🔄 Otra tienda")
                )
                markup.row(types.KeyboardButton("❌ Cancelar"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ *Problemas con {store_code}*\n\n¿Qué desea hacer?",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                session['state'] = UserState.DIAGNOSTIC
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Código inválido*\n\nFormato: K001 a K999\nEjemplo: K025, K004",
                parse_mode="Markdown"
            )
        return

    # ============================================
    # IN_MENU
    # ============================================
    if current_state == UserState.IN_MENU:
        if not store_code:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ *No hay tienda configurada*\n\nUse /start",
                parse_mode="Markdown"
            )
            return

        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action=f"MENU_{text.upper().replace(' ', '_')}",
            store=store_code
        )

        if text == "🔍 Verificar orden":
            session['state'] = UserState.WAITING_ORDER
            await bot.send_message(
                chat_id=chat_id,
                text="📝 *Ingrese el número de orden (codigo_app):*",
                parse_mode="Markdown"
            )

        elif text == "📊 Auditoría":
            session['state'] = UserState.WAITING_AUDIT
            await bot.send_message(
                chat_id=chat_id,
                text="🔎 *Ingrese el código o patrón de orden a auditar:*",
                parse_mode="Markdown"
            )

        elif text == "🖼️ Factura imagen":
            session['state'] = UserState.WAITING_INVOICE
            await bot.send_message(
                chat_id=chat_id,
                text="📄 Ingrese el CFAC_ID para obtener la imagen:",
                parse_mode="Markdown"
            )

        elif text == "📄 Nota crédito":
            session['state'] = UserState.WAITING_CREDIT_NOTE
            await bot.send_message(
                chat_id=chat_id,
                text="📝 Ingrese el CFAC_ID para obtener la imagen:",
                parse_mode="Markdown"
            )

        elif text == "🍗 Comanda":
            session['state'] = UserState.WAITING_COMANDA
            await bot.send_message(
                chat_id=chat_id,
                text="🍟 Ingrese el CFAC_ID para obtener la imagen:",
                parse_mode="Markdown"
            )

        elif text == "🔗 Código asociado":
            session['state'] = UserState.WAITING_ASSOCIATED_CODE
            await bot.send_message(
                chat_id=chat_id,
                text="🔢 *Ingrese el CFAC_ID para obtener código asociado:*",
                parse_mode="Markdown"
            )

        elif text == "🖨️ Re-Impresión":
            session['state'] = UserState.WAITING_REPRINT_TYPE
            await show_reprint_menu(bot, chat_id, store_code)

        elif text == "📅 Auditoría por Rango":
            await handle_auditoria_rango(bot, chat_id, store_code)

        elif text == "🔄 Cambiar tienda":
            session['state'] = UserState.WAITING_STORE
            session['store_code'] = None
            await bot.send_message(
                chat_id=chat_id,
                text="🏪 *Ingrese el código de la nueva tienda:*",
                parse_mode="Markdown"
            )

        elif text == "❌ Salir":
            if user_id in user_sessions:
                del user_sessions[user_id]
            await bot.send_message(
                chat_id=chat_id,
                text="✅ *SESIÓN FINALIZADA*\n\nGracias por usar el sistema KFC.\n\nPara una nueva consulta, envíe /start",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )

        elif text in ["🔍 Nueva consulta", "🏠 Menú principal"]:
            session['state'] = UserState.IN_MENU
            await show_main_menu(bot, chat_id, store_code)

        else:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ *Opción no reconocida*\n\nSeleccione una opción del menú.",
                parse_mode="Markdown"
            )
        return

    # ============================================
    # DIAGNOSTIC
    # ============================================
    if current_state == UserState.DIAGNOSTIC:
        if text == "🔧 Reintentar":
            if store_code:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🔍 Reintentando conexión con {store_code}...",
                    parse_mode="Markdown"
                )
                recommended_os = await handle_store_setup(bot, chat_id, store_code, user_id, username)
                if recommended_os:
                    session['state'] = UserState.IN_MENU
                    await show_main_menu(bot, chat_id, store_code)
        elif text == "🔄 Otra tienda":
            session['state'] = UserState.WAITING_STORE
            session['store_code'] = None
            await bot.send_message(
                chat_id=chat_id,
                text="🏪 *Ingrese el código de la nueva tienda:*",
                parse_mode="Markdown"
            )
        elif text == "❌ Cancelar":
            if user_id in user_sessions:
                del user_sessions[user_id]
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Operación cancelada*\n\nUse /start para comenzar de nuevo.",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
        return

    # ============================================
    # WAITING_ORDER
    # ============================================
    if current_state == UserState.WAITING_ORDER:
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ORDER_VERIFICATION",
            store=store_code,
            details=f"Orden: {text}"
        )
        await handle_order_verification(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_AUDIT
    # ============================================
    if current_state == UserState.WAITING_AUDIT:
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ORDER_AUDIT",
            store=store_code,
            details=f"Patrón: {text}"
        )
        await handle_order_audit(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_INVOICE
    # ============================================
    if current_state == UserState.WAITING_INVOICE:
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX\nEjemplo: K096F001779631",
                parse_mode="Markdown"
            )
            return
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="INVOICE_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )
        await handle_invoice_image(bot, chat_id, store_code, text, is_credit_note=False)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_CREDIT_NOTE
    # ============================================
    if current_state == UserState.WAITING_CREDIT_NOTE:
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXNXXXXXXXXXX\nEjemplo: K096N000123456",
                parse_mode="Markdown"
            )
            return
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="CREDIT_NOTE_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )
        await handle_invoice_image(bot, chat_id, store_code, text, is_credit_note=True)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_COMANDA
    # ============================================
    if current_state == UserState.WAITING_COMANDA:
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX\nEjemplo: K096F001779631",
                parse_mode="Markdown"
            )
            return
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="COMANDA_SEARCH",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )
        await handle_comanda(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_ASSOCIATED_CODE
    # ============================================
    if current_state == UserState.WAITING_ASSOCIATED_CODE:
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX o KXXXNXXXXXXXXXX",
                parse_mode="Markdown"
            )
            return
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ASSOCIATED_CODE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )
        await handle_associated_code(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU
        return

    # ============================================
    # WAITING_REPRINT_TYPE
    # ============================================
    if current_state == UserState.WAITING_REPRINT_TYPE:
        if text == "📄 Re-imprimir Factura":
            session['state'] = UserState.WAITING_REPRINT
            session['reprint_type'] = "factura"
            await bot.send_message(
                chat_id=chat_id,
                text="🖨️ *Ingrese el CFAC_ID para re-imprimir factura:*",
                parse_mode="Markdown"
            )
        elif text == "📋 Re-imprimir Nota Crédito":
            session['state'] = UserState.WAITING_REPRINT
            session['reprint_type'] = "nota_credito"
            await bot.send_message(
                chat_id=chat_id,
                text="🖨️ *Ingrese el CFAC_ID para re-imprimir nota de crédito:*",
                parse_mode="Markdown"
            )
        elif text == "🍗 Re-imprimir Comanda":
            session['state'] = UserState.WAITING_REPRINT
            session['reprint_type'] = "comanda"
            await bot.send_message(
                chat_id=chat_id,
                text="🖨️ *Ingrese el CFAC_ID para re-imprimir comanda:*",
                parse_mode="Markdown"
            )
        elif text == "🔙 Volver al menú":
            session['state'] = UserState.IN_MENU
            await show_main_menu(bot, chat_id, store_code)
        return

    # ============================================
    # WAITING_REPRINT
    # ============================================
    if current_state == UserState.WAITING_REPRINT:
        reprint_type = session.get('reprint_type', 'factura')
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX para facturas/comandas\nKXXXNXXXXXXXXXX para notas de crédito",
                parse_mode="Markdown"
            )
            return
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action=f"REPRINT_{reprint_type.upper()}",
            store=store_code,
            details=f"Documento: {text}"
        )
        await handle_reprint_3attempts(bot, chat_id, store_code, reprint_type, text)
        session['state'] = UserState.IN_MENU
        if 'reprint_type' in session:
            del session['reprint_type']
        return

    # ============================================
    # ESTADO NO MANEJADO
    # ============================================
    session['state'] = UserState.WAITING_STORE
    await bot.send_message(
        chat_id=chat_id,
        text="⚠️ *Estado no reconocido*\n\nPor favor ingrese el código de tienda:",
        parse_mode="Markdown"
    )


async def main():
    """Función principal"""
    logger.info("🤖 Iniciando KFC Bot")
    logger.info(f"🕒 Hora de inicio: {datetime.now()}")

    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")

        await bot.delete_webhook()
        await bot.polling(none_stop=True, interval=1, timeout=30)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        traceback.print_exc()
    finally:
        db_manager.close_all_connections()
        image_service.close_selenium()
        logger.info("👋 Bot detenido")


if __name__ == "__main__":
    asyncio.run(main())