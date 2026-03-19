# handlers/auditoria_rango.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import logging
from reports.excel_reporter import generar_excel_auditoria  # Lo crearemos luego
from database.queries import consultar_pedidos_por_rango  # Lo crearemos luego

# Estados de la conversación
SELECCION_FECHA, INGRESO_HORA_INICIO, INGRESO_HORA_FIN, CONFIRMAR = range(4)

# Opciones de fechas predefinidas
FECHAS_OPCIONES = {
    '📅 Día actual': 0,
    '⬅️ Día de ayer': 1,
    '2️⃣ Últimos 2 días': 2,
    '3️⃣ Últimos 3 días': 3,
    '🔍 Selección manual': 'manual'
}


async def auditoria_rango_start(update: Update, context: CallbackContext) -> int:
    """Inicia el proceso mostrando opciones de fecha."""
    reply_keyboard = [[opcion] for opcion in FECHAS_OPCIONES.keys()]
    reply_keyboard.append(["❌ Cancelar"])

    await update.message.reply_text(
        "📊 *Auditoría por Rango*\n\nSelecciona el rango de fechas:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Elige una opción"
        ),
        parse_mode='Markdown'
    )
    return SELECCION_FECHA


async def seleccionar_fecha(update: Update, context: CallbackContext) -> int:
    """Procesa la selección de fecha."""
    text = update.message.text
    user = update.message.from_user

    if text == "❌ Cancelar":
        await update.message.reply_text("Proceso cancelado.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    fecha_fin = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if text == '📅 Día actual':
        fecha_inicio = fecha_fin
    elif text == '⬅️ Día de ayer':
        fecha_inicio = fecha_fin - timedelta(days=1)
    elif text == '2️⃣ Últimos 2 días':
        fecha_inicio = fecha_fin - timedelta(days=2)
    elif text == '3️⃣ Últimos 3 días':
        fecha_inicio = fecha_fin - timedelta(days=3)
    elif text == '🔍 Selección manual':
        await update.message.reply_text(
            "Por favor, ingresa la fecha de inicio en formato *YYYY-MM-DD* (ej. 2026-03-19):",
            parse_mode='Markdown'
        )
        # Aquí necesitarías otro estado para manejar la entrada manual de fechas
        # Por simplicidad, usaremos solo las predefinidas por ahora
        await update.message.reply_text("Funcionalidad manual en desarrollo. Usa las opciones predefinidas.")
        return SELECCION_FECHA
    else:
        await update.message.reply_text("Opción no válida.")
        return SELECCION_FECHA

    # Guardamos las fechas en el contexto
    context.user_data['fecha_inicio'] = fecha_inicio.date()
    context.user_data['fecha_fin'] = fecha_fin.date()

    await update.message.reply_text(
        f"✅ Rango seleccionado: *{fecha_inicio.date()}* al *{fecha_fin.date()}*\n\n"
        "Ahora, ingresa la *hora de inicio* del rango (formato HH:MM, ej. 20:00):",
        parse_mode='Markdown'
    )
    return INGRESO_HORA_INICIO


async def ingresar_hora_inicio(update: Update, context: CallbackContext) -> int:
    """Recibe y valida la hora de inicio."""
    hora_text = update.message.text.strip()

    try:
        # Validar formato hora HH:MM
        hora_valida = datetime.strptime(hora_text, "%H:%M").time()
        context.user_data['hora_inicio'] = hora_valida

        await update.message.reply_text(
            f"Hora de inicio: *{hora_text}*\n\nAhora ingresa la *hora de fin* (formato HH:MM):",
            parse_mode='Markdown'
        )
        return INGRESO_HORA_FIN
    except ValueError:
        await update.message.reply_text(
            "❌ Formato incorrecto. Usa *HH:MM* (ej. 23:00):",
            parse_mode='Markdown'
        )
        return INGRESO_HORA_INICIO


async def ingresar_hora_fin(update: Update, context: CallbackContext) -> int:
    """Recibe la hora de fin y confirma los datos."""
    hora_text = update.message.text.strip()

    try:
        hora_fin = datetime.strptime(hora_text, "%H:%M").time()
        hora_inicio = context.user_data['hora_inicio']

        if hora_fin <= hora_inicio:
            await update.message.reply_text(
                "❌ La hora de fin debe ser *mayor* que la de inicio. Intenta de nuevo:",
                parse_mode='Markdown'
            )
            return INGRESO_HORA_FIN

        context.user_data['hora_fin'] = hora_fin

        # Mostrar resumen y preguntar si proceder
        resumen = (
            f"📋 *Resumen de la consulta*\n"
            f"📅 Desde: {context.user_data['fecha_inicio']} {context.user_data['hora_inicio']}\n"
            f"📅 Hasta: {context.user_data['fecha_fin']} {context.user_data['hora_fin']}\n\n"
            f"¿Generar el reporte en Excel?"
        )

        reply_keyboard = [["✅ Sí, generar"], ["❌ No, cancelar"]]
        await update.message.reply_text(
            resumen,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            parse_mode='Markdown'
        )
        return CONFIRMAR
    except ValueError:
        await update.message.reply_text(
            "❌ Formato incorrecto. Usa *HH:MM* (ej. 23:00):",
            parse_mode='Markdown'
        )
        return INGRESO_HORA_FIN


async def confirmar_y_generar(update: Update, context: CallbackContext) -> int:
    """Confirma y genera el archivo Excel."""
    if update.message.text == "❌ No, cancelar":
        await update.message.reply_text("Proceso cancelado.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Mostrar mensaje de "procesando"
    progress_msg = await update.message.reply_text(
        "⏳ Generando reporte, esto puede tomar unos segundos...",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        # 1. Obtener datos de la base de datos
        fecha_inicio = context.user_data['fecha_inicio']
        fecha_fin = context.user_data['fecha_fin']
        hora_inicio = context.user_data['hora_inicio']
        hora_fin = context.user_data['hora_fin']

        # Llamar a tu función de consulta (la crearemos en database/queries.py)
        datos = await consultar_pedidos_por_rango(
            fecha_inicio, fecha_fin, hora_inicio, hora_fin
        )

        if not datos:
            await progress_msg.edit_text("⚠️ No se encontraron datos para el rango seleccionado.")
            return ConversationHandler.END

        # 2. Generar archivo Excel
        archivo_excel = await generar_excel_auditoria(datos)

        # 3. Enviar el archivo por Telegram
        with open(archivo_excel, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=f"auditoria_{fecha_inicio}_{hora_inicio.strftime('%H-%M')}.xlsx",
                caption=f"✅ Reporte generado para el rango {fecha_inicio} {hora_inicio} - {fecha_fin} {hora_fin}"
            )

        # Limpiar archivo temporal (opcional)
        import os
        os.remove(archivo_excel)

    except Exception as e:
        logging.error(f"Error generando reporte: {e}")
        await progress_msg.edit_text(
            "❌ Ocurrió un error al generar el reporte. Revisa los logs."
        )

    return ConversationHandler.END


async def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancela la conversación."""
    await update.message.reply_text(
        "Proceso cancelado.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END