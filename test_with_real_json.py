# test_with_real_json.py
"""
Prueba de impresión usando el JSON real del SP
"""

import asyncio
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.print_service_3attempts import PrintService3Attempts
from config.database import db_manager
from core.os_detector import OSDetector


async def get_real_json(store_code, cfac_id):
    """Obtiene el JSON real ejecutando el SP"""

    print(f"🔍 Obteniendo JSON real para {cfac_id}...")

    try:
        # Detectar SO
        os_type, _ = OSDetector.detect_os(store_code, quick=True)
        print(f"   OS detectado: {os_type}")

        # Conectar
        connection = db_manager.get_connection(store_code, os_type)
        if not connection:
            print("   ❌ No se pudo conectar")
            return None

        cursor = connection.cursor()

        # Ejecutar SP
        sql = f"""
            SET NOCOUNT ON;
            DECLARE @jsonResult NVARCHAR(MAX);

            EXEC [facturacion].[IAE_TipoFacturacion] 
                @cfac = N'{cfac_id}',
                @pJsonOutput = @jsonResult OUTPUT;

            SELECT @jsonResult AS JsonData;
        """

        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()
        connection.close()

        if row and row[0]:
            json_str = row[0]
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1].replace('\\"', '"')

            json_data = json.loads(json_str)
            print(f"   ✅ JSON obtenido del SP")
            print(f"   Keys: {list(json_data.keys())}")
            if 'data' in json_data and isinstance(json_data['data'], dict):
                print(f"   Data keys: {list(json_data['data'].keys())}")
            return json_data

        print("   ❌ No se obtuvo JSON")
        return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


async def test_print_with_real_json():
    """Prueba impresión usando JSON real"""

    store_code = "J003"
    cfac_id = "J003F000571791"

    print("=" * 60)
    print("🖨️ PRUEBA CON JSON REAL")
    print("=" * 60)

    # Obtener JSON real
    json_data = await get_real_json(store_code, cfac_id)

    if json_data:
        print(f"\n📄 JSON real obtenido:")
        print(json.dumps(json_data, indent=2)[:500] + "...")

        # Crear servicio y probar
        service = PrintService3Attempts(store_code)

        # Usar el JSON real para imprimir directamente
        id_impresora = json_data.get("idImpresora", "caja1")
        ips_to_try = service._get_ips_by_chain_validation(id_impresora)

        print(f"\n📌 Probando en IPs: {ips_to_try}")

        for ip in ips_to_try:
            print(f"\n🔍 Probando {ip}...")
            success = await service._send_print_request(ip, json_data)
            if success:
                print(f"   ✅ ¡IMPRESIÓN EXITOSA en {ip}!")
                return True

        print("\n❌ No se pudo imprimir en ninguna IP")
        return False
    else:
        print("\n❌ No se pudo obtener el JSON real")
        return False


if __name__ == "__main__":
    asyncio.run(test_print_with_real_json())