"""
Generador de imágenes para facturas y comandas - Soporte Windows/Linux
"""

import os
import asyncio
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    SELENIUM_AVAILABLE = True
except:
    SELENIUM_AVAILABLE = False

try:
    import imgkit

    IMGKIT_AVAILABLE = True
except:
    IMGKIT_AVAILABLE = False

from PIL import Image
import jinja2

from config.settings import TEMPLATES_DIR, STATIC_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """Generador de imágenes multiplataforma"""

    def __init__(self, os_type: str = "windows"):
        self.os_type = os_type

        # Configurar Jinja2 para plantillas
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

        # Configurar según SO
        if os_type == "linux":
            self._setup_linux()
        else:
            self._setup_windows()

    def _setup_windows(self):
        """Configuración para Windows"""
        self.use_selenium = SELENIUM_AVAILABLE

        if self.use_selenium:
            self.chrome_options = Options()
            self.chrome_options.add_argument("--headless")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--no-sandbox")
            self.chrome_options.add_argument("--window-size=800,1200")
            self.chrome_options.add_argument("--disable-dev-shm-usage")

    def _setup_linux(self):
        """Configuración para Linux"""
        self.use_imgkit = IMGKIT_AVAILABLE

        if self.use_imgkit:
            # Configurar wkhtmltoimage
            self.config = imgkit.config(wkhtmltoimage='/usr/bin/wkhtmltoimage')
            self.options = {
                'format': 'png',
                'width': '800',
                'disable-smart-width': '',
                'quality': '100',
                'quiet': '',
                'enable-local-file-access': ''
            }

    def generate_invoice_image(self, invoice_data: Dict[str, Any]) -> Optional[BytesIO]:
        """Genera imagen de factura según SO"""
        try:
            if self.os_type == "windows" and self.use_selenium:
                return self._generate_with_selenium(invoice_data, "invoice")
            elif self.os_type == "linux" and self.use_imgkit:
                return self._generate_with_imgkit(invoice_data, "invoice")
            else:
                # Fallback a método común
                return self._generate_fallback(invoice_data, "invoice")
        except Exception as e:
            logger.error(f"Error generando imagen de factura: {e}")
            return None

    def generate_comanda_image(self, comanda_data: Dict[str, Any]) -> Optional[BytesIO]:
        """Genera imagen de comanda según SO"""
        try:
            if self.os_type == "windows" and self.use_selenium:
                return self._generate_with_selenium(comanda_data, "comanda")
            elif self.os_type == "linux" and self.use_imgkit:
                return self._generate_with_imgkit(comanda_data, "comanda")
            else:
                # Fallback a método común
                return self._generate_fallback(comanda_data, "comanda")
        except Exception as e:
            logger.error(f"Error generando imagen de comanda: {e}")
            return None

    def _generate_with_selenium(self, data: Dict[str, Any], template_type: str) -> Optional[BytesIO]:
        """Genera imagen usando Selenium (Windows)"""
        if not SELENIUM_AVAILABLE:
            return None

        try:
            # Renderizar HTML
            html_content = self._render_template(data, template_type)

            # Guardar temporalmente
            temp_file = TEMPLATES_DIR / f"temp_{datetime.now().timestamp()}.html"
            temp_file.write_text(html_content, encoding='utf-8')

            # Configurar ChromeDriver
            service = Service('chromedriver.exe')
            driver = webdriver.Chrome(service=service, options=self.chrome_options)

            try:
                # Cargar archivo local
                driver.get(f"file:///{temp_file.resolve()}")

                # Esperar a que cargue
                driver.implicitly_wait(2)

                # Tomar screenshot
                screenshot = driver.get_screenshot_as_png()

                # Convertir a BytesIO
                image_io = BytesIO(screenshot)
                image_io.seek(0)

                return image_io

            finally:
                driver.quit()

                # Eliminar archivo temporal
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            logger.error(f"Error con Selenium: {e}")
            return None

    def _generate_with_imgkit(self, data: Dict[str, Any], template_type: str) -> Optional[BytesIO]:
        """Genera imagen usando imgkit/wkhtmltoimage (Linux)"""
        if not IMGKIT_AVAILABLE:
            return None

        try:
            # Renderizar HTML
            html_content = self._render_template(data, template_type)

            # Guardar temporalmente
            temp_file = TEMPLATES_DIR / f"temp_{datetime.now().timestamp()}.html"
            temp_file.write_text(html_content, encoding='utf-8')

            # Generar imagen
            img_bytes = imgkit.from_file(
                str(temp_file),
                False,
                options=self.options,
                config=self.config
            )

            # Convertir a BytesIO
            image_io = BytesIO(img_bytes)
            image_io.seek(0)

            # Eliminar archivo temporal
            if temp_file.exists():
                temp_file.unlink()

            return image_io

        except Exception as e:
            logger.error(f"Error con imgkit: {e}")
            return None

    def _generate_fallback(self, data: Dict[str, Any], template_type: str) -> Optional[BytesIO]:
        """Método de fallback cuando no hay Selenium/imgkit"""
        try:
            # Renderizar HTML simple
            html_content = self._render_template(data, template_type)

            # Para fallback, podríamos generar un PDF o imagen simple
            # Por ahora, creamos una imagen simple con Pillow

            from PIL import Image, ImageDraw, ImageFont

            # Crear imagen básica
            img = Image.new('RGB', (800, 1200), color='white')
            draw = ImageDraw.Draw(img)

            # Usar fuente por defecto
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()

            # Escribir datos básicos
            y = 20
            draw.text((20, y), f"{template_type.upper()} - {data.get('store_code', 'N/A')}", fill='black', font=font)
            y += 30

            for key, value in data.items():
                if key not in ['details', 'items'] and isinstance(value, (str, int, float)):
                    draw.text((20, y), f"{key}: {value}", fill='black', font=font)
                    y += 20

            # Convertir a BytesIO
            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)

            return img_io

        except Exception as e:
            logger.error(f"Error en fallback: {e}")
            return None

    def _render_template(self, data: Dict[str, Any], template_type: str) -> str:
        """Renderiza plantilla HTML con datos"""
        template_file = f"{template_type}_template.html"

        try:
            template = self.template_env.get_template(template_file)

            # Agregar datos comunes
            data['generated_date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            data['current_year'] = datetime.now().year

            # Renderizar
            return template.render(**data)

        except Exception as e:
            logger.error(f"Error renderizando plantilla: {e}")

            # Plantilla de emergencia
            return self._create_emergency_template(data, template_type)

    def _create_emergency_template(self, data: Dict[str, Any], template_type: str) -> str:
        """Crea plantilla HTML de emergencia"""
        if template_type == "invoice":
            return self._create_invoice_emergency_template(data)
        else:
            return self._create_comanda_emergency_template(data)

    def _create_invoice_emergency_template(self, data: Dict[str, Any]) -> str:
        """Plantilla de emergencia para facturas"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; border-bottom: 2px solid #e63946; padding-bottom: 10px; }}
                .logo {{ color: #e63946; font-size: 24px; font-weight: bold; }}
                .info {{ margin: 20px 0; }}
                .row {{ display: flex; justify-content: space-between; margin: 5px 0; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th {{ background: #e63946; color: white; padding: 10px; }}
                .table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .total {{ text-align: right; font-size: 18px; font-weight: bold; margin-top: 20px; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">KFC</div>
                <h2>FACTURA ELECTRÓNICA</h2>
                <div>Tienda: {data.get('store_code', 'N/A')}</div>
            </div>

            <div class="info">
                <div class="row">
                    <span>Número:</span>
                    <span>{data.get('invoice_number', 'N/A')}</span>
                </div>
                <div class="row">
                    <span>Fecha:</span>
                    <span>{data.get('date', 'N/A')}</span>
                </div>
                <div class="row">
                    <span>Cliente:</span>
                    <span>{data.get('client_name', 'CONSUMIDOR FINAL')}</span>
                </div>
                <div class="row">
                    <span>RUC/CI:</span>
                    <span>{data.get('client_ruc', '9999999999999')}</span>
                </div>
            </div>

            <table class="table">
                <thead>
                    <tr>
                        <th>Cant.</th>
                        <th>Descripción</th>
                        <th>P.Unit.</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Agregar detalles
        for detail in data.get('details', []):
            html += f"""
                    <tr>
                        <td>{detail.get('quantity', 1)}</td>
                        <td>{detail.get('product_name', 'Producto')}</td>
                        <td>${detail.get('unit_price', 0):.2f}</td>
                        <td>${detail.get('subtotal', 0):.2f}</td>
                    </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="total">
                <div>Subtotal: ${data.get('subtotal', 0):.2f}</div>
                <div>IVA 15%: ${data.get('iva', 0):.2f}</div>
                <div style="color: #e63946; font-size: 24px;">TOTAL: ${data.get('total', 0):.2f}</div>
            </div>

            <div class="footer">
                <p>Generado: {data.get('generated_date', 'N/A')}</p>
                <p>Sistema KFC - Facturación Electrónica</p>
            </div>
        </body>
        </html>
        """

        return html

    def _create_comanda_emergency_template(self, data: Dict[str, Any]) -> str:
        """Plantilla de emergencia para comandas"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Courier New', monospace; margin: 10px; }}
                .header {{ text-align: center; border-bottom: 1px dashed #000; padding-bottom: 5px; margin-bottom: 10px; }}
                .title {{ font-size: 18px; font-weight: bold; }}
                .info {{ margin: 5px 0; }}
                .items {{ margin: 10px 0; }}
                .item {{ margin: 3px 0; }}
                .urgent {{ color: red; font-weight: bold; }}
                .footer {{ margin-top: 15px; text-align: center; font-size: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">KFC - COMANDA DE COCINA</div>
                <div>Tienda: {data.get('store_code', 'N/A')}</div>
            </div>

            <div class="info">
                <div>Transacción: {data.get('transaction', 'N/A')}</div>
                <div>Cuenta: {data.get('account', '1')}</div>
                <div>Orden: {data.get('order_description', 'N/A')}</div>
                <div>Cajero/a: {data.get('cashier', 'N/A')}</div>
                <div>Fecha: {data.get('date', 'N/A')}</div>
            </div>

            <div class="items">
                <div style="font-weight: bold; border-bottom: 1px solid #000; padding-bottom: 3px;">ITEMS:</div>
        """

        # Agregar items
        for item in data.get('items', []):
            html += f'<div class="item">{item}</div>'

        html += f"""
            </div>

            <div class="info">
                <div>Tiempo preparación: {data.get('prep_time', '15-20 min')}</div>
                <div class="{'' if data.get('priority') == 'NORMAL' else 'urgent'}">
                    Prioridad: {data.get('priority', 'NORMAL')}
                </div>
            </div>

            <div class="footer">
                <div>---</div>
                <div>Generado: {data.get('generated_date', 'N/A')}</div>
                <div>Sistema KFC - Comandas</div>
            </div>
        </body>
        </html>
        """

        return html


# Instancia global para fácil acceso
image_generator = ImageGenerator()