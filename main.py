"""
main.py - Bot principal de gestión KFC - SIN FLUJO 4-PASOS EXPLÍCITO
Módulo principal que maneja el bot de Telegram
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
import traceback

import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import BOT_TOKEN
from utils.logger import get_logger, usage_logger
from core.os_detector import OSDetector
from config.database import db_manager

# Importar handlers
from handlers.menu_handler_combined import (
    show_main_menu, show_action_buttons, handle_order_verification,
    handle_order_audit, handle_invoice_image, handle_comanda,
    handle_associated_code, handle_diagnostic,
    validate_store_code, handle_reprint_3attempts
)

# Importar handler de reportes
from handlers.report_handler import handle_report_command

# Importar image_service para usar el flujo 4-pasos interno
from core.image_service import image_service

# Configurar logger
logger = get_logger("main_bot")

# Verificar token
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN no configurado")
    sys.exit(1)

# Inicializar bot
bot = AsyncTeleBot(BOT_TOKEN)

# Estados y sesiones
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
    # NOTA: Se han eliminado los estados WAITING_*_4STEP


async def handle_store_setup(bot, chat_id: int, store_code: str, user_id: int, username: str):
    """Maneja la configuración inicial de una tienda - SIN MENSAJES DUPLICADOS"""
    try:
        # NO enviar mensaje aquí, ya se envía desde WAITING_STORE

        # Detección del sistema operativo
        os_type, address = OSDetector.detect_os(store_code, quick=True)

        # Probar conexión con el OS detectado
        connection_info = db_manager.get_connection_info(store_code)

        # Mensaje según resultado - NO enviar mensaje de éxito aquí
        if connection_info['recommended_os']:
            # Solo registrar en logs
            usage_logger.log_action(
                user_id=user_id,
                username=username,
                action="STORE_SETUP_SUCCESS",
                store=store_code,
                details=f"Sistema: {os_type}, Dirección: {address}, BD: {connection_info['database_name']}"
            )

            return connection_info['recommended_os']
        else:
            # Si no hay conexión, solo registrar error
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

        # Registrar error
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


async def show_action_menu_after_image(bot, chat_id: int, store_code: str):
    """Muestra menú de acción después de generar una imagen"""
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


def validate_cfac_id(cfac_id: str) -> bool:
    """Valida si un CFAC_ID tiene formato válido"""
    if not cfac_id:
        return False

    # Formato esperado: KXXXFXXXXXXXXXX o KXXXNXXXXXXXXXX
    if len(cfac_id) < 10:
        return False

    # Debe empezar con K
    if not cfac_id.startswith('K'):
        return False

    # Debe tener F o N después de los 4 primeros caracteres
    if cfac_id[4] not in ['F', 'N']:
        return False

    return True


@bot.message_handler(commands=['start', 'inicio', 'help', 'ayuda'])
async def start_command(message):
    """Maneja el comando /start simplificado"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name

    logger.info(f"Comando /start de usuario {user_id} ({username})")

    # Registrar en logs
    usage_logger.log_action(
        user_id=user_id,
        username=username,
        action="START_COMMAND"
    )

    # Limpiar sesión anterior
    if user_id in user_sessions:
        del user_sessions[user_id]

    # Inicializar nueva sesión
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

    # Registrar en logs
    usage_logger.log_action(
        user_id=user_id,
        username=username,
        action="REPORT_COMMAND"
    )

    await handle_report_command(bot, message)


