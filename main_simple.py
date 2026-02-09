#!/usr/bin/env python3
"""
Versión simplificada del bot para desarrollo y pruebas rápidas
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Agregar directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot

# Configuración simple
BOT_TOKEN = os.getenv("BOT_TOKEN", "7405762231:AAGIObeGcSn82xalyCokGKuIUYl9TuJmTS8")

if BOT_TOKEN == "7405762231:AAGIObeGcSn82xalyCokGKuIUYl9TuJmTS8":
    print("⚠️  ADVERTENCIA: Usando token de prueba")
    print("   Para producción, configure BOT_TOKEN en .env")

# Inicializar bot
bot = AsyncTeleBot(BOT_TOKEN)

# Estado simple
user_data = {}


def validate_store(store_code):
    """Valida código de tienda simple"""
    store_code = store_code.upper().strip()
    if not store_code.startswith('K'):
        return False

    try:
        num = int(store_code[1:])
        return 1 <= num <= 999
    except:
        return False


async def show_menu(chat_id, store_code=None):
    """Muestra menú simple"""
    text = "📋 *MENÚ PRINCIPAL*"
    if store_code:
        text = f"🏪 Tienda: *{store_code}*\n\n" + text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Botones principales
    btn1 = types.KeyboardButton("🔍 Verificar Orden")
    btn2 = types.KeyboardButton("📄 Factura")
    btn3 = types.KeyboardButton("🖨️ Imprimir")
    btn4 = types.KeyboardButton("🔄 Cambiar Tienda")
    btn5 = types.KeyboardButton("❌ Salir")

    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5)

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['start'])
async def start_cmd(message):
    """Comando /start simplificado"""
    user_id = message.from_user.id
    user_data[user_id] = {'state': 'waiting_store'}

    welcome = """
🍗 *SISTEMA KFC - VERSIÓN SIMPLIFICADA*

Ingrese código de tienda:
• Formato: K001 a K999
• Ejemplo: K025, K180
    """

    await bot.send_message(
        chat_id=message.chat.id,
        text=welcome,
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda m: True)
async def handle_message(message):
    """Maneja todos los mensajes"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip()

    # Obtener estado
    state = user_data.get(user_id, {}).get('state', 'start')

    if state == 'waiting_store':
        # Ingresando tienda
        if validate_store(text):
            store_code = text.upper()
            user_data[user_id] = {
                'state': 'menu',
                'store': store_code,
                'last': datetime.now()
            }

            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ *Tienda {store_code} configurada*",
                parse_mode="Markdown"
            )

            await show_menu(chat_id, store_code)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ *Código inválido*\nEjemplo: K025 (K001 a K999)",
                parse_mode="Markdown"
            )

    elif state == 'menu':
        data = user_data.get(user_id, {})
        store = data.get('store', 'K001')

        if text == "🔍 Verificar Orden":
            user_data[user_id]['state'] = 'waiting_order'
            await bot.send_message(
                chat_id=chat_id,
                text="📝 Ingrese número de orden:",
                parse_mode="Markdown"
            )

        elif text == "📄 Factura":
            user_data[user_id]['state'] = 'waiting_invoice'
            await bot.send_message(
                chat_id=chat_id,
                text="📄 Ingrese CFAC_ID:",
                parse_mode="Markdown"
            )

        elif text == "🖨️ Imprimir":
            user_data[user_id]['state'] = 'waiting_print'
            await bot.send_message(
                chat_id=chat_id,
                text="🖨️ Ingrese orden a imprimir:",
                parse_mode="Markdown"
            )

        elif text == "🔄 Cambiar Tienda":
            user_data[user_id]['state'] = 'waiting_store'
            await bot.send_message(
                chat_id=chat_id,
                text="🏪 Ingrese nueva tienda:",
                parse_mode="Markdown"
            )

        elif text == "❌ Salir":
            if user_id in user_data:
                del user_data[user_id]

            await bot.send_message(
                chat_id=chat_id,
                text="👋 *Sesión finalizada*\n\nUse /start para comenzar",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )

        else:
            await bot.send_message(
                chat_id=chat_id,
                text="Seleccione una opción del menú",
                parse_mode="Markdown"
            )

    elif state == 'waiting_order':
        data = user_data.get(user_id, {})
        store = data.get('store', 'K001')

        # Simular consulta
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Orden *{text}* encontrada en {store}\nEstado: COMPLETADA",
            parse_mode="Markdown"
        )

        # Volver al menú
        user_data[user_id]['state'] = 'menu'
        await show_menu(chat_id, store)

    elif state == 'waiting_invoice':
        data = user_data.get(user_id, {})
        store = data.get('store', 'K001')

        # Simular factura
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Factura *{text}* generada para {store}",
            parse_mode="Markdown"
        )

        # Volver al menú
        user_data[user_id]['state'] = 'menu'
        await show_menu(chat_id, store)

    elif state == 'waiting_print':
        data = user_data.get(user_id, {})
        store = data.get('store', 'K001')

        # Simular impresión
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Orden *{text}* enviada a impresión en {store}",
            parse_mode="Markdown"
        )

        # Volver al menú
        user_data[user_id]['state'] = 'menu'
        await show_menu(chat_id, store)

    else:
        # Estado desconocido
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ Use /start para comenzar",
            parse_mode="Markdown"
        )


async def main():
    """Función principal simplificada"""
    print("🤖 KFC Bot Simple - Iniciando...")

    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        print(f"🆔 ID: {bot_info.id}")
        print("🔄 Escuchando mensajes...")

        await bot.polling(none_stop=True)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("👋 Bot detenido")


if __name__ == "__main__":
    asyncio.run(main())