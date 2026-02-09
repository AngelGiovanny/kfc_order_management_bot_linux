"""
Handler para URLs de documentos - Compatible con SeleniumService existente
"""

import re
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class InvoiceHandler:
    """Handler para URLs de documentos que usa las mismas URLs que tu SeleniumService"""

    def __init__(self, store_code: str):
        self.store_code = store_code
        self.store_number = self._get_store_number(store_code)

    def _get_store_number(self, store_code: str) -> str:
        """
        Obtiene número de tienda - MÉTODO IDÉNTICO al de tu SeleniumService
        """
        if not store_code:
            return "0"

        store_code = store_code.strip().upper()

        if store_code.isdigit():
            result = store_code.lstrip('0')
            return result if result else "0"

        numbers = re.findall(r'\d+', store_code)
        if numbers:
            number_str = numbers[0]
            result = number_str.lstrip('0')
            return result if result else "0"

        return "0"

    def get_factura_url(self, cfac_id: str) -> str:
        """
        URL de factura - IDÉNTICA a la que ya usas en capture_invoice_image
        """
        return f"http://10.101.{self.store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=F"

    def get_nota_credito_url(self, cfac_id: str) -> str:
        """
        URL de nota de crédito - IDÉNTICA a la que ya usas
        """
        return f"http://10.101.{self.store_number}.20:880/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=N"

    def get_comanda_url_by_order_id(self, orden_id: str) -> str:
        """
        URL de comanda por ID de orden - Mismo que capture_comanda_image
        """
        return f"http://10.101.{self.store_number}.20:880/pos/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={orden_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1"