@bot.message_handler(func=lambda message: True)
async def handle_all_messages(message):
    """Maneja todos los mensajes"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text.strip()

    logger.info(f"Mensaje de {user_id} ({username}): {text}")

    # Obtener sesión
    session = user_sessions.get(user_id)
    if not session:
        await start_command(message)
        return

    current_state = session.get('state')
    store_code = session.get('store_code')

    # Actualizar actividad
    session['last_activity'] = datetime.now()

    # Lista de botones del menú actualizada (sin opciones 4-pasos)
    MENU_BUTTONS = [
        "🔍 Verificar orden", "📊 Auditoría", "🖼️ Factura imagen", "📄 Nota crédito",
        "🍗 Comanda", "🔗 Código asociado", "🖨️ Re-Impresión",
        "🔧 Diagnóstico", "🔄 Cambiar tienda", "❌ Salir", "🔍 Nueva consulta",
        "🏠 Menú principal", "🖼️ Factura imagen", "🍗 Comanda", "📄 Nota crédito",
        "📄 Re-imprimir Factura", "📋 Re-imprimir Nota Crédito", "🍗 Re-imprimir Comanda",
        "🔙 Volver al menú"
    ]

    # Manejar según estado
    if current_state == UserState.WAITING_STORE:
        if validate_store_code(text):
            store_code = text.upper()
            session['store_code'] = store_code

            # Enviar mensaje inicial de configuración SOLO AQUÍ
            setup_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Configurando tienda {store_code}...",
                parse_mode="Markdown"
            )

            # Configurar tienda con detección
            recommended_os = await handle_store_setup(bot, chat_id, store_code, user_id, username)

            if recommended_os:
                # Eliminar mensaje de configuración
                await bot.delete_message(chat_id=chat_id, message_id=setup_msg.message_id)

                session['state'] = UserState.IN_MENU
                # Mostrar directamente el menú principal
                await show_main_menu(bot, chat_id, store_code)
            else:
                # Mostrar opciones de error
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

    elif current_state == UserState.IN_MENU:
        if not store_code:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ *No hay tienda configurada*\n\nUse /start",
                parse_mode="Markdown"
            )
            return

        # Registrar acción
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action=f"MENU_{text.upper().replace(' ', '_')}",
            store=store_code
        )

        # Procesar selección del menú
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

        elif text == "🔧 Diagnóstico":
            await handle_diagnostic(bot, chat_id, store_code)

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

        # MANEJO DE BOTONES DEL MENÚ DE ACCIÓN (compatibilidad)
        elif text in ["🔍 Nueva consulta", "🏠 Menú principal"]:
            session['state'] = UserState.IN_MENU
            await show_main_menu(bot, chat_id, store_code)

        else:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ *Opción no reconocida*\n\nSeleccione una opción del menú.",
                parse_mode="Markdown"
            )

    elif current_state == UserState.DIAGNOSTIC:
        if text == "🔧 Reintentar":
            if store_code:
                # Enviar mensaje de reintento
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

    elif current_state == UserState.WAITING_ORDER:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Registrar consulta de orden
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ORDER_VERIFICATION",
            store=store_code,
            details=f"Orden: {text}"
        )

        await handle_order_verification(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_AUDIT:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Registrar auditoría
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ORDER_AUDIT",
            store=store_code,
            details=f"Patrón: {text}"
        )

        await handle_order_audit(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_INVOICE:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Validar formato del CFAC_ID
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX\nEjemplo: K096F001779631",
                parse_mode="Markdown"
            )
            # Mantener en el mismo estado para que reintente
            return

        # Registrar generación de factura
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="INVOICE_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )

        # Usar el handler que ahora usa el flujo 4-pasos interno
        await handle_invoice_image(bot, chat_id, store_code, text, is_credit_note=False)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_CREDIT_NOTE:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Validar formato del CFAC_ID
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXNXXXXXXXXXX\nEjemplo: K096N000123456",
                parse_mode="Markdown"
            )
            # Mantener en el mismo estado para que reintente
            return

        # Registrar generación de nota de crédito
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="CREDIT_NOTE_IMAGE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )

        # Usar el handler que ahora usa el flujo 4-pasos interno
        await handle_invoice_image(bot, chat_id, store_code, text, is_credit_note=True)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_COMANDA:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Validar formato del CFAC_ID
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX\nEjemplo: K096F001779631",
                parse_mode="Markdown"
            )
            # Mantener en el mismo estado para que reintente
            return

        # Registrar consulta de comanda
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="COMANDA_SEARCH",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )

        # Usar el handler que ahora usa el flujo 4-pasos interno
        await handle_comanda(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_ASSOCIATED_CODE:
        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Validar formato del CFAC_ID
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX o KXXXNXXXXXXXXXX",
                parse_mode="Markdown"
            )
            # Mantener en el mismo estado para que reintente
            return

        # Registrar consulta de código asociado
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="ASSOCIATED_CODE",
            store=store_code,
            details=f"CFAC_ID: {text}"
        )

        await handle_associated_code(bot, chat_id, store_code, text)
        session['state'] = UserState.IN_MENU

    elif current_state == UserState.WAITING_REPRINT_TYPE:
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

    elif current_state == UserState.WAITING_REPRINT:
        reprint_type = session.get('reprint_type', 'factura')

        # Validar que no sea un comando del menú
        if text in MENU_BUTTONS:
            # Es un botón del menú, procesarlo
            session['state'] = UserState.IN_MENU
            await handle_all_messages(message)
            return

        # Validar formato del CFAC_ID
        if not validate_cfac_id(text):
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: KXXXFXXXXXXXXXX para facturas/comandas\nKXXXNXXXXXXXXXX para notas de crédito",
                parse_mode="Markdown"
            )
            # Mantener en el mismo estado para que reintente
            return

        # Registrar re-impresión
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

    else:
        # Estado desconocido, volver al inicio
        session['state'] = UserState.WAITING_STORE
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ *Estado no reconocido*\n\nPor favor ingrese el código de tienda:",
            parse_mode="Markdown"
        )


async def main():
    """Función principal"""
    logger.info("🤖 Iniciando KFC Bot - Sistema Completo")
    logger.info(f"🕒 Hora de inicio: {datetime.now()}")

    try:
        # Verificar estado del image_service
        logger.info(f"🔧 ImageService: {'✅ DISPONIBLE' if image_service.is_available() else '❌ NO DISPONIBLE'}")
        if image_service.is_available():
            logger.info(f"   Método: {'Selenium' if image_service.is_selenium_available() else 'Imgkit'}")
            logger.info(f"   Sistema: {image_service.system}")

        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")

        await bot.delete_webhook()
        await bot.polling(none_stop=True, interval=1, timeout=30)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cerrar todas las conexiones
        db_manager.close_all_connections()

        # Cerrar Selenium si está activo
        image_service.close_selenium()

        logger.info("👋 Bot detenido")


if __name__ == "__main__":
    asyncio.run(main())