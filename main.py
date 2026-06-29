"""
main.py - Bot principal de gestión KFC
VERSIÓN CORREGIDA - CON FLUJO DE MOTORIZADO COMPLETO
"""

import asyncio
import os
import sys
import base64
import subprocess
import platform
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
    procesar_periodo_seleccion, handle_motorizado_select_callback,
    handle_motorizado_confirm_callback, motorizado_temp, set_bot_instance
)
from handlers.report_handler import handle_report_command
from core.image_service import image_service

logger = get_logger("main_bot")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN no configurado")
    sys.exit(1)

bot = AsyncTeleBot(BOT_TOKEN)

# Asignar la instancia del bot al módulo de handlers para usar en callbacks
set_bot_instance(bot)

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
    WAITING_MOTORIZADO_ORDER = "waiting_motorizado_order"
    WAITING_MOTORIZADO_DOCUMENT = "waiting_motorizado_document"


def validate_cfac_id(cfac_id: str) -> bool:
    """Valida si un CFAC_ID tiene formato válido MULTIMARCA"""
    if not cfac_id:
        return False
    if len(cfac_id) < 10:
        return False
    # Ahora acepta cualquier letra al inicio (K, M, J, T, G, A, E, V, I, R, B, C)
    # Formato: [LETRA][3 dígitos][F o N][resto]
    if len(cfac_id) >= 5 and cfac_id[4] not in ['F', 'N']:
        return False
    return True


async def handle_motorizado_final_confirm(bot, chat_id: int, user_id: int, id_motorolo: str, codigo_app: str):
    """
    PASO FINAL: Muestra confirmación antes de asignar el motorizado
    """
    try:
        logger.info(f"🔍 Confirmación final para motorizado {id_motorolo} en orden {codigo_app}")

        # Verificar sesión
        if user_id not in motorizado_temp:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Sesión expirada*\n\nPor favor inicie nuevamente desde el menú principal.",
                parse_mode="Markdown"
            )
            return

        store_code = motorizado_temp[user_id].get('store_code')
        if not store_code:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error: No se encontró la tienda*",
                parse_mode="Markdown"
            )
            return

        # Buscar el motorizado seleccionado
        motorizados = motorizado_temp[user_id].get('motorizados', [])
        motorizado_seleccionado = None
        for m in motorizados:
            if m[0] == id_motorolo:
                motorizado_seleccionado = m
                break

        if not motorizado_seleccionado:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error: No se encontró el motorizado seleccionado*",
                parse_mode="Markdown"
            )
            return

        # Datos del motorizado seleccionado
        nombres = motorizado_seleccionado[1] or ""
        apellidos = motorizado_seleccionado[2] or ""
        empresa = motorizado_seleccionado[3] or "N/A"
        tipo = motorizado_seleccionado[4] or "N/A"
        telefono = motorizado_seleccionado[5] or "N/A"
        documento = motorizado_seleccionado[6] or "N/A"

        # Motorizado actual
        orden_data = motorizado_temp[user_id].get('orden_data')
        motorizado_actual = "No asignado"
        if orden_data and orden_data[1]:
            motorizado_actual = f"{orden_data[1]} {orden_data[2]}".strip()

        mensaje = f"""
⚠️ *CONFIRMAR ASIGNACIÓN DE MOTORIZADO*

📦 *Orden:* `{codigo_app}`

👤 *MOTORIZADO ACTUAL:*
• {motorizado_actual}

{'=' * 30}

👤 *NUEVO MOTORIZADO:*
• Nombre: {nombres} {apellidos}
• Documento: {documento}
• Empresa: {empresa}
• Tipo: {tipo}
• Teléfono: {telefono}

{'=' * 30}

¿Está seguro de que desea asignar este motorizado a la orden?
"""

        # Botones de confirmación
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(
                "✅ Sí, Asignar",
                callback_data=f"mc_{id_motorolo}_{codigo_app}"
            ),
            types.InlineKeyboardButton(
                "❌ No, Cancelar",
                callback_data="menu_principal"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🔄 Buscar otro documento",
                callback_data="asignar_motorizado"
            )
        )

        await bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode="Markdown",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Error en confirmación final de motorizado: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Error:* `{str(e)[:200]}`",
            parse_mode="Markdown"
        )


