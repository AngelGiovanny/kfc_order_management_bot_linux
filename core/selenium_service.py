"""
Servicio de Selenium para capturar imágenes de documentos - URLS CORREGIDAS
"""

import asyncio
import logging
import os
import platform
import re
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SeleniumService:
    """Servicio para capturar imágenes con Selenium - URLS CORREGIDAS"""

    def __init__(self):
        self.driver = None
        self._init_driver()

    def _init_driver(self):
        """Inicializa el driver de Selenium"""
        try:
            chrome_options = Options()

            # Configuración básica
            chrome_options.add_argument("--headless")  # Ejecutar en background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")  # Tamaño más pequeño
            chrome_options.add_argument("--disable-gpu")

            # Para Linux específicamente
            if platform.system() == "Linux":
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--remote-debugging-port=9222")
                # Intentar usar software rendering si hay problemas de GPU
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")

            # Configuraciones adicionales para mejorar estabilidad
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            try:
                # Intentar usar webdriver_manager para manejar el driver automáticamente
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # Fallback a driver manual
                self.driver = webdriver.Chrome(options=chrome_options)

            # Configurar timeouts más cortos
            self.driver.set_page_load_timeout(15)
            self.driver.implicitly_wait(5)

            logger.info("Driver de Selenium inicializado exitosamente")

        except Exception as e:
            logger.error(f"Error inicializando Selenium: {e}")
            self.driver = None

    def _get_store_number(self, store_code: str) -> str:
        """
        Obtiene el número de tienda del código sin ceros a la izquierda.

        Maneja múltiples formatos:
        - K016 -> 16
        - S016 -> 16
        - 016 -> 16
        - 16 -> 16
        - K -> 0 (default)
        """
        if not store_code:
            return "0"

        # Limpiar espacios y convertir a mayúsculas
        store_code = store_code.strip().upper()

        # Si ya es un número puro, procesarlo
        if store_code.isdigit():
            result = store_code.lstrip('0')
            return result if result else "0"

        # Si tiene formato con letra al inicio (K, S, etc.)
        # Extraer todos los dígitos
        numbers = re.findall(r'\d+', store_code)

        if numbers:
            # Tomar el primer grupo de números encontrados
            number_str = numbers[0]
            result = number_str.lstrip('0')
            return result if result else "0"

        # Si no se encontraron números, devolver 0
        return "0"

    async def capture_invoice_image(self, store_code: str, invoice_id: str, is_credit_note: bool = False) -> Optional[bytes]:
        """Captura imagen de factura desde URL - URL CORREGIDA"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            store_number = self._get_store_number(store_code)

            # Construir URL CORRECTA según tus indicaciones
            tipo = "N" if is_credit_note else "F"
            url = f"http://10.101.{store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={invoice_id}&tipo_comprobante={tipo}"

            logger.info(f"Accediendo a URL de {'nota crédito' if is_credit_note else 'factura'}: {url}")

            try:
                self.driver.get(url)

                # Esperar a que la página cargue
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # Esperar un poco más para que los elementos se rendericen
                await asyncio.sleep(1)

                # Tomar screenshot
                screenshot = self.driver.get_screenshot_as_png()

                logger.info(f"Captura de {'nota crédito' if is_credit_note else 'factura'} exitosa: {invoice_id}")
                return screenshot

            except Exception as page_error:
                logger.warning(f"Error cargando página: {page_error}")
                return None

        except Exception as e:
            logger.error(f"Error capturando imagen de {'nota crédito' if is_credit_note else 'factura'} con Selenium: {e}")
            return None

    async def capture_comanda_image_by_invoice(self, store_code: str, invoice_id: str) -> Optional[bytes]:
        """Captura imagen de comanda desde URL usando invoice_id"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            # Primero necesitamos obtener el ID de la orden desde la base de datos
            store_number = self._get_store_number(store_code)

            # Obtener ID de la orden
            from config.database import db_manager
            import pyodbc

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"No hay conexión a la BD para {store_code}")
                return None

            cursor = connection.cursor()

            try:
                # Obtener ID de la orden
                cursor.execute("SELECT TOP 1 IDCabeceraOrdenPedido FROM Cabecera_Factura WHERE cfac_id = ?", (invoice_id,))
                row = cursor.fetchone()

                if not row or not row[0]:
                    logger.warning(f"No se encontró orden para factura {invoice_id}")
                    cursor.close()
                    connection.close()
                    return None

                orden_id = row[0]

                # Construir URL CORRECTA según tus indicaciones
                url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={orden_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

                logger.info(f"Accediendo a URL de comanda: {url}")

                self.driver.get(url)

                # Esperar a que la página cargue
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # Esperar un poco más para que los elementos se rendericen
                await asyncio.sleep(1)

                # Tomar screenshot
                screenshot = self.driver.get_screenshot_as_png()

                logger.info(f"Captura de comanda exitosa: {orden_id}")

                cursor.close()
                connection.close()
                return screenshot

            except Exception as db_error:
                logger.error(f"Error obteniendo orden: {db_error}")
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
                return None

        except Exception as e:
            logger.error(f"Error capturando imagen de comanda con Selenium: {e}")
            return None

    async def capture_comanda_image(self, store_code: str, id_orden: str) -> Optional[bytes]:
        """Captura imagen de comanda usando directamente el ID de orden"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            store_number = self._get_store_number(store_code)

            # Construir URL CORRECTA según tus indicaciones
            url = f"http://10.101.{store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={id_orden}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

            logger.info(f"Accediendo a URL de comanda: {url}")

            self.driver.get(url)

            # Esperar a que la página cargue
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Esperar un poco más para que los elementos se rendericen
            await asyncio.sleep(1)

            # Tomar screenshot
            screenshot = self.driver.get_screenshot_as_png()

            logger.info(f"Captura de comanda exitosa: {id_orden}")
            return screenshot

        except Exception as e:
            logger.error(f"Error capturando imagen de comanda con Selenium: {e}")
            return None

    async def capture_url_image(self, url: str) -> Optional[bytes]:
        """Captura una imagen de cualquier URL"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            logger.info(f"Accediendo a URL: {url}")

            self.driver.get(url)

            # Esperar a que la página cargue
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Esperar un poco más para que los elementos se rendericen
            await asyncio.sleep(1)

            # Tomar screenshot
            screenshot = self.driver.get_screenshot_as_png()

            logger.info(f"Captura de URL exitosa")
            return screenshot

        except Exception as e:
            logger.error(f"Error capturando URL con Selenium: {e}")
            return None

    async def capture_url_image_with_debug(self, url: str) -> Optional[bytes]:
        """Captura URL con información de debug"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            logger.info(f"🔍 DEBUG: Accediendo a URL: {url}")

            self.driver.get(url)

            # Esperar a que cargue
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Esperar adicional
            await asyncio.sleep(2)

            # OBTENER INFORMACIÓN DE DEBUG
            # 1. Título de la página
            page_title = self.driver.title
            logger.info(f"🔍 DEBUG: Título de página: {page_title}")

            # 2. URL actual (por si hay redirección)
            current_url = self.driver.current_url
            logger.info(f"🔍 DEBUG: URL actual: {current_url}")

            # 3. Tamaño del contenido
            page_source = self.driver.page_source
            logger.info(f"🔍 DEBUG: Tamaño del HTML: {len(page_source)} caracteres")

            # 4. Verificar si hay texto visible
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            logger.info(f"🔍 DEBUG: Primeros 200 chars del body: {body_text[:200]}")

            # 5. Verificar elementos específicos
            try:
                # Buscar texto común en páginas de error
                if "404" in page_title or "404" in body_text or "Not Found" in body_text or "NOT FOUND" in body_text:
                    logger.error("🔍 DEBUG: Página muestra error 404/Not Found")

                # Buscar si es página de login o error
                if "login" in body_text.lower() or "acceso" in body_text.lower():
                    logger.error("🔍 DEBUG: Página parece ser de login/autenticación")

            except Exception as e:
                logger.warning(f"🔍 DEBUG: Error analizando contenido: {e}")

            # Capturar screenshot
            screenshot = self.driver.get_screenshot_as_png()

            # Guardar screenshot temporal para inspección
            debug_dir = "debug_screenshots"
            os.makedirs(debug_dir, exist_ok=True)

            timestamp = int(time.time())
            filename = f"{debug_dir}/debug_{timestamp}.png"

            with open(filename, "wb") as f:
                f.write(screenshot)

            logger.info(f"🔍 DEBUG: Screenshot guardado en: {filename}")

            return screenshot

        except Exception as e:
            logger.error(f"🔍 DEBUG: Error capturando URL: {e}")
            return None

    def close(self):
        """Cierra el driver de Selenium"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver de Selenium cerrado")
            except Exception as e:
                logger.error(f"Error cerrando driver: {e}")

    # AÑADIR ESTOS MÉTODOS AL FINAL DE TU CLASE SeleniumService (antes del close)

    async def get_html_content(self, url: str) -> Optional[str]:
        """
        PASO 2: Obtiene contenido HTML de URL
        Mantiene compatibilidad con tus métodos existentes
        """
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            logger.info(f"Obteniendo HTML de: {url}")

            # Usar el mismo método que ya tienes
            self.driver.get(url)

            # Esperar como en tus métodos actuales
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Tiempo de espera igual
            await asyncio.sleep(1)

            # Obtener HTML
            html_content = self.driver.page_source

            # Opcional: limpiar HTML manteniendo funcionalidad
            cleaned_html = self._clean_html_for_generation(html_content)

            logger.info(f"HTML obtenido exitosamente ({len(cleaned_html)} caracteres)")
            return cleaned_html

        except Exception as e:
            logger.error(f"Error obteniendo HTML: {e}")
            return None

    def _clean_html_for_generation(self, html: str) -> str:
        """
        Limpia HTML para generación, manteniendo compatibilidad
        """
        try:
            # Si BeautifulSoup está disponible, limpiar
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, 'html.parser')

                # Mantener estructura básica pero eliminar scripts problemáticos
                for script in soup.find_all('script'):
                    if "window.print" in str(script) or "print()" in str(script):
                        script.decompose()

                # Mantener estilos importantes
                for style in soup.find_all('style'):
                    if '@media print' in str(style):
                        # Mantener estilos de impresión
                        continue

                return str(soup)

            except ImportError:
                # Si no hay BeautifulSoup, devolver HTML original
                return html

        except Exception as e:
            logger.warning(f"Error limpiando HTML: {e}")
            return html

    async def generate_image_from_html(self, html_content: str, output_filename: str) -> bool:
        """
        PASO 3: Genera imagen desde HTML
        Usa el mismo driver que ya tienes configurado
        """
        import os
        import tempfile

        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return False

            # Crear archivo HTML temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                temp_html_path = f.name
                f.write(html_content)

            try:
                # Cargar archivo local
                file_url = f"file://{temp_html_path}"
                self.driver.get(file_url)

                # Esperar como en tus métodos actuales
                await asyncio.sleep(1.5)

                # Tomar screenshot - MISMO MÉTODO que ya usas
                self.driver.save_screenshot(output_filename)

                logger.info(f"Imagen generada: {output_filename}")
                return True

            finally:
                # Limpiar archivo temporal
                os.unlink(temp_html_path)

        except Exception as e:
            logger.error(f"Error generando imagen desde HTML: {e}")
            return False

    # Agrega estos métodos al final de tu clase SeleniumService:

    async def get_html_content(self, url: str) -> Optional[str]:
        """
        Obtiene el contenido HTML de una URL
        """
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return None

            logger.info(f"Obteniendo HTML de: {url}")

            self.driver.get(url)

            # Esperar a que cargue
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Esperar para renderizado
            await asyncio.sleep(2)

            # Obtener HTML
            html_content = self.driver.page_source

            # Limpiar HTML si es muy pequeño (puede ser error page)
            if len(html_content) < 500:
                logger.warning(f"HTML muy pequeño ({len(html_content)} caracteres), puede ser página de error")
                # Verificar si es página de error
                if "404" in html_content or "Not Found" in html_content or "Error" in html_content:
                    logger.error("Página de error detectada")
                    return None

            logger.info(f"HTML obtenido exitosamente ({len(html_content)} caracteres)")
            return html_content

        except Exception as e:
            logger.error(f"Error obteniendo HTML: {e}")
            return None

    async def html_to_image(self, html_content: str, output_path: str) -> bool:
        """
        Convierte HTML a imagen
        """
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible")
                return False

            import tempfile
            import os

            # Guardar HTML temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                temp_html = f.name
                f.write(html_content)

            try:
                # Cargar archivo local
                file_url = f"file://{temp_html}"
                self.driver.get(file_url)

                # Esperar a que cargue
                await asyncio.sleep(1)

                # Tomar screenshot
                self.driver.save_screenshot(output_path)

                logger.info(f"HTML convertido a imagen: {output_path}")
                return True

            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_html):
                    os.unlink(temp_html)

        except Exception as e:
            logger.error(f"Error convirtiendo HTML a imagen: {e}")
            return False

# Instancia global
selenium_service = SeleniumService()