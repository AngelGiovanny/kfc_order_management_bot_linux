"""
Servicio de consultas para obtener datos de facturas y comandas
Versión simplificada y funcional
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from config.database import db_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class QueryService:
    """Servicio para consultar datos de documentos - VERSIÓN FUNCIONAL"""

    @staticmethod
    def _extract_store_number(store_code: str) -> str:
        """Extrae el número de tienda sin ceros a la izquierda (K016 -> 16)"""
        if not store_code or len(store_code) < 2:
            return "0"

        # Asumir formato KXXX
        number_part = store_code[1:]  # Quitar la 'K'

        # Quitar ceros a la izquierda usando int()
        try:
            return str(int(number_part))
        except ValueError:
            # Si no es un número válido, quitar ceros con lstrip
            result = number_part.lstrip('0')
            return result if result else "0"

    @staticmethod
    async def get_invoice_data(store_code: str, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos de una factura específica"""
        try:
            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"No hay conexión a la BD para {store_code}")
                return None

            with connection.cursor() as cursor:
                query = """
                    SELECT TOP 1 
                        cfac_id,
                        nombre_cliente,
                        ruc_cliente,
                        dir_cliente,
                        tel_cliente,
                        fecha,
                        hora,
                        total,
                        subtotal,
                        valor_iva,
                        forma_pago,
                        cajero,
                        codigo_app
                    FROM Cabecera_Factura WITH(NOLOCK)
                    WHERE cfac_id = ?
                """

                cursor.execute(query, (invoice_id,))
                row = cursor.fetchone()

                if not row:
                    logger.warning(f"No se encontró factura {invoice_id} en {store_code}")
                    return None

                invoice_data = {
                    'invoice_id': row[0] or invoice_id,
                    'cliente': row[1] or 'CONSUMIDOR FINAL',
                    'ruc': row[2] or '9999999999999',
                    'direccion': row[3] or 'N/A',
                    'telefono': row[4] or 'N/A',
                    'fecha': f"{row[5].strftime('%d/%m/%Y') if row[5] else datetime.now().strftime('%d/%m/%Y')} {row[6] if row[6] else ''}",
                    'total': str(row[7] or '0.00'),
                    'subtotal': str(row[8] or '0.00'),
                    'iva': str(row[9] or '0.00'),
                    'forma_pago': row[10] or 'EFECTIVO',
                    'cajero': row[11] or 'SISTEMA',
                    'orden': row[12] or 'N/A',
                    'store_code': store_code,
                    'detalles': []
                }

                detalles_query = """
                    SELECT 
                        descripcion,
                        cantidad,
                        precio_unitario,
                        total_linea
                    FROM Cuerpo_detalle WITH(NOLOCK)
                    WHERE cfac_id = ?
                    ORDER BY linea
                """

                cursor.execute(detalles_query, (invoice_id,))
                detalles = cursor.fetchall()

                for detalle in detalles:
                    invoice_data['detalles'].append({
                        'descripcion': detalle[0] or 'Producto',
                        'cantidad': str(detalle[1] or '1'),
                        'precio_unitario': str(detalle[2] or '0.00'),
                        'total': str(detalle[3] or '0.00')
                    })

            connection.close()
            logger.info(f"Datos de factura obtenidos: {invoice_id} en {store_code}")
            return invoice_data

        except Exception as e:
            logger.error(f"Error obteniendo datos de factura: {e}", exc_info=True)
            return None

    @staticmethod
    def get_comanda_url_sync(store_code: str, cfac_id: str) -> Optional[str]:
        """Obtiene la URL de comanda - VERSIÓN SÍNCRONA COMO ANTES"""
        try:
            logger.info(f"Buscando URL de comanda para factura: {cfac_id} en {store_code}")

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"No hay conexión a la BD para {store_code}")
                return None

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT IDCabeceraordenPedido FROM Cabecera_Factura WHERE cfac_id = ?",
                    (cfac_id,)
                )
                row = cursor.fetchone()

                if row and row[0]:
                    id_orden = row[0]
                    logger.info(f"ID de orden encontrado: {id_orden}")

                    # Extraer número de tienda sin ceros a la izquierda
                    store_code_int = QueryService._extract_store_number(store_code)

                    if store_code_int and store_code_int != "0":
                        url = f"http://10.101.{store_code_int}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={id_orden}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"
                        logger.info(f"URL generada: {url}")
                        return url
                    else:
                        logger.error(f"Código de tienda inválido: {store_code}")
                        return None
                else:
                    logger.warning(f"Factura {cfac_id} no tiene orden asociada")
                    return None

        except Exception as e:
            logger.error(f"Error obteniendo URL de comanda: {e}")
            return None
        finally:
            try:
                if 'connection' in locals() and connection:
                    connection.close()
            except:
                pass

    @staticmethod
    async def get_comanda_data(store_code: str, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos de comanda - versión asíncrona"""
        try:
            # Primero obtener la URL
            url = await QueryService.get_comanda_url(store_code, invoice_id)

            if not url:
                return None

            # Obtener datos de la factura para completar información
            invoice_data = await QueryService.get_invoice_data(store_code, invoice_id) or {}

            # Extraer ID de orden de la URL
            import urllib.parse
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            id_orden = query_params.get('odp_id', [None])[0]

            comanda_data = {
                'comanda_id': id_orden or f"ORD-{invoice_id}",
                'id_orden': id_orden,
                'factura_id': invoice_id,
                'store_code': store_code,
                'cliente': invoice_data.get('cliente', 'CLIENTE'),
                'telefono': invoice_data.get('telefono', 'N/A'),
                'direccion': invoice_data.get('direccion', 'N/A'),
                'fecha': invoice_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M:%S')),
                'total': invoice_data.get('total', '0.00'),
                'observaciones': 'N/A',
                'estado': 'PROCESADA',
                'forma_pago': invoice_data.get('forma_pago', 'EFECTIVO'),
                'cajero': invoice_data.get('cajero', 'SISTEMA'),
                'orden': invoice_data.get('orden', 'N/A'),
                'detalles': invoice_data.get('detalles', []),
                'url': url  # Agregar la URL directamente
            }

            logger.info(f"Datos de comanda obtenidos para factura {invoice_id}")
            return comanda_data

        except Exception as e:
            logger.error(f"Error obteniendo datos de comanda: {e}")
            return None

    @staticmethod
    async def get_comanda_url(store_code: str, cfac_id: str) -> Optional[str]:
        """Obtiene la URL de comanda - versión asíncrona"""
        # Para mantener compatibilidad, ejecutamos la versión síncrona en un thread
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            url = await loop.run_in_executor(
                executor,
                QueryService.get_comanda_url_sync,
                store_code,
                cfac_id
            )
            return url

    @staticmethod
    async def generate_comanda_url(comanda_data: Dict[str, Any]) -> str:
        """Genera la URL para imprimir la comanda"""
        # Si ya tenemos la URL en los datos, la retornamos
        if comanda_data and 'url' in comanda_data:
            return comanda_data['url']

        # Si no, generamos una nueva
        store_code = comanda_data.get('store_code', '')
        id_orden = comanda_data.get('id_orden')

        if not id_orden:
            return ""

        store_code_int = QueryService._extract_store_number(store_code)
        if not store_code_int or store_code_int == "0":
            return ""

        return f"http://10.101.{store_code_int}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={id_orden}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"

    @staticmethod
    def get_invoice_url_sync(store_code: str, cfac_id: str, is_credit_note: bool = False) -> str:
        """Obtiene la URL de factura - VERSIÓN SÍNCRONA"""
        try:
            # Extraer número de tienda sin ceros a la izquierda
            store_code_int = QueryService._extract_store_number(store_code)

            if not store_code_int or store_code_int == "0":
                raise ValueError(f"Código de tienda inválido: {store_code}")

            tipo_comprobante = 'N' if is_credit_note else 'F'
            url = f"http://10.101.{store_code_int}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante={tipo_comprobante}&"

            logger.info(f"URL de factura generada: {url}")
            return url

        except Exception as e:
            logger.error(f"Error generando URL de factura: {e}")
            return ""

    @staticmethod
    async def get_invoice_url(store_code: str, cfac_id: str, is_credit_note: bool = False) -> str:
        """Obtiene la URL de factura - versión asíncrona"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            url = await loop.run_in_executor(
                executor,
                QueryService.get_invoice_url_sync,
                store_code,
                cfac_id,
                is_credit_note
            )
            return url

    @staticmethod
    async def get_simple_invoice_data(invoice_id: str, store_code: str) -> Dict[str, Any]:
        """Obtiene datos mínimos de factura cuando no hay conexión a BD"""
        return {
            'invoice_id': invoice_id,
            'cliente': 'CONSUMIDOR FINAL',
            'ruc': '9999999999999',
            'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'total': '0.00',
            'subtotal': '0.00',
            'iva': '0.00',
            'forma_pago': 'EFECTIVO',
            'cajero': 'SISTEMA',
            'orden': 'N/A',
            'store_code': store_code,
            'detalles': []
        }

    @staticmethod
    async def get_simple_comanda_data(invoice_id: str, store_code: str) -> Dict[str, Any]:
        """Obtiene datos mínimos de comanda cuando no hay conexión a BD"""
        return {
            'comanda_id': f"ORD-{invoice_id}",
            'cliente': 'CLIENTE',
            'telefono': 'N/A',
            'direccion': 'N/A',
            'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'total': '0.00',
            'observaciones': 'N/A',
            'estado': 'PROCESADA',
            'factura_id': invoice_id,
            'store_code': store_code,
            'forma_pago': 'EFECTIVO',
            'cajero': 'SISTEMA',
            'orden': 'N/A',
            'detalles': []
        }