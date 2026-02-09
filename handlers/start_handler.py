from telebot import types
from datetime import datetime
from utils.logger import BotLogger

logger = BotLogger()


class StartHandler:
    """Manejador del comando /start"""

    @staticmethod
    async def handle_start(bot, message):
        """Maneja el comando /start"""
        user_id = message.from_user.id
        logger.log_command(user_id, "/start")

        welcome_text = """
        🍗 *BIENVENIDO AL SISTEMA DE VERIFICACIÓN Y AUDITORÍA DE ÓRDENES KFC*

        _Sistema de gestión multiplataforma - Soporte Windows/Linux_

        📋 *Por favor, ingrese el código de la tienda para comenzar:*

        Ejemplo: K025, K180, K001

        ⚠️ _El sistema detectará automáticamente si el local opera en Windows o Linux_
        """

        await bot.send_message(
            chat_id=message.chat.id,
            text=welcome_text,
            parse_mode="Markdown"
        )

        # Registrar inicio de sesión
        logger.log_command(user_id, "SESSION_START")


class StoreHandler:
    """Manejador de ingreso de tienda"""

    @staticmethod
    async def handle_store_input(bot, message, store_code: str):
        """Procesa el código de tienda ingresado"""
        user_id = message.from_user.id

        # Validar formato de tienda
        if not store_code.upper().startswith('K') or len(store_code) < 4:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ *Formato inválido*\n\nEl código debe comenzar con 'K' seguido del número de tienda.\nEjemplo: K025, K180",
                parse_mode="Markdown"
            )
            return False

        # Validar rango de tienda (K001 a K999)
        try:
            store_num = int(store_code[1:])
            if store_num < 1 or store_num > 999:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ *Tienda fuera de rango*\n\nEl número debe estar entre 001 y 999.",
                    parse_mode="Markdown"
                )
                return False
        except ValueError:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ *Código inválido*\n\nEl código debe contener números después de la 'K'.",
                parse_mode="Markdown"
            )
            return False

        # Detectar sistema operativo
        from core.os_detector import OSDetector
        os_type, server_address = OSDetector.detect_os(store_code)

        logger.log_command(user_id, f"STORE_INPUT:{store_code}")
        logger.log_query(store_code, "OS_DETECTION", os_type)

        # Mostrar menú principal
        await MenuHandler.show_main_menu(bot, message.chat.id, store_code, os_type)

        return True


class MenuHandler:
    """Manejador del menú principal"""

    @staticmethod
    async def show_main_menu(bot, chat_id, store_code: str, os_type: str):
        """Muestra el menú principal con botones"""

        os_icon = "🖥️" if os_type == "windows" else "🐧"

        menu_text = f"""
        🏪 *Tienda:* {store_code}
        {os_icon} *Sistema:* {os_type.upper()}

        📋 *SELECCIONE UNA OPCIÓN:*
        """

        # Crear teclado con botones
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        buttons = [
            types.KeyboardButton("📋 Verificar estado de orden"),
            types.KeyboardButton("🔍 Auditoría de órdenes"),
            types.KeyboardButton("🖼️ Generar imagen de factura"),
            types.KeyboardButton("🍗 Verificar Comanda"),
            types.KeyboardButton("📄 Obtener código asociado de factura"),
            types.KeyboardButton("🖨️ Re-Impresión"),
            types.KeyboardButton("📊 Reporte Diario"),
            types.KeyboardButton("🔄 Volver a ingresar tienda"),
            types.KeyboardButton("❌ Finalizar consulta")
        ]

        # Agregar botones en filas de 2
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.row(buttons[i], buttons[i + 1])
            else:
                markup.row(buttons[i])

        await bot.send_message(
            chat_id=chat_id,
            text=menu_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @staticmethod
    async def handle_menu_selection(bot, message, store_code: str):
        """Maneja la selección del menú"""
        selection = message.text
        chat_id = message.chat.id

        from utils.logger import BotLogger
        logger = BotLogger(store_code)
        logger.log_command(message.from_user.id, f"MENU:{selection}")

        if selection == "📋 Verificar estado de orden":
            await bot.send_message(
                chat_id=chat_id,
                text="📝 *Ingrese el número de orden para verificar el estado:*\n\nEjemplo: 0002293258-010103",
                parse_mode="Markdown"
            )
            # Estado: Esperando número de orden

        elif selection == "🖼️ Generar imagen de factura":
            await bot.send_message(
                chat_id=chat_id,
                text="📄 *Ingrese el CFAC_ID de la factura:*",
                parse_mode="Markdown"
            )
            # Estado: Esperando CFAC_ID

        elif selection == "🍗 Verificar Comanda":
            await bot.send_message(
                chat_id=chat_id,
                text="🍟 *Ingrese el código de la comanda:*",
                parse_mode="Markdown"
            )
            # Estado: Esperando código de comanda

        elif selection == "🖨️ Re-Impresión":
            await bot.send_message(
                chat_id=chat_id,
                text="🖨️ *Ingrese el número de orden para re-imprimir:*",
                parse_mode="Markdown"
            )
            # Estado: Esperando orden para imprimir

        elif selection == "📊 Reporte Diario":
            from reports.generator import ReportManager
            await ReportManager.send_daily_report(bot, chat_id, store_code)

        elif selection == "🔄 Volver a ingresar tienda":
            await bot.send_message(
                chat_id=chat_id,
                text="🏪 *Ingrese el código de la nueva tienda:*\n\nEjemplo: K025, K180",
                parse_mode="Markdown"
            )
            # Estado: Esperando nueva tienda

        elif selection == "❌ Finalizar consulta":
            await FinalHandler.handle_finalize(bot, message, store_code)

        else:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ *Opción no reconocida*\n\nPor favor, seleccione una opción del menú.",
                parse_mode="Markdown"
            )


