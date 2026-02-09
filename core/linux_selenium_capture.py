"""
Captura de imágenes de URLs para Linux usando Selenium
"""

import asyncio
import platform
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


class LinuxSeleniumCapture:
    """Captura de imágenes específica para Linux"""

    def __init__(self):
        self.driver = None
        if platform.system() == "Linux":
            self._init_linux_driver()

    def _init_linux_driver(self):
        """Inicializa el driver para Linux"""
        try:
            chrome_options = Options()

            # Configuración específica para Linux
            chrome_options.add_argument("--headless=new")  # Nuevo headless
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--disable-gpu")

            # Optimizaciones para Linux
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            # Usar software rendering si hay problemas
            chrome_options.add_argument("--use-gl=swiftshader")

            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.warning(f"Error con webdriver_manager: {e}")
                # Fallback a ruta directa
                self.driver = webdriver.Chrome(options=chrome_options)

            self.driver.set_page_load_timeout(15)
            self.driver.implicitly_wait(5)

            logger.info("Driver de Selenium para Linux inicializado")

        except Exception as e:
            logger.error(f"Error inicializando Selenium en Linux: {e}")
            self.driver = None

    async def capture_url_image(self, url: str) -> Optional[bytes]:
        """Captura una imagen de una URL"""
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible en Linux")
                return None

            logger.info(f"Linux: Accediendo a URL: {url}")

            self.driver.get(url)

            # Esperar a que cargue
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Esperar para renderizado
            await asyncio.sleep(1.5)

            # Capturar screenshot
            screenshot = self.driver.get_screenshot_as_png()

            logger.info("Linux: Captura de URL exitosa")
            return screenshot

        except Exception as e:
            logger.error(f"Linux: Error capturando URL: {e}")
            return None

    def close(self):
        """Cierra el driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Linux: Driver de Selenium cerrado")
            except Exception as e:
                logger.error(f"Linux: Error cerrando driver: {e}")

    # Agrega este método a tu clase LinuxSeleniumCapture:

    async def html_to_image(self, html_content: str, output_path: str) -> bool:
        """
        Convierte HTML a imagen en Linux
        """
        try:
            if not self.driver:
                logger.warning("Driver de Selenium no disponible en Linux")
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

                # Usar el mismo método de captura
                screenshot = await self.capture_url_image(file_url)

                if screenshot:
                    with open(output_path, 'wb') as f:
                        f.write(screenshot)

                    logger.info(f"Linux: HTML convertido a imagen: {output_path}")
                    return True
                return False

            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_html):
                    os.unlink(temp_html)

        except Exception as e:
            logger.error(f"Linux: Error convirtiendo HTML a imagen: {e}")
            return False

# Instancia global para Linux
linux_selenium = LinuxSeleniumCapture()