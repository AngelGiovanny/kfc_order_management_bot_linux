"""
Servicio unificado de imágenes - VERSIÓN CORREGIDA PARA COMANDAS
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
import platform
import sys

from utils.logger import get_logger
from core.selenium_service import selenium_service
from core.linux_image_generator import LinuxImageGenerator
from core.linux_selenium_capture import linux_selenium

logger = get_logger(__name__)

# ============================================================================
# DIAGNÓSTICO DEL SISTEMA AL INICIAR
# ============================================================================

logger.info("=" * 60)
logger.info("DIAGNÓSTICO DEL SISTEMA - ImageService")
logger.info(f"Python: {sys.version}")
logger.info(f"System: {platform.system()}")
logger.info(f"Platform: {platform.platform()}")
logger.info("=" * 60)

# ============================================================================
# INTEGRACIÓN TICKET GENERATOR
# ============================================================================

try:
    from core.ticket_generator import ticket_generator
    HAS_TICKET_GENERATOR = True
    logger.info("✅ TicketGenerator disponible - MÉTODO PRIMARIO")
except ImportError as e:
    HAS_TICKET_GENERATOR = False
    logger.warning(f"⚠️ TicketGenerator no disponible: {e}")

# ============================================================================
# INTEGRACIÓN LINUX JSON IMAGER
# ============================================================================

try:
    from core.linux_json_imager import linux_imager
    HAS_LINUX_JSON_IMAGER = (linux_imager is not None)
    logger.info("✅ LinuxJsonImager disponible para usar JSON de impresión")
except ImportError as e:
    HAS_LINUX_JSON_IMAGER = False
    logger.warning(f"⚠️ LinuxJsonImager no disponible: {e}")


class ImageService:
    """Servicio unificado con TicketGenerator como método primario"""

    def __init__(self):
        # Detección simple pero efectiva del sistema
        self.system = platform.system()
        self.is_linux = (self.system == "Linux")
        self.is_windows = (self.system == "Windows")

        logger.info(f"✅ Sistema detectado: {self.system}")
        logger.info(f"   Linux: {self.is_linux}, Windows: {self.is_windows}")

        # Inicializar generadores
        self.linux_image_generator = LinuxImageGenerator()

        # Directorios
        self.generated_dir = Path("generated_images")
        self.generated_dir.mkdir(exist_ok=True)

        # Cache para optimizar consultas repetidas
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos

        logger.info(f"ImageService inicializado para {self.system}")
        if HAS_TICKET_GENERATOR:
            logger.info("   🎫 TicketGenerator disponible")
        if self.is_linux and HAS_LINUX_JSON_IMAGER:
            logger.info("   🐧 JSON Imager disponible para Linux")

    # ============================================================================
    # MÉTODOS PÚBLICOS PRINCIPALES - TICKETS COMO PRIMARIO
    # ============================================================================

    async def generate_invoice_image(self, store_code: str, invoice_id: str,
                                     is_credit_note: bool = False) -> Optional[bytes]:
        """Genera imagen de factura o nota de crédito - TICKETS PRIMERO"""
        try:
            doc_type = "NOTA_CREDITO" if is_credit_note else "FACTURA"
            logger.info(f"📄 Generando {'Nota de Crédito' if is_credit_note else 'Factura'} {invoice_id}")

            # INTENTO 1: Generar ticket profesional (método preferido)
            if HAS_TICKET_GENERATOR:
                logger.info("1️⃣ Usando TicketGenerator (método primario)...")
                ticket_bytes = await self.generate_ticket_from_json(
                    store_code=store_code,
                    cfac_id=invoice_id,
                    doc_type=doc_type
                )

                if ticket_bytes and len(ticket_bytes) > 100:  # Umbral más bajo para validación
                    logger.info(f"✅ Ticket generado: {len(ticket_bytes):,} bytes")
                    return ticket_bytes
                elif ticket_bytes:
                    logger.warning(f"⚠️ Ticket pequeño pero válido: {len(ticket_bytes)} bytes")
                    return ticket_bytes
                else:
                    logger.warning("⚠️ TicketGenerator no pudo generar imagen")

            # INTENTO 2: Método según sistema operativo (fallback)
            logger.info("2️⃣ Usando método del sistema (fallback)...")

            fallback_bytes = await self._fallback_generate_invoice(
                store_code=store_code,
                cfac_id=invoice_id,
                is_credit_note=is_credit_note
            )

            if fallback_bytes:
                logger.info(f"✅ Fallback generado: {len(fallback_bytes):,} bytes")
                return fallback_bytes

            # INTENTO 3: Crear imagen de error
            logger.warning("⚠️ Todos los métodos fallaron, creando imagen de error")
            return self._create_error_image(
                doc_type=doc_type,
                cfac_id=invoice_id,
                store_code=store_code,
                message="No se pudo generar el documento"
            )

        except Exception as e:
            logger.error(f"❌ Error en generate_invoice_image: {e}", exc_info=True)
            return self._create_error_image(
                doc_type="NOTA_CREDITO" if is_credit_note else "FACTURA",
                cfac_id=invoice_id,
                store_code=store_code,
                error=str(e)[:100]
            )

    async def generate_comanda_image(self, store_code: str, invoice_id: str) -> Optional[bytes]:
        """Genera imagen de comanda - VERSIÓN MEJORADA"""
        try:
            logger.info(f"🍗 Generando Comanda para factura {invoice_id}")

            # INTENTO 1: Generar ticket profesional
            if HAS_TICKET_GENERATOR:
                logger.info("1️⃣ Usando TicketGenerator (método primario)...")
                ticket_bytes = await self.generate_ticket_from_json(
                    store_code=store_code,
                    cfac_id=invoice_id,
                    doc_type="COMANDA"
                )

                if ticket_bytes and len(ticket_bytes) > 100:
                    logger.info(f"✅ Ticket generado: {len(ticket_bytes):,} bytes")
                    return ticket_bytes
                elif ticket_bytes:
                    logger.warning(f"⚠️ Ticket pequeño pero válido: {len(ticket_bytes)} bytes")
                    return ticket_bytes

            # INTENTO 2: Método según sistema operativo (fallback)
            logger.info("2️⃣ Usando método del sistema (fallback)...")

            fallback_bytes = await self._fallback_generate_comanda(
                store_code=store_code,
                cfac_id=invoice_id
            )

            if fallback_bytes:
                logger.info(f"✅ Fallback generado: {len(fallback_bytes):,} bytes")
                return fallback_bytes

            # INTENTO 3: Crear imagen de error específica para comanda
            logger.warning("⚠️ Todos los métodos fallaron, creando imagen de error")
            return self._create_comanda_error_image(
                cfac_id=invoice_id,
                store_code=store_code,
                message="No se pudo generar la comanda. Verifique que exista una orden asociada."
            )

        except Exception as e:
            logger.error(f"❌ Error en generate_comanda_image: {e}", exc_info=True)
            return self._create_comanda_error_image(
                cfac_id=invoice_id,
                store_code=store_code,
                error=str(e)[:100]
            )

    # ============================================================================
    # MÉTODO CORREGIDO PARA GENERAR COMANDAS EN WINDOWS
    # ============================================================================

    async def _generate_windows_comanda(self, store_code: str, cfac_id: str) -> Optional[str]:
        """Estrategia específica para comandas en Windows - VERSIÓN CORREGIDA"""
        logger.info(f"🪟 Windows: Generando Comanda para factura {cfac_id}")

        # Obtener order_id
        order_id = await self._get_order_id_from_db(store_code, cfac_id)
        if not order_id:
            logger.warning(f"No se encontró comanda para factura {cfac_id}")
            return None

        logger.info(f"✅ Order ID encontrado: {order_id}")

        # Generar URL de comanda CORREGIDA - CAMBIO PRINCIPAL: tiposervicio -> tipoServicio
        store_number = self._extract_store_number(store_code)

        # URL CORREGIDA según tu ejemplo (tipoServicio con "S" mayúscula)
        url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

        logger.info(f"🌐 URL de comanda generada: {url}")

        # Capturar con Selenium
        logger.info("📸 Capturando pantalla con Selenium...")
        screenshot = await self._capture_with_selenium(url)

        if not screenshot:
            logger.error("❌ No se pudo capturar la pantalla")

            # Intentar con URL alternativa (por si hay variaciones)
            logger.info("🔄 Intentando con URL alternativa...")
            alt_url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}"
            screenshot = await self._capture_with_selenium(alt_url)

            if not screenshot:
                logger.error("❌ URL alternativa también falló")
                return None

        # Guardar imagen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"win_comanda_{store_code}_{cfac_id}_{timestamp}.png"
        output_path = self.generated_dir / filename

        try:
            with open(output_path, 'wb') as f:
                f.write(screenshot)

            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Comanda Windows generada: {output_path} ({file_size:,} bytes)")

            # Verificar que la imagen no esté en blanco
            if file_size < 5000:  # Imagen muy pequeña probablemente esté en blanco
                logger.warning(f"⚠️ Imagen sospechosamente pequeña: {file_size} bytes")
                # Intentar método alternativo
                return await self._try_alternative_comanda_method(store_code, cfac_id, order_id)

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Error guardando imagen: {e}")
            return None

    async def _try_alternative_comanda_method(self, store_code: str, cfac_id: str, order_id: str) -> Optional[str]:
        """Método alternativo para generar comandas si el principal falla"""
        logger.info("🔄 Probando método alternativo para comanda...")

        store_number = self._extract_store_number(store_code)

        # Probar diferentes combinaciones de parámetros
        url_variations = [
            # Tu ejemplo original (con tipoServicio)
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1",
            # Versión con tiposervicio (minúscula - la original que fallaba)
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tiposervicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1",
            # Sin algunos parámetros
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=2",
            # Solo order_id
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}",
            # Con diferentes valores de tipoServicio
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=1",
            f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=0",
        ]

        for i, url in enumerate(url_variations, 1):
            logger.info(f"  {i}. Probando URL: {url[:100]}...")
            screenshot = await self._capture_with_selenium(url)

            if screenshot and len(screenshot) > 10000:  # Imagen válida
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"win_comanda_alt{i}_{store_code}_{cfac_id}_{timestamp}.png"
                output_path = self.generated_dir / filename

                with open(output_path, 'wb') as f:
                    f.write(screenshot)

                logger.info(f"  ✅ Método alternativo {i} funcionó: {len(screenshot):,} bytes")
                return str(output_path)

        logger.error("❌ Todos los métodos alternativos fallaron")
        return None

    # ============================================================================
    # MÉTODO ACTUALIZADO PARA LINUX COMANDAS
    # ============================================================================

    async def _generate_linux_comanda(self, store_code: str, cfac_id: str) -> Optional[str]:
        """Estrategia específica para comandas en Linux - VERSIÓN ACTUALIZADA"""
        logger.info(f"🐧 Linux: Generando Comanda para factura {cfac_id}")

        # INTENTO 1: Usar JSON de impresión
        if HAS_LINUX_JSON_IMAGER:
            logger.info("1️⃣ Intentando con JSON de impresión...")
            image_path = await self._try_json_method_linux(store_code, cfac_id, "COMANDA")
            if image_path:
                return image_path

        # INTENTO 2: Si estamos en Linux pero queremos usar Selenium también
        logger.info("2️⃣ Intentando con Selenium en Linux...")

        # Obtener order_id
        order_id = await self._get_order_id_from_db(store_code, cfac_id)
        if not order_id:
            logger.warning(f"No se encontró comanda para factura {cfac_id}")
            return None

        # Generar URL (similar a Windows pero para Linux)
        store_number = self._extract_store_number(store_code)
        # USANDO LA URL CORREGIDA (tipoServicio en lugar de tiposervicio)
        url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={order_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

        logger.info(f"🌐 URL para Linux: {url}")

        # Capturar con Selenium Linux
        if hasattr(linux_selenium, 'capture_url_image'):
            screenshot = await linux_selenium.capture_url_image(url)

            if screenshot:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"linux_comanda_selenium_{store_code}_{cfac_id}_{timestamp}.png"
                output_path = self.generated_dir / filename

                with open(output_path, 'wb') as f:
                    f.write(screenshot)

                logger.info(f"✅ Comanda Linux (Selenium) generada: {output_path}")
                return str(output_path)

        # INTENTO 3: Usar LinuxImageGenerator
        logger.info("3️⃣ Usando LinuxImageGenerator...")
        return await self._generate_comanda_with_generator(store_code, cfac_id)

    # ============================================================================
    # IMAGEN DE ERROR ESPECÍFICA PARA COMANDAS
    # ============================================================================

    def _create_comanda_error_image(self, cfac_id: str, store_code: str,
                                  message: str = "", error: str = "") -> bytes:
        """Crea una imagen de error específica para comandas"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io

            # Crear imagen
            width, height = 500, 300
            img = Image.new('RGB', (width, height), color=(255, 248, 225))  # Fondo amarillo claro
            draw = ImageDraw.Draw(img)

            # Fuentes
            try:
                font_title = ImageFont.truetype("arial.ttf", 24)
                font_text = ImageFont.truetype("arial.ttf", 16)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()
                font_small = ImageFont.load_default()

            y = 40

            # Título con icono
            title = "⚠️ ERROR EN COMANDA"
            draw.text((width//2, y), title, fill=(220, 53, 69), font=font_title, anchor="mm")
            y += 50

            # Información
            info_lines = [
                f"Factura: {cfac_id}",
                f"Tienda: {store_code}",
                f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                "",
                "POSIBLE CAUSA:",
                "- No existe orden asociada a la factura",
                "- La orden fue eliminada",
                "- Error de conexión con la impresora"
            ]

            for line in info_lines:
                draw.text((50, y), line, fill=(0, 0, 0), font=font_text if y < 180 else font_small)
                y += 30 if y < 180 else 25

            # Mensaje adicional
            if message:
                y += 10
                draw.text((width//2, y), message, fill=(108, 117, 125), font=font_text, anchor="mm")

            if error:
                y += 30
                error_text = f"Error técnico: {error[:50]}..." if len(error) > 50 else f"Error: {error}"
                draw.text((width//2, y), error_text, fill=(220, 53, 69), font=font_small, anchor="mm")

            # Convertir a bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True, quality=90)

            logger.info(f"✅ Imagen de error para comanda creada: {len(img_bytes.getvalue()):,} bytes")
            return img_bytes.getvalue()

        except Exception as e:
            logger.error(f"Error creando imagen de error para comanda: {e}")
            # Fallback simple
            try:
                from PIL import Image, ImageDraw
                import io
                img = Image.new('RGB', (200, 100), color=(255, 248, 225))
                draw = ImageDraw.Draw(img)
                draw.text((100, 50), "ERROR COMANDA", fill=(220, 53, 69), anchor="mm")
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                return img_bytes.getvalue()
            except:
                # Último recurso
                return b''

    # ============================================================================
    # MÉTODOS DE FALLBACK (sin cambios)
    # ============================================================================

    async def _fallback_generate_invoice(self, store_code: str, cfac_id: str,
                                       is_credit_note: bool = False) -> Optional[bytes]:
        """Método de fallback para generar factura"""
        try:
            if self.is_linux:
                # Linux: usar métodos específicos
                image_path = await self._generate_linux_invoice(
                    store_code=store_code,
                    cfac_id=cfac_id,
                    is_credit_note=is_credit_note
                )
            else:
                # Windows: intentar con Selenium
                image_path = await self._generate_windows_invoice(
                    store_code=store_code,
                    cfac_id=cfac_id,
                    is_credit_note=is_credit_note
                )

            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    return f.read()

            return None

        except Exception as e:
            logger.error(f"Error en fallback factura: {e}")
            return None

    async def _fallback_generate_comanda(self, store_code: str, cfac_id: str) -> Optional[bytes]:
        """Método de fallback para generar comanda"""
        try:
            if self.is_linux:
                image_path = await self._generate_linux_comanda(
                    store_code=store_code,
                    cfac_id=cfac_id
                )
            else:
                image_path = await self._generate_windows_comanda(
                    store_code=store_code,
                    cfac_id=cfac_id
                )

            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    return f.read()

            return None

        except Exception as e:
            logger.error(f"Error en fallback comanda: {e}")
            return None

    # ============================================================================
    # CREACIÓN DE IMÁGENES DE ERROR GENERAL (sin cambios)
    # ============================================================================

    def _create_error_image(self, doc_type: str, cfac_id: str,
                          store_code: str, message: str = "",
                          error: str = "") -> bytes:
        """Crea una imagen de error cuando todo falla"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io

            # Crear imagen
            width, height = 400, 250
            img = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Fuentes (con fallback)
            try:
                font_title = ImageFont.truetype("arial.ttf", 20)
                font_text = ImageFont.truetype("arial.ttf", 14)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()

            y = 30

            # Título
            title = "⚠️ ERROR DEL SISTEMA"
            draw.text((width//2, y), title, fill=(220, 53, 69), font=font_title, anchor="mm")
            y += 40

            # Información del documento
            doc_names = {
                "FACTURA": "Factura",
                "NOTA_CREDITO": "Nota de Crédito",
                "COMANDA": "Comanda"
            }
            doc_name = doc_names.get(doc_type, "Documento")

            info_lines = [
                f"{doc_name}: {cfac_id}",
                f"Tienda: {store_code}",
                f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ]

            for line in info_lines:
                draw.text((width//2, y), line, fill=(0, 0, 0), font=font_text, anchor="mm")
                y += 25

            y += 10

            # Mensaje
            if message:
                draw.text((width//2, y), message, fill=(108, 117, 125), font=font_text, anchor="mm")
                y += 25

            if error:
                error_text = f"Detalle: {error[:40]}..." if len(error) > 40 else f"Detalle: {error}"
                draw.text((width//2, y), error_text, fill=(220, 53, 69), font=font_text, anchor="mm")

            # Pie de página
            draw.text((width//2, height - 20), "Sistema KFC - Generado automáticamente",
                     fill=(108, 117, 125), font=font_text, anchor="mm")

            # Convertir a bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True, quality=90)

            logger.info(f"✅ Imagen de error creada: {len(img_bytes.getvalue()):,} bytes")
            return img_bytes.getvalue()

        except Exception as e:
            logger.error(f"Error creando imagen de error: {e}")
            # Último recurso: imagen en blanco mínima
            from PIL import Image
            import io
            img = Image.new('RGB', (100, 50), color=(255, 255, 255))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            return img_bytes.getvalue()

    # ============================================================================
    # MÉTODO PRIMARIO: GENERACIÓN DE TICKETS DESDE JSON (sin cambios)
    # ============================================================================

    async def generate_ticket_from_json(self, store_code: str, cfac_id: str,
                                      doc_type: str = "FACTURA") -> Optional[bytes]:
        """Genera ticket tipo recibo desde datos de la BD"""
        try:
            logger.info(f"🎫 Generando ticket {doc_type} para {cfac_id}")

            # Verificar cache primero
            cache_key = f"{store_code}_{cfac_id}_{doc_type}"
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if datetime.now().timestamp() - cached_data['timestamp'] < self._cache_timeout:
                    logger.info(f"📦 Usando datos en caché para {cfac_id}")
                    data = cached_data['data']
                else:
                    # Cache expirado
                    del self._cache[cache_key]
                    data = await self._get_structured_data(store_code, cfac_id, doc_type)
            else:
                data = await self._get_structured_data(store_code, cfac_id, doc_type)

            if not data:
                logger.error(f"No se pudieron obtener datos para {cfac_id}")
                return None

            # Guardar en cache
            self._cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now().timestamp()
            }

            # Generar ticket según tipo
            doc_type_upper = doc_type.upper()
            if doc_type_upper == "FACTURA":
                return ticket_generator.generate_invoice_ticket(data)
            elif doc_type_upper == "NOTA_CREDITO":
                data['is_credit_note'] = True
                return ticket_generator.generate_invoice_ticket(data)
            elif doc_type_upper == "COMANDA":
                return ticket_generator.generate_comanda_ticket(data)
            else:
                logger.error(f"Tipo de documento no soportado: {doc_type}")
                return None

        except Exception as e:
            logger.error(f"Error generando ticket: {e}", exc_info=True)
            return None

    # ============================================================================
    # MÉTODOS RESTANTES (sin cambios)
    # ============================================================================

    async def _get_structured_data(self, store_code: str, cfac_id: str,
                                 doc_type: str) -> Optional[Dict]:
        """Obtiene datos estructurados para el ticket desde la BD"""
        try:
            from config.database import db_manager

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"No hay conexión a BD para {store_code}")
                return None

            cursor = connection.cursor()

            try:
                if doc_type.upper() in ["FACTURA", "NOTA_CREDITO"]:
                    return await self._get_invoice_data(cursor, cfac_id)
                elif doc_type.upper() == "COMANDA":
                    return await self._get_comanda_data(cursor, store_code, cfac_id)
                else:
                    return None
            finally:
                cursor.close()
                connection.close()

        except Exception as e:
            logger.error(f"Error obteniendo datos estructurados: {e}", exc_info=True)
            return None

    async def _get_invoice_data(self, cursor, cfac_id: str) -> Optional[Dict]:
        """Obtiene datos de factura desde la BD"""
        try:
            # Consulta mejorada con manejo de errores
            query = """
                SELECT TOP 1 
                    COALESCE(cfac_id, id, numero_factura) as numero,
                    COALESCE(cfac_fecha, fecha, GETDATE()) as fecha,
                    COALESCE(cli_nombre, 'Consumidor Final') as cliente,
                    COALESCE(cli_ruc, '0000000000') as ruc,
                    COALESCE(cli_direccion, '') as direccion,
                    COALESCE(cli_telefono, '') as telefono,
                    COALESCE(total, 0) as total,
                    COALESCE(subtotal, 0) as subtotal,
                    COALESCE(iva, 0) as iva,
                    COALESCE(forma_pago, 'EFECTIVO') as forma_pago,
                    COALESCE(observaciones, '') as observaciones
                FROM Cabecera_Factura 
                WHERE cfac_id = ? OR id = ? OR numero_factura = ?
            """

            cursor.execute(query, (cfac_id, cfac_id, cfac_id))
            result = cursor.fetchone()

            if not result:
                logger.warning(f"No se encontró factura {cfac_id}")
                return None

            # Construir datos básicos
            invoice_data = {
                'numero': str(result[0]),
                'fecha': self._format_date(result[1]),
                'cliente': str(result[2]),
                'ruc': str(result[3]),
                'direccion': str(result[4]),
                'telefono': str(result[5]),
                'total': float(result[6] or 0),
                'subtotal': float(result[7] or 0),
                'iva': float(result[8] or 0),
                'forma_pago': str(result[9]),
                'observaciones': str(result[10]),
                'detalles': [],
                'tienda': 'KFC'  # Valor por defecto
            }

            # Obtener detalles
            details_query = """
                SELECT 
                    COALESCE(descripcion, 'Producto') as producto,
                    COALESCE(cantidad, 1) as cantidad,
                    COALESCE(precio_unitario, 0) as precio,
                    COALESCE(subtotal, 0) as subtotal
                FROM Detalle_Factura 
                WHERE cfac_id = ? OR id_factura = ?
                ORDER BY item_order, id
            """

            cursor.execute(details_query, (cfac_id, cfac_id))
            detalles = cursor.fetchall()

            for detalle in detalles:
                invoice_data['detalles'].append({
                    'producto': str(detalle[0]),
                    'cantidad': float(detalle[1]),
                    'precio': float(detalle[2]),
                    'subtotal': float(detalle[3])
                })

            # Calcular valores si no existen
            if not invoice_data['subtotal'] and invoice_data['detalles']:
                invoice_data['subtotal'] = sum(item['subtotal'] for item in invoice_data['detalles'])

            if not invoice_data['iva'] and invoice_data['subtotal']:
                invoice_data['iva'] = round(invoice_data['subtotal'] * 0.12, 2)

            logger.info(f"✅ Datos factura obtenidos: {len(invoice_data['detalles'])} items")
            return invoice_data

        except Exception as e:
            logger.error(f"Error obteniendo datos factura: {e}")
            return None

    async def _get_comanda_data(self, cursor, store_code: str, cfac_id: str) -> Optional[Dict]:
        """Obtiene datos de comanda desde la BD"""
        try:
            # Primero obtener order_id
            order_query = """
                SELECT TOP 1 IDCabeceraOrdenPedido 
                FROM Cabecera_Factura 
                WHERE cfac_id = ? OR id = ?
            """

            cursor.execute(order_query, (cfac_id, cfac_id))
            order_result = cursor.fetchone()

            if not order_result or not order_result[0]:
                logger.warning(f"No se encontró comanda para factura {cfac_id}")
                return None

            order_id = str(order_result[0])

            # Obtener datos de comanda
            comanda_query = """
                SELECT TOP 1 
                    COALESCE(odp_id, id, numero_orden) as comanda_id,
                    COALESCE(fecha_creacion, GETDATE()) as fecha,
                    COALESCE(cliente_nombre, 'Cliente') as cliente,
                    COALESCE(cliente_telefono, '') as telefono,
                    COALESCE(cliente_direccion, '') as direccion,
                    COALESCE(estado, 'PENDIENTE') as estado,
                    COALESCE(forma_pago, 'EFECTIVO') as forma_pago,
                    COALESCE(cajero, 'SISTEMA') as cajero,
                    COALESCE(observaciones, '') as observaciones
                FROM Cabecera_OrdenPedido 
                WHERE odp_id = ? OR id = ? OR numero_orden = ?
            """

            cursor.execute(comanda_query, (order_id, order_id, order_id))
            result = cursor.fetchone()

            if not result:
                return None

            # Construir datos
            comanda_data = {
                'comanda_id': str(result[0]),
                'fecha': self._format_date(result[1]),
                'cliente': str(result[2]),
                'telefono': str(result[3]),
                'direccion': str(result[4]),
                'estado': str(result[5]),
                'forma_pago': str(result[6]),
                'cajero': str(result[7]),
                'observaciones': str(result[8]),
                'items': [],
                'tienda': 'KFC'
            }

            # Obtener items
            items_query = """
                SELECT 
                    COALESCE(producto_desc, 'Producto') as producto,
                    COALESCE(cantidad, 1) as cantidad,
                    COALESCE(observaciones, '') as observacion
                FROM Detalle_OrdenPedido 
                WHERE odp_id = ? OR id_orden = ?
                ORDER BY item_order, id
            """

            cursor.execute(items_query, (order_id, order_id))
            items = cursor.fetchall()

            for item in items:
                comanda_data['items'].append({
                    'producto': str(item[0]),
                    'cantidad': float(item[1]),
                    'observacion': str(item[2])
                })

            logger.info(f"✅ Datos comanda obtenidos: {len(comanda_data['items'])} items")
            return comanda_data

        except Exception as e:
            logger.error(f"Error obteniendo datos comanda: {e}")
            return None

    def _format_date(self, date_value) -> str:
        """Formatea fecha a string legible"""
        try:
            if hasattr(date_value, 'strftime'):
                return date_value.strftime('%d/%m/%Y %H:%M')
            else:
                return str(date_value)[:19]  # Tomar primeros 19 caracteres
        except:
            return str(date_value)

    # ============================================================================
    # MÉTODOS EXISTENTES (se mantienen para compatibilidad)
    # ============================================================================

    async def _generate_linux_invoice(self, store_code: str, cfac_id: str,
                                     is_credit_note: bool = False) -> Optional[str]:
        """Estrategia específica para Linux"""
        logger.info(f"🐧 Linux: Generando {'Nota de Crédito' if is_credit_note else 'Factura'} {cfac_id}")
        doc_type = "NOTA_CREDITO" if is_credit_note else "FACTURA"

        # INTENTO 1: Usar JSON de impresión
        if HAS_LINUX_JSON_IMAGER:
            logger.info("1️⃣ Intentando con JSON de impresión...")
            image_path = await self._try_json_method_linux(store_code, cfac_id, doc_type)
            if image_path:
                return image_path

        # INTENTO 2: Usar LinuxImageGenerator
        logger.info("2️⃣ Usando LinuxImageGenerator...")
        return await self._generate_with_linux_generator(
            store_code=store_code,
            cfac_id=cfac_id,
            doc_type=doc_type
        )

    async def _generate_windows_invoice(self, store_code: str, cfac_id: str,
                                       is_credit_note: bool = False) -> Optional[str]:
        """Estrategia específica para Windows"""
        logger.info(f"🪟 Windows: Generando {'Nota de Crédito' if is_credit_note else 'Factura'} {cfac_id}")

        # Generar URL
        url = self._generate_windows_url(store_code, cfac_id, is_credit_note)
        if not url:
            logger.error("No se pudo generar URL")
            return None

        # Capturar con Selenium
        screenshot = await self._capture_with_selenium(url)
        if not screenshot:
            return None

        # Guardar imagen
        doc_type = "nota_credito" if is_credit_note else "factura"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"win_{doc_type}_{store_code}_{cfac_id}_{timestamp}.png"
        output_path = self.generated_dir / filename

        with open(output_path, 'wb') as f:
            f.write(screenshot)

        logger.info(f"✅ Imagen Windows generada: {output_path}")
        return str(output_path)

    # ============================================================================
    # MÉTODOS AUXILIARES (con mejoras menores)
    # ============================================================================

    async def _try_json_method_linux(self, store_code: str, cfac_id: str,
                                   doc_type: str) -> Optional[str]:
        """Intenta usar JSON de impresión en Linux"""
        try:
            if not HAS_LINUX_JSON_IMAGER:
                return None

            logger.info(f"   📋 Buscando JSON para {cfac_id}...")

            # Obtener JSON
            json_data = linux_imager.get_json_any_method(store_code, cfac_id)
            if not json_data:
                logger.warning(f"   ⚠️ No se encontró JSON para {cfac_id}")
                return None

            logger.info(f"   ✅ JSON encontrado")

            # Generar imagen desde JSON
            logger.info(f"   🖼️ Generando imagen desde JSON...")
            image_bytes = linux_imager.generate_image_from_json(
                json_data=json_data,
                store_code=store_code,
                cfac_id=cfac_id,
                doc_type=doc_type
            )

            if not image_bytes:
                logger.error("   ❌ No se pudo generar imagen desde JSON")
                return None

            # Guardar imagen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"json_{doc_type.lower()}_{store_code}_{cfac_id}_{timestamp}.png"
            output_path = self.generated_dir / filename

            with open(output_path, 'wb') as f:
                f.write(image_bytes)

            logger.info(f"   ✅ Imagen JSON guardada: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"   ❌ Error en método JSON: {e}")
            return None

    async def _generate_from_database(self, store_code: str, cfac_id: str,
                                    doc_type: str) -> Optional[str]:
        """Genera imagen consultando datos desde BD"""
        # Este método debe implementarse según tus necesidades
        # Por ahora retorna None para usar otros métodos
        return None

    async def _generate_with_linux_generator(self, store_code: str, cfac_id: str,
                                           doc_type: str) -> Optional[str]:
        """Genera imagen usando LinuxImageGenerator"""
        try:
            if not hasattr(self.linux_image_generator, 'generate_image'):
                return None

            logger.info(f"   🖼️ Usando LinuxImageGenerator para {doc_type}...")
            image_bytes = await self.linux_image_generator.generate_image(
                store_code=store_code,
                cfac_id=cfac_id,
                doc_type=doc_type
            )

            if not image_bytes:
                return None

            # Guardar imagen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linux_{doc_type.lower()}_{store_code}_{cfac_id}_{timestamp}.png"
            output_path = self.generated_dir / filename

            with open(output_path, 'wb') as f:
                f.write(image_bytes)

            logger.info(f"   ✅ Imagen Linux generada: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"   ❌ Error con LinuxImageGenerator: {e}")
            return None

    async def _generate_comanda_from_database(self, store_code: str, cfac_id: str) -> Optional[str]:
        """Genera imagen de comanda desde BD"""
        # Implementar según necesidades
        return None

    async def _generate_comanda_with_generator(self, store_code: str, cfac_id: str) -> Optional[str]:
        """Genera comanda usando LinuxImageGenerator"""
        return await self._generate_with_linux_generator(store_code, cfac_id, "COMANDA")

    def _generate_windows_url(self, store_code: str, cfac_id: str,
                            is_credit_note: bool = False) -> Optional[str]:
        """Genera URL para Windows"""
        try:
            store_number = self._extract_store_number(store_code)
            if is_credit_note:
                return f"http://10.101.{store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=N"
            else:
                return f"http://10.101.{store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=F"
        except Exception as e:
            logger.error(f"Error generando URL Windows: {e}")
            return None

    async def _capture_with_selenium(self, url: str) -> Optional[bytes]:
        """Captura pantalla usando Selenium - VERSIÓN MEJORADA"""
        try:
            logger.info(f"🌐 Capturando URL: {url[:80]}...")

            # Determinar qué driver usar
            if self.is_linux and hasattr(linux_selenium, 'driver') and linux_selenium.driver:
                logger.info("   Usando driver Linux Selenium")
                return await linux_selenium.capture_url_image(url)
            elif hasattr(selenium_service, 'driver') and selenium_service.driver:
                logger.info("   Usando driver Windows Selenium")
                return await selenium_service.capture_url_image(url)
            else:
                logger.error("   ❌ Selenium no disponible")
                return None

        except Exception as e:
            logger.error(f"❌ Error capturando con Selenium: {e}", exc_info=True)
            return None

    def _extract_store_number(self, store_code: str) -> str:
        """Extrae solo los números del store_code"""
        import re
        numbers = re.findall(r'\d+', store_code)
        if numbers:
            return str(int(numbers[0]))
        return "0"

    async def _get_order_id_from_db(self, store_code: str, cfac_id: str) -> Optional[str]:
        """Obtiene order_id desde la base de datos para comandas - VERSIÓN MEJORADA"""
        try:
            from config.database import db_manager

            logger.info(f"🔍 Buscando order_id para factura {cfac_id} en tienda {store_code}")

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"❌ No hay conexión a BD para {store_code}")
                return None

            cursor = connection.cursor()
            try:
                # Probar diferentes columnas posibles
                queries = [
                    ("SELECT TOP 1 IDCabeceraOrdenPedido FROM Cabecera_Factura WHERE cfac_id = ?", [cfac_id]),
                    ("SELECT TOP 1 IDCabeceraOrdenPedido FROM Cabecera_Factura WHERE id = ?", [cfac_id]),
                    ("SELECT TOP 1 IDCabeceraOrdenPedido FROM Cabecera_Factura WHERE numero_factura = ?", [cfac_id]),
                    ("SELECT TOP 1 odp_id FROM Cabecera_OrdenPedido WHERE id_factura = ?", [cfac_id]),
                ]

                order_id = None
                for query, params in queries:
                    try:
                        cursor.execute(query, params)
                        row = cursor.fetchone()
                        if row and row[0]:
                            order_id = str(row[0]).strip()
                            logger.info(f"✅ Order ID encontrado con query: {query.split()[3]}")
                            break
                    except Exception as query_error:
                        logger.debug(f"Query falló: {query_error}")

                if order_id:
                    # Verificar formato del order_id
                    if len(order_id) < 5:
                        logger.warning(f"⚠️ Order ID muy corto: {order_id}")

                    # Log del formato
                    if '-' in order_id:
                        logger.info(f"📋 Order ID parece ser GUID: {order_id}")
                    elif order_id.isdigit():
                        logger.info(f"📋 Order ID numérico: {order_id}")
                    else:
                        logger.info(f"📋 Order ID: {order_id}")

                    return order_id
                else:
                    logger.warning(f"⚠️ No se encontró order_id para factura {cfac_id}")

                    # Intentar buscar en otras tablas
                    try:
                        cursor.execute("""
                            SELECT TOP 1 odp_id 
                            FROM Cabecera_OrdenPedido 
                            WHERE observaciones LIKE ? OR cliente_nombre LIKE ?
                        """, [f'%{cfac_id}%', f'%{cfac_id}%'])

                        row = cursor.fetchone()
                        if row and row[0]:
                            order_id = str(row[0]).strip()
                            logger.info(f"✅ Order ID encontrado en observaciones: {order_id}")
                            return order_id
                    except:
                        pass

                    return None

            finally:
                cursor.close()
                connection.close()

        except Exception as e:
            logger.error(f"❌ Error obteniendo order_id: {e}", exc_info=True)
            return None

    # ============================================================================
    # MÉTODOS DE COMPATIBILIDAD
    # ============================================================================

    def is_available(self) -> bool:
        """Verifica disponibilidad del servicio"""
        return True

    def is_selenium_available(self) -> bool:
        """Verifica disponibilidad de Selenium"""
        if self.is_linux and hasattr(linux_selenium, 'driver'):
            return linux_selenium.driver is not None
        elif hasattr(selenium_service, 'driver'):
            return selenium_service.driver is not None
        return False

    async def url_to_image(self, url: str) -> Optional[bytes]:
        """Convierte URL a imagen"""
        try:
            screenshot = await self._capture_with_selenium(url)
            return screenshot
        except Exception as e:
            logger.error(f"Error en url_to_image: {e}")
            return None

    # ============================================================================
    # MÉTODOS DE MANTENIMIENTO
    # ============================================================================

    def close_selenium(self):
        """Cierra instancias de Selenium"""
        try:
            if self.is_linux and hasattr(linux_selenium, 'close'):
                linux_selenium.close()
            if hasattr(selenium_service, 'close'):
                selenium_service.close()
            logger.info("Instancias de Selenium cerradas")
        except Exception as e:
            logger.error(f"Error cerrando Selenium: {e}")

    def cleanup_generated_files(self, max_age_hours: int = 24):
        """Limpia archivos generados antiguos"""
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            for file_path in self.generated_dir.glob("*.png"):
                if os.path.exists(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            logger.debug(f"Archivo antiguo eliminado: {file_path}")
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error limpiando archivos: {e}")

    def clear_cache(self):
        """Limpia el cache de datos"""
        self._cache.clear()
        logger.info("Cache limpiado")


# Instancia global
image_service = ImageService()