class OrderHandler:
    """Manejador de órdenes"""

    @staticmethod
    async def handle_order_input(bot, message, store_code: str, order_number: str):
        """Procesa el número de orden"""

        from core.os_detector import OSDetector
        from database.queries import QueryManager

        os_type, _ = OSDetector.detect_os(store_code)

        if os_type == "windows":
            from database.windows_db import WindowsDatabase
            db = WindowsDatabase()
        else:
            from database.linux_db import LinuxDatabase
            db = LinuxDatabase()

        # Buscar orden
        order_data = db.get_order_status(store_code, order_number)

        if not order_data:
            # Mostrar opciones si no se encuentra
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"❌ *No se encontró la orden {order_number} en la tienda {store_code}.*\n\n¿Qué desea hacer?",
                parse_mode="Markdown",
                reply_markup=MenuHandler.get_action_keyboard()
            )
            return

        # Formatear respuesta
        response_text = f"""
        ✅ *ORDEN ENCONTRADA*

        🏪 Tienda: {store_code}
        📦 Número: {order_data.get('order_number', 'N/A')}
        📅 Fecha: {order_data.get('order_date', 'N/A')}
        🚦 Estado: {order_data.get('status', 'N/A')}
        💰 Total: ${order_data.get('total', 0):,.2f}
        👤 Cliente: {order_data.get('client_name', 'N/A')}

        ⏰ _Consulta realizada: {datetime.now().strftime("%H:%M:%S")}_
        """

        await bot.send_message(
            chat_id=message.chat.id,
            text=response_text,
            parse_mode="Markdown",
            reply_markup=MenuHandler.get_action_keyboard()
        )

        # Log
        logger = BotLogger(store_code)
        logger.log_query(store_code, "ORDER_LOOKUP", "FOUND")


class FinalHandler:
    """Manejador de finalización"""

    @staticmethod
    async def handle_finalize(bot, message, store_code: str = None):
        """Finaliza la consulta actual"""

        final_text = """
        ✅ *CONSULTA FINALIZADA*

        Gracias por utilizar el sistema de gestión KFC.

        Para iniciar una nueva consulta, envíe /start

        ⏰ _La sesión se cerrará automáticamente en 1 minuto._
        """

        await bot.send_message(
            chat_id=message.chat.id,
            text=final_text,
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )

        # Log
        if store_code:
            logger = BotLogger(store_code)
            logger.log_command(message.from_user.id, "SESSION_END")

        # Programar cierre automático (simulado)
        # En implementación real, usaría asyncio.sleep o un scheduler