async def handle_store_setup(bot, chat_id: int, store_code: str, user_id: int, username: str):
    """
    Maneja la configuración inicial de una tienda - VERSIÓN SIN ODBC
    Solo detecta el SO y valida conectividad por ping
    """
    try:
        # Detectar SO primero (esto no necesita BD)
        os_type, address = OSDetector.detect_os(store_code, quick=True)
        logger.info(f"Tienda {store_code}: SO detectado = {os_type}, IP = {address}")

        # Verificar conectividad básica (ping)
        system = platform.system()
        param = '-n' if system == 'Windows' else '-c'

        try:
            result = subprocess.run(
                ['ping', param, '2', address],
                capture_output=True,
                text=True,
                timeout=5
            )
            host_online = result.returncode == 0
            if host_online:
                logger.info(f"✅ Ping exitoso a {address}")
            else:
                logger.warning(f"⚠️ Ping fallido a {address}, pero continuamos (puede ser firewall)")
        except Exception as e:
            logger.warning(f"⚠️ Error en ping: {e}, continuando...")
            host_online = True  # Asumimos que está online

        # Registrar éxito sin conexión a BD
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="STORE_SETUP_SUCCESS",
            store=store_code,
            details=f"Sistema detectado: {os_type}, Dirección: {address}"
        )

        logger.info(f"✅ Configuración exitosa para {store_code} usando {os_type}")
        return os_type

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
    🍗 *SISTEMA MULTIMARCA - GESTIÓN DE ÓRDENES*

    📋 *Por favor, ingrese el código de la tienda:*

    • KFC (ej: K025)
    • Menestras del Negro (ej: M012)
    • Cajun (ej: J030)
    • Tropi (ej: T045)
    • Gus (ej: G078)
    • American Deli (ej: A012)
    • Español (ej: E056)
    • Juan Valdez (ej: V010)
    • Il Cappo (ej: I089)
    • Cara Res (ej: R034)
    • Baskin Robbins (ej: BS05)
    • Cinnabon (ej: CN12)

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

    # ============================================================
    # ✅ MANEJAR CALLBACKS DE MOTORIZADO - SELECCIÓN (CORREGIDO)
    # ============================================================
    if call.data.startswith('ms_'):
        idx = call.data.replace('ms_', '')
        logger.info(f"Motorizado seleccionado - índice: {idx}")

        # Obtener datos del motorizado seleccionado
        if user_id in motorizado_temp:
            temp_ids = motorizado_temp[user_id].get('temp_ids', {})
            temp_data = temp_ids.get(idx)
            if temp_data:
                id_motorolo = temp_data['id_motorolo']
                codigo_app = temp_data['codigo_app']
                logger.info(f"✅ Motorizado seleccionado: ID={id_motorolo}, Orden={codigo_app}")

                # ✅ PASO FINAL: Mostrar confirmación
                await handle_motorizado_final_confirm(bot, chat_id, user_id, id_motorolo, codigo_app)
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ *Error: No se encontraron datos del motorizado*",
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Sesión expirada*\n\nPor favor inicie nuevamente desde el menú principal.",
                parse_mode="Markdown"
            )

        await bot.answer_callback_query(call.id)
        return

    # ============================================================
    # ✅ MANEJAR CALLBACKS DE MOTORIZADO - CONFIRMACIÓN FINAL (CORREGIDO)
    # ============================================================
    if call.data.startswith('mc_'):
        parts = call.data.split('_')
        if len(parts) >= 3:
            id_motorolo = parts[1]
            codigo_app = '_'.join(parts[2:])
            logger.info(f"✅ Confirmando asignación - ID: {id_motorolo}, Orden: {codigo_app}")

            # ✅ PASO IMPORTANTE: Verificar que la sesión existe
            if user_id not in motorizado_temp:
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ *Sesión expirada*\n\nPor favor inicie nuevamente el proceso de asignación.",
                    parse_mode="Markdown"
                )
                await bot.answer_callback_query(call.id)
                return

            # ✅ SI LA SESIÓN EXISTE, PERO NO TIENE selected_motorizado, RECUPERARLO
            if 'selected_motorizado' not in motorizado_temp[user_id]:
                logger.warning(f"⚠️ selected_motorizado no encontrado en sesión para user_id {user_id}")
                logger.info(f"🔍 Datos en sesión: {list(motorizado_temp[user_id].keys())}")

                # Intentar recuperar de motorizados
                motorizados = motorizado_temp[user_id].get('motorizados', [])
                motorizado_encontrado = None
                for m in motorizados:
                    if m[0] == id_motorolo:
                        motorizado_encontrado = m
                        break

                if motorizado_encontrado:
                    motorizado_temp[user_id]['selected_motorizado'] = motorizado_encontrado
                    logger.info(f"✅ Motorizado recuperado de motorizados: {motorizado_encontrado[1]} {motorizado_encontrado[2]}")
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ *Error: No se encontró el motorizado seleccionado*\n\n"
                             f"ID: {id_motorolo}\n"
                             f"Orden: {codigo_app}\n\n"
                             f"Por favor, inicie nuevamente el proceso de asignación.",
                        parse_mode="Markdown"
                    )
                    await bot.answer_callback_query(call.id)
                    return

            # ✅ LLAMAR A LA FUNCIÓN DE CONFIRMACIÓN
            await handle_motorizado_confirm_callback(call, id_motorolo, codigo_app)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Error: Formato de callback inválido*",
                parse_mode="Markdown"
            )

        await bot.answer_callback_query(call.id)
        return

    # ============================================================
    # CALLBACKS ANTIGUOS (COMPATIBILIDAD)
    # ============================================================
    if call.data.startswith('motorizado_select_'):
        temp_id = call.data.replace('motorizado_select_', '')
        await handle_motorizado_select_callback(call, temp_id)
        await bot.answer_callback_query(call.id)
        return

    if call.data.startswith('motorizado_confirm_'):
        parts = call.data.split('_')
        if len(parts) >= 4:
            id_motorolo = parts[2]
            codigo_app = '_'.join(parts[3:])
            await handle_motorizado_confirm_callback(call, id_motorolo, codigo_app)
        await bot.answer_callback_query(call.id)
        return

    # ============================================================
    # RANGO
    # ============================================================
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
    # ESTADOS DE AUDITORÍA POR RANGO
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
                text="❌ *Código inválido*\n\n"
                     "Formatos válidos:\n"
                     "• KFC: K025\n"
                     "• Menestras del Negro: M012\n"
                     "• Cajun: J030\n"
                     "• Tropi: T045\n"
                     "• Gus: G078\n"
                     "• American Deli: A012\n"
                     "• Español: E056\n"
                     "• Juan Valdez: V010\n"
                     "• Il Cappo: I089\n"
                     "• Cara Res: R034\n"
                     "• Baskin Robbins: BS05\n"
                     "• Cinnabon: CN12",
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

        elif text == "🚚 Asignar Motorizado":
            session['state'] = UserState.WAITING_MOTORIZADO_ORDER
            await bot.send_message(
                chat_id=chat_id,
                text="🚚 *ASIGNAR MOTORIZADO*\n\n"
                     "📝 *Ingrese el código de la orden (codigo_app):*\n\n"
                     "Ejemplo: `0007271177-010101`",
                parse_mode="Markdown"
            )

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
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: [LETRA]XXX[F o N]XXXXXXXXXX\nEjemplo: K096F001779631, M061F000234440",
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
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: [LETRA]XXX[F o N]XXXXXXXXXX\nEjemplo: K096N000123456, M061N000123456",
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
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: [LETRA]XXX[F o N]XXXXXXXXXX\nEjemplo: K096F001779631",
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
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: [LETRA]XXX[F o N]XXXXXXXXXX\nEjemplo: K096F001779631, M061F000234440",
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
                text="❌ *CFAC_ID inválido*\n\nFormato esperado: [LETRA]XXX[F o N]XXXXXXXXXX\nEjemplo: K096F001779631, M061F000234440",
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
    # WAITING_MOTORIZADO_ORDER
    # ============================================
    if current_state == UserState.WAITING_MOTORIZADO_ORDER:
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="MOTORIZADO_ORDER_SEARCH",
            store=store_code,
            details=f"Orden: {text}"
        )
        # Guardar directamente en motorizado_temp con el user_id actual
        motorizado_temp[user_id] = {
            'store_code': store_code,
            'codigo_app': text,
            'step': 'waiting_order'
        }
        logger.info(f"✅ Motorizado temp guardado para user_id {user_id}: orden={text}")

        from handlers.menu_handler_combined import handle_motorizado_order_search
        await handle_motorizado_order_search(bot, chat_id, text, store_code, user_sessions)
        session['state'] = UserState.WAITING_MOTORIZADO_DOCUMENT
        return

    # ============================================
    # WAITING_MOTORIZADO_DOCUMENT
    # ============================================
    if current_state == UserState.WAITING_MOTORIZADO_DOCUMENT:
        usage_logger.log_action(
            user_id=user_id,
            username=username,
            action="MOTORIZADO_DOCUMENT_SEARCH",
            store=store_code,
            details=f"Documento: {text}"
        )

        # Verificar que existe en motorizado_temp
        if user_id not in motorizado_temp:
            logger.error(f"❌ user_id {user_id} no encontrado en motorizado_temp. Keys: {list(motorizado_temp.keys())}")
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Sesión expirada*\n\nPor favor inicie nuevamente desde el menú principal.",
                parse_mode="Markdown"
            )
            session['state'] = UserState.IN_MENU
            await show_main_menu(bot, chat_id, store_code)
            return

        from handlers.menu_handler_combined import handle_motorizado_document_search
        await handle_motorizado_document_search(bot, chat_id, text, user_id, user_sessions)
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