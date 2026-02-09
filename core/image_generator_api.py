"""
API de generación de imágenes integrada - Funciona en Windows/Linux sin servidor externo
"""

import io
import os
import json
import logging
import platform
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from threading import Thread
import queue

from flask import Flask, request, jsonify, send_file
import requests

logger = logging.getLogger(__name__)


class IntegratedImageGeneratorAPI:
    """API integrada para generación de imágenes - Sin servidor externo necesario"""

    def __init__(self, selenium_service):
        self.selenium_service = selenium_service
        self.app = None
        self.server_thread = None
        self.running = False
        self.base_url = "http://localhost:5010"
        logger.info(f"API integrada de imágenes inicializada para {platform.system()}")

    def start_server(self, port: int = 5010):
        """Inicia el servidor Flask en un hilo separado"""
        if self.running:
            logger.info("API ya está corriendo")
            return self.base_url

        self.app = Flask(__name__)
        self.base_url = f"http://localhost:{port}"

        # Configurar endpoints
        self._setup_endpoints()

        # Iniciar en hilo separado
        self.server_thread = Thread(
            target=self._run_server,
            args=(port,),
            daemon=True
        )
        self.server_thread.start()

        # Esperar a que el servidor inicie
        import time
        for _ in range(10):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    self.running = True
                    logger.info(f"API integrada iniciada en {self.base_url}")
                    return self.base_url
            except:
                time.sleep(0.5)

        logger.warning("API no pudo iniciarse completamente")
        return None

    def _run_server(self, port: int):
        """Ejecuta el servidor Flask"""
        try:
            self.app.run(
                host='127.0.0.1',
                port=port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Error en servidor API: {e}")

    def _setup_endpoints(self):
        """Configura los endpoints de la API"""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'system': platform.system(),
                'selenium_available': self.selenium_service.driver is not None,
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/generate/invoice', methods=['POST'])
        def generate_invoice():
            try:
                data = request.json

                if not data:
                    return jsonify({'error': 'No se proporcionaron datos'}), 400

                store_code = data.get('store_code')
                cfac_id = data.get('cfac_id')
                is_credit_note = data.get('is_credit_note', False)

                if not store_code or not cfac_id:
                    return jsonify({'error': 'Faltan parámetros'}), 400

                logger.info(f"API: Generando {'nota crédito' if is_credit_note else 'factura'} {cfac_id}")

                # Usar Selenium para capturar la imagen
                import asyncio

                # Crear un nuevo event loop para este hilo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Capturar imagen con Selenium
                    image_bytes = loop.run_until_complete(
                        self.selenium_service.capture_invoice_image(
                            store_code, cfac_id, is_credit_note
                        )
                    )

                    if image_bytes:
                        image_stream = io.BytesIO(image_bytes)
                        image_stream.seek(0)

                        filename = f"{'NC' if is_credit_note else 'FAC'}_{cfac_id}.png"
                        return send_file(
                            image_stream,
                            mimetype='image/png',
                            as_attachment=False,
                            download_name=filename
                        )
                    else:
                        # Generar imagen de fallback
                        from PIL import Image, ImageDraw, ImageFont

                        img = Image.new('RGB', (600, 300), color=(255, 255, 255))
                        draw = ImageDraw.Draw(img)

                        try:
                            font = ImageFont.truetype("arial.ttf", 20)
                        except:
                            font = ImageFont.load_default()

                        draw.text((50, 50), f"⚠️ Imagen no disponible", fill=(227, 0, 43), font=font)
                        draw.text((50, 100), f"Documento: {cfac_id}", fill=(0, 0, 0), font=font)
                        draw.text((50, 150), f"Tienda: {store_code}", fill=(0, 0, 0), font=font)
                        draw.text((50, 200), "Generado localmente", fill=(108, 117, 125), font=font)

                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)

                        return send_file(
                            img_byte_arr,
                            mimetype='image/png',
                            as_attachment=False
                        )

                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Error API generate_invoice: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/generate/comanda', methods=['POST'])
        def generate_comanda():
            try:
                data = request.json

                if not data:
                    return jsonify({'error': 'No se proporcionaron datos'}), 400

                store_code = data.get('store_code')
                cfac_id = data.get('cfac_id')

                if not store_code or not cfac_id:
                    return jsonify({'error': 'Faltan parámetros'}), 400

                logger.info(f"API: Generando comanda para factura {cfac_id}")

                # Usar Selenium para capturar la imagen
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Intentar primero con el método que usa invoice_id
                    image_bytes = loop.run_until_complete(
                        self.selenium_service.capture_comanda_image_by_invoice(
                            store_code, cfac_id
                        )
                    )

                    if not image_bytes:
                        # Si falla, intentar imagen simple
                        from config.database import db_manager
                        import pyodbc

                        # Obtener conexión a BD
                        connection = db_manager.get_connection(store_code)
                        if connection:
                            cursor = connection.cursor()
                            cursor.execute(
                                "SELECT TOP 1 IDCabeceraOrdenPedido FROM Cabecera_Factura WHERE cfac_id = ?",
                                (cfac_id,)
                            )
                            row = cursor.fetchone()
                            cursor.close()
                            connection.close()

                            if row and row[0]:
                                orden_id = row[0]
                                image_bytes = loop.run_until_complete(
                                    self.selenium_service.capture_comanda_image(store_code, orden_id)
                                )

                    if image_bytes:
                        image_stream = io.BytesIO(image_bytes)
                        image_stream.seek(0)

                        filename = f"COM_{cfac_id}.png"
                        return send_file(
                            image_stream,
                            mimetype='image/png',
                            as_attachment=False,
                            download_name=filename
                        )
                    else:
                        # Imagen de fallback
                        from PIL import Image, ImageDraw, ImageFont

                        img = Image.new('RGB', (600, 300), color=(255, 255, 255))
                        draw = ImageDraw.Draw(img)

                        try:
                            font = ImageFont.truetype("arial.ttf", 20)
                        except:
                            font = ImageFont.load_default()

                        draw.text((50, 50), f"🍗 Comanda no disponible", fill=(40, 167, 69), font=font)
                        draw.text((50, 100), f"Factura: {cfac_id}", fill=(0, 0, 0), font=font)
                        draw.text((50, 150), f"Tienda: {store_code}", fill=(0, 0, 0), font=font)
                        draw.text((50, 200), "Generado localmente", fill=(108, 117, 125), font=font)

                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)

                        return send_file(
                            img_byte_arr,
                            mimetype='image/png',
                            as_attachment=False
                        )

                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Error API generate_comanda: {e}")
                return jsonify({'error': str(e)}), 500

    def stop_server(self):
        """Detiene el servidor"""
        self.running = False
        logger.info("API integrada detenida")

    def get_base_url(self):
        """Obtiene la URL base de la API"""
        return self.base_url if self.running else None


# Instancia global
integrated_api = None


def get_integrated_api(selenium_service):
    """Obtiene o crea la instancia de la API integrada"""
    global integrated_api
    if integrated_api is None:
        integrated_api = IntegratedImageGeneratorAPI(selenium_service)
    return integrated_api