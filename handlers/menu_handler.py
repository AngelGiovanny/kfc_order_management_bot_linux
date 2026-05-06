"""
Handlers para todas las opciones del menú - Versión combinada
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telebot import types

from config.database import db_manager
from database.queries import QueryManager
from utils.logger import get_logger
from core.image_service import ImageService
from core.printer_manager import PrinterManager, PrintFlowManager
from core.os_detector import OSDetector

logger = get_logger(__name__)

# Instancia global de servicios
image_service = ImageService()

# Diccionario para almacenar estados de motorizado
motorizado_temp = {}


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú principal completo"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    menu_text = "📋 *SELECCIONE UNA OPCIÓN:*"

    if store_code:
        menu_text = f"🏪 *Tienda:* {store_code}\n\n{menu_text}"

    # Crear teclado inline
    keyboard = [
        [InlineKeyboardButton("🔍 Verificar orden", callback_data='verificar_orden')],
        [InlineKeyboardButton("📊 Auditoría", callback_data='auditoria')],
        [InlineKeyboardButton("🖼️ Factura imagen", callback_data='factura_imagen')],
        [InlineKeyboardButton("📄 Nota crédito", callback_data='nota_credito')],
        [InlineKeyboardButton("🍗 Comanda", callback_data='comanda')],
        [InlineKeyboardButton("🔗 Código asociado", callback_data='codigo_asociado')],
        [InlineKeyboardButton("🖨️ Re-Impresión", callback_data='re_impresion')],
        [InlineKeyboardButton("🚚 Asignar Motorizado", callback_data='asignar_motorizado')],  # NUEVO BOTÓN
        [InlineKeyboardButton("🔧 Diagnóstico", callback_data='diagnostico')],
        [InlineKeyboardButton("📈 Reportes", callback_data='reportes')],
        [InlineKeyboardButton("🔄 Cambiar tienda", callback_data='cambiar_tienda')],
        [InlineKeyboardButton("❌ Salir", callback_data='salir')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=menu_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=menu_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except:
        # Fallback sin Markdown
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=menu_text.replace('*', ''),
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=menu_text.replace('*', ''),
                reply_markup=reply_markup
            )


async def show_action_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra botones de acción después de una operación"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    keyboard = [
        [InlineKeyboardButton("🔍 Nueva consulta", callback_data='nueva_consulta')],
        [InlineKeyboardButton("🔧 Diagnóstico", callback_data='diagnostico')],
        [InlineKeyboardButton("🏠 Menú principal", callback_data='menu_principal')],
        [InlineKeyboardButton("🔄 Cambiar tienda", callback_data='cambiar_tienda')],
        [InlineKeyboardButton("❌ Salir", callback_data='salir')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=f"🏪 *Tienda:* {store_code}\n\n¿Qué desea hacer ahora?",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=f"🏪 *Tienda:* {store_code}\n\n¿Qué desea hacer ahora?",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except:
        # Fallback sin Markdown
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=f"🏪 Tienda: {store_code}\n\n¿Qué desea hacer ahora?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=f"🏪 Tienda: {store_code}\n\n¿Qué desea hacer ahora?",
                reply_markup=reply_markup
            )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks de botones inline"""
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    store_code = user_data.get('store_code')

    if query.data == 'menu_principal':
        await show_main_menu(update, context)

    elif query.data == 'cambiar_tienda':
        user_data['awaiting_input'] = 'store_code'
        user_data.pop('store_code', None)
        await query.message.reply_text(
            "Por favor, ingrese el código de la tienda (ej: K096):"
        )

    elif query.data == 'nueva_consulta':
        user_data['awaiting_input'] = 'invoice_id'
        await query.message.reply_text(
            "¿Qué número de factura/nota/comanda desea consultar?"
        )

    elif query.data == 'salir':
        user_data.clear()
        await query.message.reply_text(
            "✅ *SESIÓN FINALIZADA*\n\nGracias por usar el sistema KFC.\n\nPara una nueva consulta, envíe /start",
            parse_mode="Markdown"
        )

    elif query.data == 'factura_imagen':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'factura_imagen'
        await query.message.reply_text(
            "Ingrese el número de factura para generar la imagen:"
        )

    elif query.data == 'nota_credito':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'nota_credito'
        await query.message.reply_text(
            "Ingrese el número de nota de crédito:"
        )

    elif query.data == 'comanda':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'comanda'
        await query.message.reply_text(
            "Ingrese el número de factura o ID de comanda:"
        )

    elif query.data == 'verificar_orden':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'verificar_orden'
        await query.message.reply_text(
            "📝 Ingrese el número de orden (codigo_app):"
        )

    elif query.data == 'auditoria':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'auditoria'
        await query.message.reply_text(
            "🔎 Ingrese el código o patrón de orden a auditar:\n\nEjemplo: 2293, 000229, etc."
        )

    elif query.data == 'codigo_asociado':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'codigo_asociado'
        await query.message.reply_text(
            "🔢 Ingrese el CFAC_ID para obtener código asociado:"
        )

    elif query.data == 're_impresion':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        await show_reprint_menu(update, context)

    elif query.data == 'asignar_motorizado':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        user_data['awaiting_input'] = 'motorizado_order'
        await query.message.reply_text(
            "🚚 *ASIGNAR MOTORIZADO*\n\n"
            "📝 *Ingrese el código de la orden (codigo_app):*\n\n"
            "Ejemplo: `0007271177-010101`",
            parse_mode="Markdown"
        )

    elif query.data == 'diagnostico':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        await handle_diagnostic(update, context)

    elif query.data == 'reportes':
        if not store_code:
            await query.message.reply_text(
                "Primero debe configurar una tienda. Use el botón '🔄 Cambiar tienda'"
            )
            return

        await handle_reports(update, context)


