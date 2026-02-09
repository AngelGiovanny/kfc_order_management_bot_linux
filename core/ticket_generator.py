"""
Generador profesional de tickets tipo recibo - VERSIÓN OPTIMIZADA PARA KFC
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import io

from utils.logger import get_logger

logger = get_logger(__name__)


class TicketGenerator:
    """Generador de tickets tipo recibo estilo KFC"""

    def __init__(self):
        # Configuración del ticket
        self.width = 400  # Ancho estándar para tickets de 80mm
        self.max_height = 1500  # Altura máxima (se ajusta dinámicamente)

        # Colores estilo KFC
        self.colors = {
            'background': (255, 255, 255),  # Blanco
            'text': (0, 0, 0),  # Negro
            'header': (227, 0, 43),  # Rojo KFC
            'accent': (255, 193, 7),  # Amarillo KFC
            'divider': (200, 200, 200),  # Gris claro
            'total': (40, 167, 69),  # Verde para totales
            'warning': (220, 53, 69)  # Rojo para advertencias
        }

        # Cargar fuentes (intentar varias opciones)
        self.fonts = self._load_fonts()

        # Directorio para tickets generados
        self.output_dir = Path("generated_tickets")
        self.output_dir.mkdir(exist_ok=True)

        logger.info("✅ TicketGenerator inicializado")

    def _load_fonts(self) -> Dict[str, Optional[ImageFont.FreeTypeFont]]:
        """Carga fuentes para el ticket"""
        fonts = {
            'title': None,
            'header': None,
            'normal': None,
            'small': None,
            'mono': None
        }

        # Lista de fuentes a intentar
        font_paths = [
            # Fuentes monoespaciadas para tickets
            ("cour.ttf", "Courier New"),  # Windows
            ("courbd.ttf", "Courier New Bold"),
            ("DejaVuSansMono.ttf", "DejaVu Sans Mono"),  # Linux
            ("LiberationMono-Regular.ttf", "Liberation Mono"),
            ("arial.ttf", "Arial"),  # Fallback
            ("arialbd.ttf", "Arial Bold")
        ]

        base_sizes = {
            'title': 20,
            'header': 16,
            'normal': 14,
            'small': 12,
            'mono': 14
        }

        # Intentar cargar cada fuente
        for font_file, font_name in font_paths:
            try:
                font_path = f"C:/Windows/Fonts/{font_file}"
                if os.path.exists(font_path):
                    # Cargar todas las variantes
                    if 'title' not in fonts or fonts['title'] is None:
                        fonts['title'] = ImageFont.truetype(font_path, base_sizes['title'])
                    if 'header' not in fonts or fonts['header'] is None:
                        fonts['header'] = ImageFont.truetype(font_path, base_sizes['header'])
                    if 'normal' not in fonts or fonts['normal'] is None:
                        fonts['normal'] = ImageFont.truetype(font_path, base_sizes['normal'])
                    if 'small' not in fonts or fonts['small'] is None:
                        fonts['small'] = ImageFont.truetype(font_path, base_sizes['small'])
                    if 'mono' not in fonts or fonts['mono'] is None and 'Mono' in font_name:
                        fonts['mono'] = ImageFont.truetype(font_path, base_sizes['mono'])

                    logger.info(f"✅ Fuente cargada: {font_name}")
            except Exception as e:
                continue

        # Si no se cargaron fuentes, usar defaults
        for font_type in fonts:
            if fonts[font_type] is None:
                fonts[font_type] = ImageFont.load_default()
                logger.warning(f"⚠️ Usando fuente default para {font_type}")

        return fonts

    def generate_invoice_ticket(self, invoice_data: Dict) -> Optional[bytes]:
        """Genera ticket de factura estilo recibo KFC"""
        try:
            logger.info("🎫 Generando ticket de factura...")

            # Validar datos mínimos
            if not invoice_data or 'numero' not in invoice_data:
                logger.error("❌ Datos de factura incompletos")
                return None

            # Crear imagen base
            img, draw = self._create_base_image()

            # Posición vertical inicial
            y_pos = 20

            # ===== ENCABEZADO =====
            y_pos = self._draw_header(draw, y_pos, "FACTURA")

            # ===== INFORMACIÓN DE LA EMPRESA =====
            y_pos = self._draw_company_info(draw, y_pos)

            # ===== INFORMACIÓN DEL CLIENTE =====
            y_pos = self._draw_client_info(draw, y_pos, invoice_data)

            # ===== DETALLES DE PRODUCTOS =====
            y_pos = self._draw_items_table(draw, y_pos, invoice_data)

            # ===== TOTALES =====
            y_pos = self._draw_totals(draw, y_pos, invoice_data)

            # ===== PIE DE PÁGINA =====
            y_pos = self._draw_footer(draw, y_pos, invoice_data)

            # Recortar imagen al contenido real
            final_height = y_pos + 20
            img = img.crop((0, 0, self.width, min(final_height, self.max_height)))

            # Guardar para depuración
            if os.getenv("DEBUG_TICKETS", "False").lower() == "true":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"factura_{invoice_data.get('numero', 'unknown')}_{timestamp}.png"
                output_path = self.output_dir / filename
                img.save(output_path, 'PNG', optimize=True)
                logger.info(f"📁 Ticket guardado: {output_path}")

            # Convertir a bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True, quality=95)

            logger.info(f"✅ Ticket de factura generado: {len(img_bytes.getvalue()):,} bytes")
            return img_bytes.getvalue()

        except Exception as e:
            logger.error(f"❌ Error generando ticket de factura: {e}", exc_info=True)
            return None

    def generate_comanda_ticket(self, comanda_data: Dict) -> Optional[bytes]:
        """Genera ticket de comanda estilo KFC"""
        try:
            logger.info("🎫 Generando ticket de comanda...")

            # Validar datos mínimos
            if not comanda_data or 'comanda_id' not in comanda_data:
                logger.error("❌ Datos de comanda incompletos")
                return None

            # Crear imagen base
            img, draw = self._create_base_image()

            # Posición vertical inicial
            y_pos = 20

            # ===== ENCABEZADO =====
            y_pos = self._draw_header(draw, y_pos, "COMANDA", is_comanda=True)

            # ===== INFORMACIÓN DE LA EMPRESA =====
            y_pos = self._draw_company_info(draw, y_pos)

            # ===== INFORMACIÓN DE LA ORDEN =====
            y_pos = self._draw_order_info(draw, y_pos, comanda_data)

            # ===== DETALLES DE PRODUCTOS =====
            y_pos = self._draw_comanda_items(draw, y_pos, comanda_data)

            # ===== INFORMACIÓN ADICIONAL =====
            y_pos = self._draw_comanda_footer(draw, y_pos, comanda_data)

            # Recortar imagen al contenido real
            final_height = y_pos + 20
            img = img.crop((0, 0, self.width, min(final_height, self.max_height)))

            # Guardar para depuración
            if os.getenv("DEBUG_TICKETS", "False").lower() == "true":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"comanda_{comanda_data.get('comanda_id', 'unknown')}_{timestamp}.png"
                output_path = self.output_dir / filename
                img.save(output_path, 'PNG', optimize=True)
                logger.info(f"📁 Ticket guardado: {output_path}")

            # Convertir a bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True, quality=95)

            logger.info(f"✅ Ticket de comanda generado: {len(img_bytes.getvalue()):,} bytes")
            return img_bytes.getvalue()

        except Exception as e:
            logger.error(f"❌ Error generando ticket de comanda: {e}", exc_info=True)
            return None

    def _create_base_image(self):
        """Crea imagen base blanca"""
        img = Image.new('RGB', (self.width, self.max_height),
                        color=self.colors['background'])
        draw = ImageDraw.Draw(img)
        return img, draw

    def _draw_header(self, draw, y_pos: int, title: str, is_comanda: bool = False) -> int:
        """Dibuja el encabezado del ticket"""
        # Línea superior
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['header'], width=3)
        y_pos += 15

        # Título
        draw.text((self.width // 2, y_pos), title,
                  fill=self.colors['header'],
                  font=self.fonts['title'],
                  anchor="mm")
        y_pos += 25

        # Subtítulo
        subtitle = "🍗 KENTUCKY FRIED CHICKEN 🍗"
        draw.text((self.width // 2, y_pos), subtitle,
                  fill=self.colors['accent'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 20

        # Línea divisoria
        draw.line([20, y_pos, self.width - 20, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 15

        return y_pos

    def _draw_company_info(self, draw, y_pos: int) -> int:
        """Dibuja información de la empresa"""
        # Nombre de empresa
        empresa = "INT FOOD SERVICES CORP SA"
        draw.text((self.width // 2, y_pos), empresa,
                  fill=self.colors['text'],
                  font=self.fonts['normal'],
                  anchor="mm")
        y_pos += 20

        # RUC
        ruc = "RUC: 1791415132001"
        draw.text((self.width // 2, y_pos), ruc,
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 15

        # Línea divisoria
        draw.line([30, y_pos, self.width - 30, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 15

        return y_pos

    def _draw_client_info(self, draw, y_pos: int, invoice_data: Dict) -> int:
        """Dibuja información del cliente"""
        # Número de factura
        factura_num = f"FACTURA: {invoice_data.get('numero', 'N/A')}"
        draw.text((20, y_pos), factura_num,
                  fill=self.colors['text'],
                  font=self.fonts['header'])
        y_pos += 20

        # Fecha
        fecha = f"FECHA: {invoice_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M'))}"
        draw.text((20, y_pos), fecha,
                  fill=self.colors['text'],
                  font=self.fonts['normal'])
        y_pos += 18

        # Cliente
        cliente = f"CLIENTE: {invoice_data.get('cliente', 'Consumidor Final')}"
        # Ajustar texto largo
        if len(cliente) > 40:
            cliente = cliente[:37] + "..."
        draw.text((20, y_pos), cliente,
                  fill=self.colors['text'],
                  font=self.fonts['normal'])
        y_pos += 18

        # RUC/CI si existe
        if invoice_data.get('ruc') and invoice_data['ruc'] != '0000000000':
            ruc_text = f"RUC/CI: {invoice_data['ruc']}"
            draw.text((20, y_pos), ruc_text,
                      fill=self.colors['text'],
                      font=self.fonts['small'])
            y_pos += 16

        # Línea divisoria
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=2)
        y_pos += 15

        # Encabezado de tabla
        headers = ["CANT", "DESCRIPCIÓN", "TOTAL"]
        draw.text((25, y_pos), headers[0],
                  fill=self.colors['text'],
                  font=self.fonts['small'])
        draw.text((self.width // 2, y_pos), headers[1],
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="mm")
        draw.text((self.width - 50, y_pos), headers[2],
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="rm")
        y_pos += 20

        # Línea bajo encabezados
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 10

        return y_pos

    def _draw_items_table(self, draw, y_pos: int, invoice_data: Dict) -> int:
        """Dibuja tabla de items de la factura"""
        items = invoice_data.get('detalles', [])

        if not items:
            # Mensaje si no hay items
            draw.text((self.width // 2, y_pos), "NO HAY DETALLES DISPONIBLES",
                      fill=self.colors['warning'],
                      font=self.fonts['small'],
                      anchor="mm")
            y_pos += 30
        else:
            # Dibujar cada item
            for item in items[:15]:  # Máximo 15 items
                # Cantidad
                cant = str(item.get('cantidad', 1))
                draw.text((25, y_pos), cant,
                          fill=self.colors['text'],
                          font=self.fonts['small'])

                # Descripción (truncar si es muy largo)
                desc = item.get('producto', 'Producto')
                if len(desc) > 25:
                    desc = desc[:22] + "..."
                draw.text((80, y_pos), desc,
                          fill=self.colors['text'],
                          font=self.fonts['small'])

                # Total
                total = f"${item.get('subtotal', 0):.2f}"
                draw.text((self.width - 50, y_pos), total,
                          fill=self.colors['text'],
                          font=self.fonts['small'],
                          anchor="rm")

                y_pos += 18

            # Si hay más items, indicar
            if len(items) > 15:
                draw.text((self.width // 2, y_pos), f"... y {len(items) - 15} más",
                          fill=self.colors['text'],
                          font=self.fonts['small'],
                          anchor="mm")
                y_pos += 20

        # Línea divisoria después de items
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=2)
        y_pos += 15

        return y_pos

    def _draw_totals(self, draw, y_pos: int, invoice_data: Dict) -> int:
        """Dibuja totales de la factura"""
        # Subtotal
        subtotal = invoice_data.get('subtotal', 0)
        if not subtotal:
            # Calcular subtotal si no viene
            items = invoice_data.get('detalles', [])
            subtotal = sum(item.get('subtotal', 0) for item in items)

        draw.text((self.width - 100, y_pos), "SUBTOTAL:",
                  fill=self.colors['text'],
                  font=self.fonts['normal'],
                  anchor="rm")
        draw.text((self.width - 30, y_pos), f"${subtotal:.2f}",
                  fill=self.colors['text'],
                  font=self.fonts['normal'],
                  anchor="rm")
        y_pos += 20

        # IVA (asumir 12% si no viene)
        iva = invoice_data.get('iva', subtotal * 0.12)
        draw.text((self.width - 100, y_pos), "IVA 12%:",
                  fill=self.colors['text'],
                  font=self.fonts['normal'],
                  anchor="rm")
        draw.text((self.width - 30, y_pos), f"${iva:.2f}",
                  fill=self.colors['text'],
                  font=self.fonts['normal'],
                  anchor="rm")
        y_pos += 20

        # Total
        total = invoice_data.get('total', subtotal + iva)
        draw.text((self.width - 100, y_pos), "TOTAL:",
                  fill=self.colors['total'],
                  font=self.fonts['header'],
                  anchor="rm")
        draw.text((self.width - 30, y_pos), f"${total:.2f}",
                  fill=self.colors['total'],
                  font=self.fonts['header'],
                  anchor="rm")
        y_pos += 25

        # Forma de pago si existe
        forma_pago = invoice_data.get('forma_pago')
        if forma_pago:
            draw.text((self.width // 2, y_pos), f"FORMA DE PAGO: {forma_pago}",
                      fill=self.colors['text'],
                      font=self.fonts['small'],
                      anchor="mm")
            y_pos += 20

        return y_pos

    def _draw_footer(self, draw, y_pos: int, invoice_data: Dict) -> int:
        """Dibuja pie de página de la factura"""
        # Línea divisoria
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 15

        # Mensaje de agradecimiento
        draw.text((self.width // 2, y_pos), "¡GRACIAS POR SU COMPRA!",
                  fill=self.colors['header'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 20

        # Información de contacto
        contacto = "📞 Contacto: 1800-KFC-ECU"
        draw.text((self.width // 2, y_pos), contacto,
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 15

        # Fecha y hora de generación
        generado = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        draw.text((self.width // 2, y_pos), generado,
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 15

        return y_pos

    def _draw_order_info(self, draw, y_pos: int, comanda_data: Dict) -> int:
        """Dibuja información de la orden para comanda"""
        # Número de comanda
        comanda_id = f"ORDEN: {comanda_data.get('comanda_id', 'N/A')}"
        draw.text((self.width // 2, y_pos), comanda_id,
                  fill=self.colors['header'],
                  font=self.fonts['header'],
                  anchor="mm")
        y_pos += 25

        # Fecha
        fecha = f"FECHA: {comanda_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M'))}"
        draw.text((20, y_pos), fecha,
                  fill=self.colors['text'],
                  font=self.fonts['normal'])
        y_pos += 18

        # Cliente
        cliente = comanda_data.get('cliente', 'Cliente no especificado')
        if len(cliente) > 30:
            cliente = cliente[:27] + "..."
        draw.text((20, y_pos), f"CLIENTE: {cliente}",
                  fill=self.colors['text'],
                  font=self.fonts['normal'])
        y_pos += 18

        # Teléfono si existe
        telefono = comanda_data.get('telefono')
        if telefono:
            draw.text((20, y_pos), f"TEL: {telefono}",
                      fill=self.colors['text'],
                      font=self.fonts['normal'])
            y_pos += 18

        # Dirección si existe
        direccion = comanda_data.get('direccion')
        if direccion:
            # Dividir dirección si es muy larga
            if len(direccion) > 40:
                dir_parts = [direccion[i:i + 40] for i in range(0, len(direccion), 40)]
                for part in dir_parts[:2]:  # Máximo 2 líneas
                    draw.text((20, y_pos), f"DIR: {part}",
                              fill=self.colors['text'],
                              font=self.fonts['small'])
                    y_pos += 16
            else:
                draw.text((20, y_pos), f"DIR: {direccion}",
                          fill=self.colors['text'],
                          font=self.fonts['normal'])
                y_pos += 18

        # Estado
        estado = comanda_data.get('estado', 'Pendiente')
        draw.text((self.width - 30, y_pos), f"ESTADO: {estado.upper()}",
                  fill=self.colors['total'] if estado.lower() == 'completado' else self.colors['warning'],
                  font=self.fonts['small'],
                  anchor="rm")
        y_pos += 20

        # Línea divisoria
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=2)
        y_pos += 15

        # Encabezado de items
        draw.text((25, y_pos), "CANT",
                  fill=self.colors['text'],
                  font=self.fonts['small'])
        draw.text((self.width // 2, y_pos), "PRODUCTO",
                  fill=self.colors['text'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 20

        # Línea bajo encabezados
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 10

        return y_pos

    def _draw_comanda_items(self, draw, y_pos: int, comanda_data: Dict) -> int:
        """Dibuja items de la comanda"""
        items = comanda_data.get('items', [])

        if not items:
            # Mensaje si no hay items
            draw.text((self.width // 2, y_pos), "NO HAY PRODUCTOS",
                      fill=self.colors['warning'],
                      font=self.fonts['small'],
                      anchor="mm")
            y_pos += 30
        else:
            # Dibujar cada item
            for item in items[:20]:  # Máximo 20 items
                # Cantidad
                cant = str(item.get('cantidad', 1))
                draw.text((25, y_pos), cant,
                          fill=self.colors['text'],
                          font=self.fonts['small'])

                # Descripción del producto
                producto = item.get('producto', 'Producto')
                if len(producto) > 25:
                    producto = producto[:22] + "..."
                draw.text((70, y_pos), producto,
                          fill=self.colors['text'],
                          font=self.fonts['small'])

                # Observaciones si existen
                observacion = item.get('observacion', '')
                if observacion:
                    y_pos += 15
                    obs_text = f"  > {observacion}"
                    if len(obs_text) > 35:
                        obs_text = obs_text[:32] + "..."
                    draw.text((70, y_pos), obs_text,
                              fill=self.colors['text'],
                              font=self.fonts['small'])

                y_pos += 20

            # Si hay más items, indicar
            if len(items) > 20:
                draw.text((self.width // 2, y_pos), f"... y {len(items) - 20} más",
                          fill=self.colors['text'],
                          font=self.fonts['small'],
                          anchor="mm")
                y_pos += 20

        # Línea divisoria después de items
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=2)
        y_pos += 15

        return y_pos

    def _draw_comanda_footer(self, draw, y_pos: int, comanda_data: Dict) -> int:
        """Dibuja pie de página de la comanda"""
        # Forma de pago
        forma_pago = comanda_data.get('forma_pago')
        if forma_pago:
            draw.text((20, y_pos), f"PAGO: {forma_pago}",
                      fill=self.colors['text'],
                      font=self.fonts['normal'])
            y_pos += 18

        # Cajero
        cajero = comanda_data.get('cajero')
        if cajero:
            draw.text((20, y_pos), f"CAJERO: {cajero}",
                      fill=self.colors['text'],
                      font=self.fonts['normal'])
            y_pos += 18

        # Observaciones generales
        observaciones = comanda_data.get('observaciones', '')
        if observaciones:
            y_pos += 10
            draw.line([10, y_pos, self.width - 10, y_pos],
                      fill=self.colors['divider'], width=1)
            y_pos += 15

            draw.text((20, y_pos), "OBSERVACIONES:",
                      fill=self.colors['text'],
                      font=self.fonts['small'])
            y_pos += 15

            # Dividir observaciones si son largas
            if len(observaciones) > 50:
                obs_parts = [observaciones[i:i + 50] for i in range(0, len(observaciones), 50)]
                for part in obs_parts[:3]:  # Máximo 3 líneas
                    draw.text((20, y_pos), f"  {part}",
                              fill=self.colors['text'],
                              font=self.fonts['small'])
                    y_pos += 14
            else:
                draw.text((20, y_pos), f"  {observaciones}",
                          fill=self.colors['text'],
                          font=self.fonts['small'])
                y_pos += 14

        y_pos += 10
        draw.line([10, y_pos, self.width - 10, y_pos],
                  fill=self.colors['divider'], width=1)
        y_pos += 15

        # Mensaje final
        draw.text((self.width // 2, y_pos), "¡BON APPÉTIT!",
                  fill=self.colors['header'],
                  font=self.fonts['header'],
                  anchor="mm")
        y_pos += 25

        # Información de preparación
        draw.text((self.width // 2, y_pos), "PREPARAR CON ❤️",
                  fill=self.colors['accent'],
                  font=self.fonts['small'],
                  anchor="mm")
        y_pos += 20

        return y_pos


# Instancia global
ticket_generator = TicketGenerator()