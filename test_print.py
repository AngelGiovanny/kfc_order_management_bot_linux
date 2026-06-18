# test_print.py
"""
Prueba del servicio de impresión
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.print_service_3attempts import PrintService3Attempts


async def test_print():
    """Prueba el servicio de impresión"""

    # Configuración
    store_code = "J003"  # Cambia por la tienda que quieras probar
    document_id = "J003F000571791"  # Cambia por un ID real
    doc_type = "factura"  # factura, nota_credito, comanda

    print("=" * 60)
    print("🖨️ PRUEBA DE IMPRESIÓN")
    print("=" * 60)
    print(f"Tienda: {store_code}")
    print(f"Documento: {document_id}")
    print(f"Tipo: {doc_type}")
    print("=" * 60)
    print()

    # Crear servicio
    service = PrintService3Attempts(store_code)

    # Ejecutar impresión (bot=None para pruebas)
    result = await service.print_document(None, None, doc_type, document_id)

    print("\n" + "=" * 60)
    print("📊 RESULTADO")
    print("=" * 60)
    print(f"✅ Success: {result['success']}")
    print(f"📝 Message: {result['message']}")
    print(f"🏪 Estación: {result.get('estacion_impresion', 'N/A')}")
    print(f"🖨️ idImpresora: {result.get('id_impresora_used', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_print())