async def show_reprint_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra menú de re-impresión"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    keyboard = [
        [InlineKeyboardButton("📄 Re-imprimir Factura", callback_data='reimprimir_factura')],
        [InlineKeyboardButton("📋 Re-imprimir Nota Crédito", callback_data='reimprimir_nota_credito')],
        [InlineKeyboardButton("🍗 Re-imprimir Comanda", callback_data='reimprimir_comanda')],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data='menu_principal')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=f"🏪 *Tienda:* {store_code}\n\n🖨️ *SELECCIONE TIPO DE RE-IMPRESIÓN:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=f"🏪 *Tienda:* {store_code}\n\n🖨️ *SELECCIONE TIPO DE RE-IMPRESIÓN:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except:
        # Fallback sin Markdown
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=f"🏪 Tienda: {store_code}\n\n🖨️ SELECCIONE TIPO DE RE-IMPRESIÓN:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=f"🏪 Tienda: {store_code}\n\n🖨️ SELECCIONE TIPO DE RE-IMPRESIÓN:",
                reply_markup=reply_markup
            )


async def handle_motorizado_order_search(update: Update, context: ContextTypes.DEFAULT_TYPE, codigo_app: str):
    """Busca la orden para asignar motorizado"""
    user_data = context.user_data
    store_code = user_data.get('store_code')
    user_id = update.effective_user.id

    try:
        await update.message.reply_text(
            f"🔍 *Buscando orden {codigo_app}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await update.message.reply_text(
                "❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        # Consultar información de la orden con motorizado actual
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
                ca.estado as estado_app,
                cf.cfac_claveAcceso,
                s.std_descripcion as estado_factura
            FROM Cabecera_App ca
            LEFT JOIN Motorolo m ON ca.IDMotorolo = m.IDMotorolo
            LEFT JOIN Cabecera_Factura cf ON ca.cfac_id = cf.cfac_id
            LEFT JOIN Status s ON cf.IDStatus = s.IDStatus
            WHERE ca.codigo_app = ?
        """

        cursor.execute(query, (codigo_app,))
        orden = cursor.fetchone()
        cursor.close()

        if not orden:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Intentar con otro código", callback_data='asignar_motorizado')],
                [InlineKeyboardButton("🏠 Volver al menú", callback_data='menu_principal')]
            ])
            await update.message.reply_text(
                f"❌ *ORDEN NO ENCONTRADA*\n\n"
                f"No se encontró la orden `{codigo_app}` en la tienda {store_code}.\n\n"
                f"Verifique el código e intente nuevamente.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return

        # Guardar datos de la orden en sesión temporal
        motorizado_temp[user_id] = {
            'store_code': store_code,
            'codigo_app': codigo_app,
            'orden_data': orden,
            'step': 'waiting_document'
        }

        # Obtener datos de la orden
        id_motorolo_actual = orden[0]
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
"""

        if id_motorolo_actual:
            mensaje += f"\n🆔 ID Motorizado: `{id_motorolo_actual}`"

        mensaje += f"\n\n{'='*30}\n\n"
        mensaje += "🚚 *PASO 2/3 - BUSCAR NUEVO MOTORIZADO*\n\n"
        mensaje += "📝 *Ingrese el número de documento del nuevo motorizado:*\n\n"
        mensaje += "*(Ejemplo: 12345678 o 1234567890)*"

        user_data['awaiting_input'] = 'motorizado_document'
        await update.message.reply_text(
            text=mensaje,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error buscando orden para motorizado: {e}")
        await update.message.reply_text(
            f"❌ *Error al buscar la orden:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )


async def handle_motorizado_document_search(update: Update, context: ContextTypes.DEFAULT_TYPE, documento: str):
    """Busca motorizados por número de documento"""
    user_data = context.user_data
    user_id = update.effective_user.id

    if user_id not in motorizado_temp:
        await update.message.reply_text(
            "❌ *Sesión expirada*\n\nPor favor inicie nuevamente desde el menú principal.",
            parse_mode="Markdown"
        )
        return

    store_code = motorizado_temp[user_id]['store_code']
    codigo_app = motorizado_temp[user_id]['codigo_app']

    try:
        await update.message.reply_text(
            f"🔍 Buscando motorizados con documento que contenga `{documento}`...",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await update.message.reply_text(
                "❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        # Buscar motorizados por documento
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
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Intentar con otro documento", callback_data='asignar_motorizado')],
                [InlineKeyboardButton("🏠 Volver al menú", callback_data='menu_principal')]
            ])
            await update.message.reply_text(
                f"❌ *NO SE ENCONTRARON MOTORIZADOS*\n\n"
                f"Documento buscado: `{documento}`\n"
                f"Orden: `{codigo_app}`\n\n"
                f"Verifique el número de documento e intente nuevamente.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return

        # Guardar resultados
        motorizado_temp[user_id]['motorizados'] = motorizados
        motorizado_temp[user_id]['step'] = 'select_motorizado'

        # Crear teclado con los motorizados encontrados
        keyboard = []

        for m in motorizados:
            id_motorolo = m[0]
            nombres = m[1] or ""
            apellidos = m[2] or ""
            empresa = m[3] or "N/A"
            tipo = m[4] or "N/A"

            nombre_completo = f"{nombres} {apellidos}".strip()
            btn_text = f"👤 {nombre_completo} - {empresa} ({tipo})"
            callback_data = f"motorizado_select_{id_motorolo}_{codigo_app}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='menu_principal')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        mensaje = f"""
✅ *MOTORIZADOS ENCONTRADOS:* {len(motorizados)}

📦 *Orden:* `{codigo_app}`

🚚 *PASO 3/3 - SELECCIONE MOTORIZADO:*

Seleccione el motorizado que desea asignar:
"""

        user_data['awaiting_input'] = None
        await update.message.reply_text(
            text=mensaje,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error buscando motorizado por documento: {e}")
        await update.message.reply_text(
            f"❌ *Error al buscar motorizado:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )


async def handle_motorizado_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, id_motorolo: int, codigo_app: str):
    """Maneja la selección de motorizado para confirmación"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if user_id not in motorizado_temp:
        await query.message.reply_text(
            "❌ *Sesión expirada*\n\nPor favor inicie nuevamente.",
            parse_mode="Markdown"
        )
        return

    motorizados = motorizado_temp[user_id].get('motorizados', [])
    motorizado_seleccionado = None

    for m in motorizados:
        if m[0] == id_motorolo:
            motorizado_seleccionado = m
            break

    if not motorizado_seleccionado:
        await query.message.reply_text("❌ Error: No se encontró el motorizado")
        return

    # Guardar motorizado seleccionado
    motorizado_temp[user_id]['selected_motorizado'] = motorizado_seleccionado
    motorizado_temp[user_id]['step'] = 'confirm'

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
⚠️ *CONFIRMAR ASIGNACIÓN DE MOTORIZADO*

📦 *Orden:* `{codigo_app}`

👤 *MOTORIZADO ACTUAL:*
• {motorizado_actual}

{'='*30}

👤 *NUEVO MOTORIZADO:*
• Nombre: {nombres} {apellidos}
• Documento: {documento}
• Empresa: {empresa}
• Tipo: {tipo}
• Teléfono: {telefono}

{'='*30}

¿Está seguro de que desea asignar este motorizado a la orden?
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, Asignar", callback_data=f"motorizado_confirm_{id_motorolo}_{codigo_app}")],
        [InlineKeyboardButton("❌ No, Cancelar", callback_data='menu_principal')],
        [InlineKeyboardButton("🔄 Buscar otro documento", callback_data='asignar_motorizado')]
    ])

    await query.edit_message_text(
        text=mensaje,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_motorizado_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, id_motorolo: int, codigo_app: str):
    """Ejecuta la asignación del motorizado en la base de datos"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if user_id not in motorizado_temp:
        await query.message.reply_text(
            "❌ *Sesión expirada*\n\nPor favor inicie nuevamente.",
            parse_mode="Markdown"
        )
        return

    store_code = motorizado_temp[user_id]['store_code']
    motorizado_seleccionado = motorizado_temp[user_id].get('selected_motorizado')

    if not motorizado_seleccionado:
        await query.message.reply_text(
            "❌ *Error interno*: No se encontraron datos del motorizado seleccionado.",
            parse_mode="Markdown"
        )
        return

    try:
        await query.edit_message_text(
            text="⏳ *Procesando asignación...*\n\nActualizando base de datos...",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)
        if not connection:
            await query.message.reply_text(
                "❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        # Actualizar el motorizado en la orden
        update_query = """
            UPDATE Cabecera_App 
            SET IDMotorolo = ? 
            WHERE codigo_app = ?
        """

        cursor.execute(update_query, (id_motorolo, codigo_app))
        connection.commit()

        if cursor.rowcount > 0:
            nombres = motorizado_seleccionado[1] or ""
            apellidos = motorizado_seleccionado[2] or ""
            empresa = motorizado_seleccionado[3] or "N/A"
            tipo = motorizado_seleccionado[4] or "N/A"
            telefono = motorizado_seleccionado[5] or "N/A"

            mensaje = f"""
✅ *¡MOTORIZADO ASIGNADO CON ÉXITO!*

📦 *Orden:* `{codigo_app}`

👤 *MOTORIZADO ASIGNADO:*
• Nombre: {nombres} {apellidos}
• Empresa: {empresa}
• Tipo: {tipo}
• Teléfono: {telefono}

{'='*30}

✅ La orden ha sido actualizada correctamente.
"""

            # Registrar en log de uso
            from utils.logger import usage_logger
            usage_logger.log_action(
                user_id=user_id,
                username=query.from_user.username or query.from_user.first_name,
                action="MOTORIZADO_ASIGNADO",
                store=store_code,
                details=f"Orden: {codigo_app}, Motorizado ID: {id_motorolo}"
            )

        else:
            mensaje = f"""
❌ *ERROR AL ASIGNAR MOTORIZADO*

No se pudo actualizar la orden `{codigo_app}`.

Posibles causas:
• La orden no existe
• La orden ya fue entregada
• Problemas de conexión con la base de datos

Verifique el código de la orden e intente nuevamente.
"""

        # Limpiar sesión temporal
        if user_id in motorizado_temp:
            del motorizado_temp[user_id]

        # Mostrar opciones finales
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚚 Nueva Asignación", callback_data='asignar_motorizado')],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data='menu_principal')]
        ])

        await query.edit_message_text(
            text=mensaje,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error ejecutando asignación de motorizado: {e}")
        await query.message.reply_text(
            f"❌ *Error al asignar motorizado:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las entradas de texto del usuario"""
    user_data = context.user_data
    text = update.message.text.strip().upper()
    awaiting = user_data.get('awaiting_input')
    store_code = user_data.get('store_code')

    if awaiting == 'store_code':
        # Validar formato de tienda
        if len(text) == 4 and text.startswith('K') and text[1:].isdigit():
            store_number = int(text[1:])
            if 1 <= store_number <= 999:
                user_data['store_code'] = text
                user_data['awaiting_input'] = None

                await update.message.reply_text(
                    f"✅ *Tienda configurada:* {text}\n\nAhora seleccione una opción del menú.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Menú principal", callback_data='menu_principal')]
                    ])
                )
            else:
                await update.message.reply_text(
                    "❌ *Código inválido*\n\nNúmero de tienda debe estar entre 001 y 999.",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ *Formato incorrecto*\n\nUse: K seguido de 3 números (ej: K096, K007)",
                parse_mode="Markdown"
            )

    elif awaiting == 'factura_imagen':
        if not store_code:
            await update.message.reply_text("Primero configure una tienda.")
            return

        # Usar el ImageService existente
        from core.image_service import image_service

        store_number = store_code[1:]
        url = f"http://10.101.{store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={text}&tipo_comprobante=F"

        try:
            if image_service.is_available():
                await update.message.reply_text(
                    "🖼️ *Generando imagen de factura...*",
                    parse_mode="Markdown"
                )

                image_bytes = await image_service.url_to_image(url)

                if image_bytes:
                    # Enviar imagen sin URL en el caption
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=image_bytes,
                        caption=f"📄 *Factura {text}*\n🏪 Tienda: {store_code}",
                        parse_mode="Markdown"
                    )
                else:
                    # Solo enviar información sin URL
                    await update.message.reply_text(
                        f"📄 *Factura {text}*\n🏪 Tienda: {store_code}\n\n⚠️ *No se pudo generar la imagen automáticamente*",
                        parse_mode="Markdown"
                    )
            else:
                # Solo información sin URL
                await update.message.reply_text(
                    f"📄 *Factura {text}*\n🏪 Tienda: {store_code}",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error generando imagen de factura: {e}")
            await update.message.reply_text(
                f"📄 *Factura {text}*\n🏪 Tienda: {store_code}\n\n❌ *Error generando imagen*",
                parse_mode="Markdown"
            )

        await show_action_buttons(update, context)

    elif awaiting == 'nota_credito':
        if not store_code:
            await update.message.reply_text("Primero configure una tienda.")
            return

        store_number = store_code[1:]
        url = f"http://10.101.{store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={text}&tipo_comprobante=N"

        try:
            if image_service.is_available():
                await update.message.reply_text(
                    "🖼️ *Generando imagen de nota de crédito...*",
                    parse_mode="Markdown"
                )

                image_bytes = await image_service.url_to_image(url)

                if image_bytes:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=image_bytes,
                        caption=f"📄 *Nota de Crédito {text}*\n🏪 Tienda: {store_code}",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"📄 *Nota de Crédito {text}*\n🏪 Tienda: {store_code}",
                        parse_mode="Markdown"
                    )
            else:
                await update.message.reply_text(
                    f"📄 *Nota de Crédito {text}*\n🏪 Tienda: {store_code}",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error generando imagen de nota de crédito: {e}")
            await update.message.reply_text(
                f"📄 *Nota de Crédito {text}*\n🏪 Tienda: {store_code}",
                parse_mode="Markdown"
            )

        await show_action_buttons(update, context)

    elif awaiting == 'comanda':
        if not store_code:
            await update.message.reply_text("Primero configure una tienda.")
            return

        # Primero buscar ID de comanda
        try:
            connection = db_manager.get_connection(store_code)
            if connection:
                cursor = connection.cursor()
                query = QueryManager.get_comanda_url_query()
                cursor.execute(query, (text,))
                result = cursor.fetchone()
                cursor.close()

                if result and result[0]:
                    comanda_id = result[0]
                    store_number = store_code[1:]

                    url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={comanda_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

                    if image_service.is_available():
                        await update.message.reply_text(
                            "🍗 *Generando imagen de comanda...*",
                            parse_mode="Markdown"
                        )

                        image_bytes = await image_service.url_to_image(url)

                        if image_bytes:
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=image_bytes,
                                caption=f"🍗 *Comanda {comanda_id}*\n📄 Factura: {text}\n🏪 Tienda: {store_code}",
                                parse_mode="Markdown"
                            )
                        else:
                            await update.message.reply_text(
                                f"🍗 *Comanda {comanda_id}*\n📄 Factura: {text}\n🏪 Tienda: {store_code}",
                                parse_mode="Markdown"
                            )
                    else:
                        await update.message.reply_text(
                            f"🍗 *Comanda {comanda_id}*\n📄 Factura: {text}\n🏪 Tienda: {store_code}",
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_text(
                        f"❌ *No se encontró comanda para factura {text}*",
                        parse_mode="Markdown"
                    )
            else:
                await update.message.reply_text(
                    f"❌ *Error de conexión con la tienda {store_code}*",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error buscando comanda: {e}")
            await update.message.reply_text(
                f"❌ *Error buscando comanda:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )

        await show_action_buttons(update, context)

    elif awaiting == 'verificar_orden':
        await handle_order_verification(update, context, text)

    elif awaiting == 'auditoria':
        await handle_order_audit(update, context, text)

    elif awaiting == 'codigo_asociado':
        await handle_associated_code(update, context, text)

    elif awaiting == 'motorizado_order':
        await handle_motorizado_order_search(update, context, text)

    elif awaiting == 'motorizado_document':
        await handle_motorizado_document_search(update, context, text)

    elif awaiting == 'invoice_id':
        # Guardar ID y mostrar opciones
        user_data['last_invoice_id'] = text
        keyboard = [
            [
                InlineKeyboardButton("🖼️ Imagen", callback_data='factura_imagen'),
                InlineKeyboardButton("📄 Reimprimir", callback_data='factura')
            ],
            [
                InlineKeyboardButton("🍗 Comanda", callback_data='comanda'),
                InlineKeyboardButton("📄 Nota crédito", callback_data='nota_credito')
            ]
        ]
        await update.message.reply_text(
            f"¿Qué desea hacer con {text}?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        # Comando no reconocido
        await update.message.reply_text(
            "⚠️ *Comando no reconocido*\n\nUse el menú o ingrese un comando válido.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menú principal", callback_data='menu_principal')]
            ])
        )


# Funciones adaptadas de tu código original
async def handle_order_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, order_number: str):
    """Maneja verificación de estado de orden"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    try:
        await update.message.reply_text(
            f"🔍 *Buscando orden {order_number}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await update.message.reply_text(
                "❌ *Error de conexión con la base de datos*",
                parse_mode="Markdown"
            )
            return

        cursor = connection.cursor()

        try:
            query = QueryManager.get_order_status_query()
            cursor.execute(query, (order_number, order_number))
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

            await update.message.reply_text(
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error en consulta: {e}")
            await update.message.reply_text(
                text=f"❌ *Error en la consulta:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en verificación: {e}")
        await update.message.reply_text(
            text=f"❌ *Error en el proceso:*\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    user_data['awaiting_input'] = None
    await show_action_buttons(update, context)


async def handle_order_audit(update: Update, context: ContextTypes.DEFAULT_TYPE, order_pattern: str):
    """Maneja auditoría de órdenes"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    try:
        await update.message.reply_text(
            text=f"📊 *Auditoría para patrón {order_pattern}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await update.message.reply_text(
                text="❌ *Error de conexión*",
                parse_mode="Markdown"
            )
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

            await update.message.reply_text(
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error en auditoría: {e}")
            await update.message.reply_text(
                text=f"❌ *Error en auditoría:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en proceso de auditoría: {e}")
        await update.message.reply_text(
            text="❌ *Error en proceso*",
            parse_mode="Markdown"
        )

    user_data['awaiting_input'] = None
    await show_action_buttons(update, context)


async def handle_associated_code(update: Update, context: ContextTypes.DEFAULT_TYPE, cfac_id: str):
    """Maneja obtención de código asociado"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    try:
        await update.message.reply_text(
            text=f"🔗 *Buscando código asociado para {cfac_id}...*",
            parse_mode="Markdown"
        )

        connection = db_manager.get_connection(store_code)

        if not connection:
            await update.message.reply_text(
                text="❌ *Error de conexión*",
                parse_mode="Markdown"
            )
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

            await update.message.reply_text(
                text=response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error buscando código asociado: {e}")
            await update.message.reply_text(
                text=f"❌ *Error buscando código asociado:*\n`{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en proceso de código asociado: {e}")
        await update.message.reply_text(
            text="❌ *Error en proceso*",
            parse_mode="Markdown"
        )

    user_data['awaiting_input'] = None
    await show_action_buttons(update, context)


async def handle_diagnostic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja diagnóstico completo del sistema"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    try:
        await update.message.reply_text(
            text=f"🔬 *INICIANDO DIAGNÓSTICO COMPLETO - {store_code}*",
            parse_mode="Markdown"
        )

        connection_info = db_manager.get_connection_info(store_code)

        diagnostic_text = f"""
🔍 *DIAGNÓSTICO DEL SISTEMA - {store_code}*

📊 *INFORMACIÓN GENERAL:*
• Base de datos: `{connection_info['database_name']}`
• Sistema recomendado: {connection_info['recommended_os'].upper() if connection_info['recommended_os'] else 'NO DISPONIBLE'}

🔌 *PRUEBAS DE CONEXIÓN:*
"""

        # Linux
        linux_test = connection_info.get('linux_test', {'success': False})
        linux_status = "✅ CONECTADO" if linux_test.get('success') else "❌ FALLIDO"
        diagnostic_text += f"• Linux: {linux_status}\n"

        # Windows
        windows_test = connection_info.get('windows_test', {'success': False})
        windows_status = "✅ CONECTADO" if windows_test.get('success') else "❌ FALLIDO"
        diagnostic_text += f"• Windows: {windows_status}\n"

        # Servicios
        diagnostic_text += f"\n🖼️ *SERVICIO DE IMÁGENES:*\n"
        diagnostic_text += f"• Estado: {'✅ DISPONIBLE' if image_service.is_available() else '❌ NO DISPONIBLE'}\n"
        diagnostic_text += f"• Método: {'Selenium' if hasattr(image_service, 'is_selenium_available') and image_service.is_selenium_available else 'Imgkit'}\n"

        diagnostic_text += f"\n🕒 *Diagnóstico realizado:* {datetime.now().strftime('%H:%M:%S')}"

        await update.message.reply_text(
            text=diagnostic_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}")
        error_msg = str(e).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

        await update.message.reply_text(
            text=f"❌ *Error en diagnóstico:*\n`{error_msg[:200]}`",
            parse_mode="Markdown"
        )

    await show_action_buttons(update, context)


async def handle_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja reportes del sistema"""
    user_data = context.user_data
    store_code = user_data.get('store_code')

    try:
        await update.message.reply_text(
            text=f"📈 *Generando reportes para {store_code}...*",
            parse_mode="Markdown"
        )

        connection_info = db_manager.get_connection_info(store_code)
        report_date = datetime.now().strftime('%d/%m/%Y %H:%M')

        report_text = f"""
📊 *REPORTE DEL SISTEMA - {store_code}*
Fecha: {report_date}

*INFORMACIÓN DE CONEXIÓN:*
• Base de datos: `{connection_info['database_name']}`
• Sistema detectado: {connection_info['recommended_os'].upper() if connection_info['recommended_os'] else 'NO DETECTADO'}
• Linux: {'✅ CONECTADO' if connection_info.get('linux_test', {}).get('success') else '❌ FALLIDO'}
• Windows: {'✅ CONECTADO' if connection_info.get('windows_test', {}).get('success') else '❌ FALLIDO'}

*ESTADO DEL SISTEMA:*
• Tienda configurada: ✅
• Servicio de imágenes: {'✅ DISPONIBLE' if image_service.is_available() else '❌ NO DISPONIBLE'}
• Hora del sistema: {report_date}
"""

        await update.message.reply_text(
            text=report_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        simple_report = f"""
📊 *REPORTE SIMPLE - {store_code}*

Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Estado: ✅ OPERATIVO
Tienda: {store_code}
        """

        await update.message.reply_text(
            text=simple_report,
            parse_mode="Markdown"
        )

    await show_action_buttons(update, context)