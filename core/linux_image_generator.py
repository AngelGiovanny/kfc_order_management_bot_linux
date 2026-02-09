"""
Sistema de generación de imágenes para KFC - Linux/Windows compatible
"""

import io
import os
import logging
import platform
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image, ImageDraw, ImageFont
from utils.logger import get_logger

logger = get_logger(__name__)


class LinuxImageGenerator:
    """Generador de imágenes para facturas y comandas KFC"""

    def __init__(self):
        self.system = platform.system()
        self.font_cache = {}
        self._init_fonts()
        logger.info(f"Generador de imágenes inicializado para {self.system}")

    def _init_fonts(self):
        """Inicializa las fuentes disponibles"""
        self.available_fonts = []

        # Rutas comunes de fuentes
        font_dirs = []

        if self.system == "Windows":
            font_dirs = [
                "C:\\Windows\\Fonts",
                os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts")
            ]
        elif self.system == "Linux":
            font_dirs = [
                "/usr/share/fonts/truetype/dejavu",
                "/usr/share/fonts/truetype/liberation",
                "/usr/share/fonts/truetype/ubuntu",
                "/usr/share/fonts/TTF",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts")
            ]

        # Extensiones de fuentes
        font_extensions = ['.ttf', '.otf']

        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                try:
                    for root, dirs, files in os.walk(font_dir):
                        for file in files:
                            if any(file.lower().endswith(ext) for ext in font_extensions):
                                font_path = os.path.join(root, file)
                                self.available_fonts.append(font_path)
                except Exception as e:
                    logger.warning(f"No se pudo escanear {font_dir}: {e}")

        # Fuentes por defecto a intentar
        default_fonts = [
            "arial.ttf",
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
            "Ubuntu-R.ttf"
        ]

        for font_name in default_fonts:
            try:
                # Intentar cargar por nombre
                font = ImageFont.truetype(font_name, 10)
                self.available_fonts.append(font_name)
            except:
                pass

        logger.info(f"Fuentes disponibles: {len(self.available_fonts)}")

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Obtiene una fuente del tamaño especificado"""
        cache_key = f"{size}_{bold}"

        if cache_key in self.font_cache:
            return self.font_cache[cache_key]

        # Intentar fuentes específicas primero
        preferred_fonts = []

        if bold:
            if self.system == "Windows":
                preferred_fonts = ["arialbd.ttf", "calibrib.ttf"]
            else:
                preferred_fonts = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
        else:
            if self.system == "Windows":
                preferred_fonts = ["arial.ttf", "calibri.ttf", "tahoma.ttf"]
            else:
                preferred_fonts = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Ubuntu-R.ttf"]

        # Intentar fuentes preferidas
        for font_name in preferred_fonts:
            for font_path in self.available_fonts:
                if font_name.lower() in font_path.lower():
                    try:
                        font = ImageFont.truetype(font_path, size)
                        self.font_cache[cache_key] = font
                        return font
                    except Exception as e:
                        logger.debug(f"No se pudo cargar {font_path}: {e}")

        # Intentar cualquier fuente disponible
        for font_path in self.available_fonts[:5]:  # Solo las primeras 5
            try:
                font = ImageFont.truetype(font_path, size)
                self.font_cache[cache_key] = font
                logger.info(f"Usando fuente: {os.path.basename(font_path)} tamaño {size}")
                return font
            except Exception as e:
                continue

        # Fallback a fuente por defecto
        logger.warning("Usando fuente por defecto de PIL")
        font = ImageFont.load_default()
        self.font_cache[cache_key] = font
        return font

    def _draw_text_with_outline(self, draw, position, text, font, text_color, outline_color, outline_width=2):
        """Dibuja texto con borde/contorno"""
        x, y = position

        # Dibujar contorno
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

        # Dibujar texto principal
        draw.text(position, text, font=font, fill=text_color)

    async def generate_invoice_image_from_data(self, invoice_data: Dict[str, Any]) -> Optional[io.BytesIO]:
        """Genera imagen de factura a partir de datos estructurados"""
        try:
            logger.info("Generando imagen de factura desde datos")

            # Extraer datos
            store_code = invoice_data.get('store_code', 'K000')
            invoice_id = invoice_data.get('invoice_id', 'N/A')
            cliente = invoice_data.get('cliente', 'CONSUMIDOR FINAL')
            ruc = invoice_data.get('ruc', '9999999999999')
            fecha = invoice_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
            total = invoice_data.get('total', '0.00')
            subtotal = invoice_data.get('subtotal', '0.00')
            iva = invoice_data.get('iva', '0.00')
            detalles = invoice_data.get('detalles', [])
            forma_pago = invoice_data.get('forma_pago', 'EFECTIVO')
            cajero = invoice_data.get('cajero', 'SISTEMA')
            orden = invoice_data.get('orden', 'N/A')

            # Dimensiones de la imagen
            width, height = 800, 1200
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)

            # Fuentes
            font_large = self._get_font(24, bold=True)
            font_medium = self._get_font(18)
            font_normal = self._get_font(14)
            font_small = self._get_font(12)
            font_xsmall = self._get_font(10)

            # ENCABEZADO - Rojo KFC
            header_height = 150
            draw.rectangle([0, 0, width, header_height], fill=(227, 0, 43))  # Rojo KFC

            # Logo KFC (texto)
            self._draw_text_with_outline(
                draw, (width // 2, 40),
                "🍗 KENTUCKY FRIED CHICKEN 🍗",
                font_large, (255, 255, 255), (0, 0, 0), 1
            )

            draw.text((width // 2, 80), "INT FOOD SERVICES CORP SA",
                     fill=(255, 255, 255), font=font_medium, anchor="mm")

            draw.text((width // 2, 110), "RUC: 1791415132001 - GRAN CONTRIBUYENTE",
                     fill=(255, 255, 255), font=font_small, anchor="mm")

            # INFORMACIÓN DE LA FACTURA
            y = header_height + 20

            # Recuadro de información
            info_height = 180
            draw.rectangle([20, y, width - 20, y + info_height],
                          fill=(248, 249, 250), outline=(222, 226, 230), width=2)

            # Título
            draw.text((width // 2, y + 15), "FACTURA ELECTRÓNICA RIDE",
                     fill=(40, 167, 69), font=self._get_font(20, bold=True), anchor="mm")

            # Línea divisoria
            draw.line([40, y + 45, width - 40, y + 45], fill=(108, 117, 125), width=1)

            # Datos en 2 columnas
            col1_x = 50
            col2_x = width // 2 + 20
            row_height = 25

            current_y = y + 60

            # Columna 1
            draw.text((col1_x, current_y), f"🏪 LOCAL:", fill=(73, 80, 87), font=font_normal)
            draw.text((col1_x + 100, current_y), store_code, fill=(33, 37, 41), font=font_normal)
            current_y += row_height

            draw.text((col1_x, current_y), f"📄 COMPROBANTE:", fill=(73, 80, 87), font=font_normal)
            draw.text((col1_x + 130, current_y), invoice_id, fill=(33, 37, 41), font=font_normal)
            current_y += row_height

            draw.text((col1_x, current_y), f"📅 FECHA:", fill=(73, 80, 87), font=font_normal)
            draw.text((col1_x + 100, current_y), fecha, fill=(33, 37, 41), font=font_normal)
            current_y += row_height

            # Columna 2
            current_y = y + 60
            draw.text((col2_x, current_y), f"👤 CLIENTE:", fill=(73, 80, 87), font=font_normal)
            draw.text((col2_x + 100, current_y), cliente[:20], fill=(33, 37, 41), font=font_normal)
            current_y += row_height

            draw.text((col2_x, current_y), f"🔢 RUC/CI:", fill=(73, 80, 87), font=font_normal)
            draw.text((col2_x + 100, current_y), ruc, fill=(33, 37, 41), font=font_normal)
            current_y += row_height

            draw.text((col2_x, current_y), f"💳 FORMA PAGO:", fill=(73, 80, 87), font=font_normal)
            draw.text((col2_x + 130, current_y), forma_pago, fill=(33, 37, 41), font=font_normal)

            y += info_height + 30

            # DETALLES DE PRODUCTOS
            if detalles:
                detalles_height = min(400, len(detalles) * 35 + 60)
                draw.rectangle([20, y, width - 20, y + detalles_height],
                              fill=(255, 255, 255), outline=(206, 212, 218), width=2)

                draw.text((width // 2, y + 15), "🛒 DETALLES DE PRODUCTOS",
                         fill=(40, 167, 69), font=self._get_font(18, bold=True), anchor="mm")

                # Encabezados de tabla
                table_y = y + 50
                draw.line([40, table_y, width - 40, table_y], fill=(108, 117, 125), width=1)

                # Encabezados
                draw.text((60, table_y + 10), "CANT.", fill=(73, 80, 87), font=font_small)
                draw.text((120, table_y + 10), "DESCRIPCIÓN", fill=(73, 80, 87), font=font_small)
                draw.text((width - 120, table_y + 10), "PRECIO", fill=(73, 80, 87), font=font_small)
                draw.text((width - 60, table_y + 10), "TOTAL", fill=(73, 80, 87), font=font_small)

                table_y += 30

                # Productos (máximo 10)
                for detalle in detalles[:10]:
                    cantidad = str(detalle.get('cantidad', '1'))
                    descripcion = str(detalle.get('descripcion', 'Producto'))[:25]
                    precio = f"${detalle.get('precio_unitario', '0.00')}"
                    total_item = f"${detalle.get('total', '0.00')}"

                    draw.text((60, table_y), cantidad, fill=(33, 37, 41), font=font_small)
                    draw.text((120, table_y), descripcion, fill=(33, 37, 41), font=font_small)
                    draw.text((width - 120, table_y), precio, fill=(33, 37, 41), font=font_small, anchor="rm")
                    draw.text((width - 60, table_y), total_item, fill=(33, 37, 41), font=font_small, anchor="rm")

                    table_y += 25

                if len(detalles) > 10:
                    draw.text((width // 2, table_y + 10),
                             f"... y {len(detalles) - 10} productos más",
                             fill=(108, 117, 125), font=font_xsmall, anchor="mm")

                y += detalles_height + 20

            # TOTALES
            totales_height = 120
            draw.rectangle([20, y, width - 20, y + totales_height],
                          fill=(248, 249, 250), outline=(40, 167, 69), width=2)

            draw.text((width // 2, y + 15), "💰 TOTALES",
                     fill=(40, 167, 69), font=self._get_font(18, bold=True), anchor="mm")

            total_y = y + 45

            # Subtotal
            draw.text((width - 200, total_y), "Subtotal:", fill=(73, 80, 87), font=font_normal)
            draw.text((width - 40, total_y), f"${subtotal}", fill=(33, 37, 41), font=font_normal, anchor="rm")
            total_y += 25

            # IVA
            draw.text((width - 200, total_y), "IVA 15%:", fill=(73, 80, 87), font=font_normal)
            draw.text((width - 40, total_y), f"${iva}", fill=(33, 37, 41), font=font_normal, anchor="rm")
            total_y += 25

            # Total
            draw.text((width - 200, total_y), "TOTAL:", fill=(33, 37, 41), font=self._get_font(16, bold=True))
            draw.text((width - 40, total_y), f"${total}",
                     fill=(40, 167, 69), font=self._get_font(18, bold=True), anchor="rm")

            y += totales_height + 30

            # INFORMACIÓN ADICIONAL
            info_box_y = height - 120
            draw.rectangle([20, info_box_y, width - 20, height - 20],
                          fill=(255, 243, 205), outline=(255, 238, 186), width=2)

            draw.text((width // 2, info_box_y + 15), "⚠️ INFORMACIÓN IMPORTANTE",
                     fill=(133, 100, 4), font=font_normal, anchor="mm")

            draw.text((width // 2, info_box_y + 40),
                     "Esta es una representación visual generada por el sistema.",
                     fill=(133, 100, 4), font=font_small, anchor="mm")

            draw.text((width // 2, info_box_y + 60),
                     "Para la factura electrónica oficial, consulte el SRI.",
                     fill=(133, 100, 4), font=font_small, anchor="mm")

            # Pie de página
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            draw.text((width // 2, height - 10),
                     f"Generado: {timestamp} | Sistema: {self.system}",
                     fill=(108, 117, 125), font=font_xsmall, anchor="mm")

            # Convertir a BytesIO
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', optimize=True, quality=90)
            img_byte_arr.seek(0)

            logger.info(f"Imagen de factura generada: {width}x{height}px")
            return img_byte_arr

        except Exception as e:
            logger.error(f"Error generando imagen de factura: {e}", exc_info=True)
            return None

    async def generate_comanda_image_from_data(self, comanda_data: Dict[str, Any]) -> Optional[io.BytesIO]:
        """Genera imagen de comanda a partir de datos estructurados"""
        try:
            logger.info("Generando imagen de comanda desde datos")

            # Extraer datos
            comanda_id = comanda_data.get('comanda_id', 'N/A')
            factura_id = comanda_data.get('factura_id', 'N/A')
            store_code = comanda_data.get('store_code', 'K000')
            cliente = comanda_data.get('cliente', 'CLIENTE')
            telefono = comanda_data.get('telefono', 'N/A')
            direccion = comanda_data.get('direccion', 'N/A')
            fecha = comanda_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
            orden = comanda_data.get('orden', 'N/A')
            total = comanda_data.get('total', '0.00')
            forma_pago = comanda_data.get('forma_pago', 'EFECTIVO')
            detalles = comanda_data.get('detalles', [])
            observaciones = comanda_data.get('observaciones', 'N/A')

            # Dimensiones
            width, height = 700, 1000
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)

            # Fuentes
            font_title = self._get_font(28, bold=True)
            font_header = self._get_font(20, bold=True)
            font_normal = self._get_font(16)
            font_small = self._get_font(14)
            font_xsmall = self._get_font(12)

            # ENCABEZADO - Verde KFC
            header_height = 120
            draw.rectangle([0, 0, width, header_height], fill=(40, 167, 69))  # Verde KFC

            # Logo/Título
            self._draw_text_with_outline(
                draw, (width // 2, 40),
                "🍗 COMANDA KFC 🍗",
                font_title, (255, 255, 255), (0, 0, 0), 1
            )

            draw.text((width // 2, 80), "SISTEMA DE ÓRDENES Y PEDIDOS",
                     fill=(255, 255, 255), font=self._get_font(18), anchor="mm")

            draw.text((width // 2, 105), "PARA LLEVAR / DELIVERY",
                     fill=(255, 255, 255), font=font_small, anchor="mm")

            # INFORMACIÓN PRINCIPAL
            y = header_height + 20

            # Recuadro principal
            main_height = 180
            draw.rectangle([20, y, width - 20, y + main_height],
                          fill=(233, 236, 239), outline=(206, 212, 218), width=2)

            # Título
            draw.text((width // 2, y + 15), "📋 INFORMACIÓN DE LA COMANDA",
                     fill=(33, 37, 41), font=font_header, anchor="mm")

            # Datos
            info_y = y + 50
            col_width = (width - 60) // 2

            # Columna izquierda
            draw.text((40, info_y), f"🔢 ID COMANDA:", fill=(73, 80, 87), font=font_normal)
            draw.text((180, info_y), comanda_id[:20], fill=(33, 37, 41), font=font_normal)
            info_y += 30

            draw.text((40, info_y), f"🧾 FACTURA:", fill=(73, 80, 87), font=font_normal)
            draw.text((180, info_y), factura_id, fill=(33, 37, 41), font=font_normal)
            info_y += 30

            draw.text((40, info_y), f"🏪 TIENDA:", fill=(73, 80, 87), font=font_normal)
            draw.text((180, info_y), store_code, fill=(33, 37, 41), font=font_normal)

            # Columna derecha
            info_y = y + 50
            draw.text((col_width + 40, info_y), f"📅 FECHA:", fill=(73, 80, 87), font=font_normal)
            draw.text((col_width + 180, info_y), fecha, fill=(33, 37, 41), font=font_normal)
            info_y += 30

            draw.text((col_width + 40, info_y), f"👤 CLIENTE:", fill=(73, 80, 87), font=font_normal)
            draw.text((col_width + 180, info_y), cliente[:15], fill=(33, 37, 41), font=font_normal)
            info_y += 30

            draw.text((col_width + 40, info_y), f"📞 TELÉFONO:", fill=(73, 80, 87), font=font_normal)
            draw.text((col_width + 180, info_y), telefono, fill=(33, 37, 41), font=font_normal)

            y += main_height + 20

            # DIRECCIÓN SI EXISTE
            if direccion and direccion != 'N/A':
                dir_height = 80
                draw.rectangle([20, y, width - 20, y + dir_height],
                              fill=(220, 248, 255), outline=(135, 206, 235), width=2)

                draw.text((width // 2, y + 15), "📍 DIRECCIÓN DE ENTREGA",
                         fill=(0, 123, 255), font=font_normal, anchor="mm")

                # Dirección dividida en líneas
                dir_lines = []
                current_line = ""
                for word in direccion.split():
                    test_line = current_line + " " + word if current_line else word
                    if len(test_line) < 40:
                        current_line = test_line
                    else:
                        dir_lines.append(current_line)
                        current_line = word
                if current_line:
                    dir_lines.append(current_line)

                dir_y = y + 40
                for line in dir_lines[:3]:  # Máximo 3 líneas
                    draw.text((width // 2, dir_y), line,
                             fill=(33, 37, 41), font=font_small, anchor="mm")
                    dir_y += 20

                y += dir_height + 20

            # DETALLES DEL PEDIDO
            if detalles:
                detalles_height = min(350, len(detalles) * 30 + 60)
                draw.rectangle([20, y, width - 20, y + detalles_height],
                              fill=(255, 255, 255), outline=(255, 193, 7), width=2)

                draw.text((width // 2, y + 15), "🛒 DETALLES DEL PEDIDO",
                         fill=(255, 193, 7), font=font_header, anchor="mm")

                # Encabezados
                det_y = y + 50
                draw.line([40, det_y, width - 40, det_y], fill=(108, 117, 125), width=1)

                draw.text((60, det_y + 10), "CANT.", fill=(73, 80, 87), font=font_small)
                draw.text((120, det_y + 10), "PRODUCTO", fill=(73, 80, 87), font=font_small)

                det_y += 30

                # Productos
                for detalle in detalles[:12]:  # Máximo 12 productos
                    cantidad = str(detalle.get('cantidad', '1'))
                    producto = str(detalle.get('producto', 'Producto'))[:25]

                    draw.text((60, det_y), cantidad, fill=(33, 37, 41), font=font_small)
                    draw.text((120, det_y), producto, fill=(33, 37, 41), font=font_small)

                    det_y += 25

                if len(detalles) > 12:
                    draw.text((width // 2, det_y + 10),
                             f"... y {len(detalles) - 12} productos más",
                             fill=(108, 117, 125), font=font_xsmall, anchor="mm")

                y += detalles_height + 20

            # TOTAL Y FORMA DE PAGO
            total_height = 100
            draw.rectangle([20, y, width - 20, y + total_height],
                          fill=(40, 167, 69), outline=(33, 136, 56), width=2)

            draw.text((width // 2, y + 20), "💰 TOTAL A PAGAR",
                     fill=(255, 255, 255), font=font_header, anchor="mm")

            draw.text((width // 2, y + 50), f"${total}",
                     fill=(255, 255, 255), font=self._get_font(28, bold=True), anchor="mm")

            draw.text((width // 2, y + 85), f"Forma de pago: {forma_pago}",
                     fill=(255, 255, 255), font=font_normal, anchor="mm")

            y += total_height + 30

            # OBSERVACIONES SI EXISTEN
            if observaciones and observaciones != 'N/A':
                obs_height = 60
                draw.rectangle([20, y, width - 20, y + obs_height],
                              fill=(255, 243, 205), outline=(255, 238, 186), width=2)

                draw.text((width // 2, y + 15), "📝 OBSERVACIONES",
                         fill=(133, 100, 4), font=font_normal, anchor="mm")

                obs_text = observaciones[:60] + "..." if len(observaciones) > 60 else observaciones
                draw.text((width // 2, y + 40), obs_text,
                         fill=(133, 100, 4), font=font_small, anchor="mm")

                y += obs_height + 20

            # PIE DE PÁGINA
            footer_y = height - 60
            draw.rectangle([0, footer_y, width, height], fill=(248, 249, 250))

            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            draw.text((width // 2, footer_y + 20), f"🕒 Generado: {timestamp}",
                     fill=(108, 117, 125), font=font_small, anchor="mm")

            draw.text((width // 2, footer_y + 40), "📱 Sistema de Gestión KFC - Generado automáticamente",
                     fill=(40, 167, 69), font=font_xsmall, anchor="mm")

            # Convertir a BytesIO
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', optimize=True, quality=90)
            img_byte_arr.seek(0)

            logger.info(f"Imagen de comanda generada: {width}x{height}px")
            return img_byte_arr

        except Exception as e:
            logger.error(f"Error generando imagen de comanda: {e}", exc_info=True)
            return None

    async def generate_simple_comanda_image(self, comanda_id: str, factura_id: str, store_code: str) -> Optional[io.BytesIO]:
        """Genera una imagen simple de comanda con datos mínimos"""
        try:
            # Datos mínimos para la comanda
            comanda_data = {
                'comanda_id': comanda_id,
                'factura_id': factura_id,
                'store_code': store_code,
                'cliente': 'CLIENTE',
                'telefono': 'N/A',
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'total': '0.00',
                'forma_pago': 'EFECTIVO',
                'detalles': []
            }

            return await self.generate_comanda_image_from_data(comanda_data)

        except Exception as e:
            logger.error(f"Error generando imagen simple de comanda: {e}")
            return None

    async def generate_simple_invoice_image(self, invoice_id: str, store_code: str) -> Optional[io.BytesIO]:
        """Genera una imagen simple de factura con datos mínimos"""
        try:
            # Datos mínimos para la factura
            invoice_data = {
                'invoice_id': invoice_id,
                'store_code': store_code,
                'cliente': 'CONSUMIDOR FINAL',
                'ruc': '9999999999999',
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'total': '0.00',
                'subtotal': '0.00',
                'iva': '0.00',
                'forma_pago': 'EFECTIVO',
                'cajero': 'SISTEMA',
                'orden': 'N/A',
                'detalles': []
            }

            return await self.generate_invoice_image_from_data(invoice_data)

        except Exception as e:
            logger.error(f"Error generando imagen simple de factura: {e}")
            return None