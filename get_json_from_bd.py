# get_json_from_bd.py
"""
Obtiene el JSON real de la BD y muestra su estructura
"""

import json
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()


def get_json_from_database(store_code, cfac_id):
    """Obtiene el JSON de Canal_Movimiento"""

    print("=" * 70)
    print(f"🔍 OBTENIENDO JSON REAL DE {store_code} - {cfac_id}")
    print("=" * 70)

    # Configurar conexión
    server = f"10.110.3.20"  # Windows para J003
    database = f"MAXPOINT_{store_code}"
    username = os.getenv('DB_USERNAME', 'sis_tercernivel')
    password = os.getenv('DB_PASSWORD', 'T3rc3rn1*m4x')

    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server},1433;"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )

        print(f"📌 Conectando a {server}...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Obtener el JSON más reciente
        query = """
            SELECT TOP 1 
                Canal_MovimientoVarchar1,
                imp_impresora,
                imp_ip_estacion,
                imp_fecha
            FROM Canal_Movimiento 
            WHERE Canal_MovimientoVarchar3 = ?
            ORDER BY imp_fecha DESC
        """

        cursor.execute(query, (cfac_id,))
        row = cursor.fetchone()

        if not row:
            print(f"❌ No se encontró JSON para {cfac_id}")
            return None

        json_str, impresora, ip, fecha = row

        print(f"\n📄 JSON RAW:")
        print("─" * 70)
        print(json_str[:1000] + ("..." if len(json_str) > 1000 else ""))
        print("─" * 70)

        try:
            json_data = json.loads(json_str)

            print(f"\n📊 ESTRUCTURA DEL JSON:")
            print("─" * 70)

            # Mostrar estructura
            def show_structure(data, indent=0):
                if isinstance(data, dict):
                    for key, value in data.items():
                        print(f"{'  ' * indent}🔹 {key}: {type(value).__name__}")
                        if isinstance(value, (dict, list)):
                            show_structure(value, indent + 1)
                        elif isinstance(value, str) and len(value) > 50:
                            print(f"{'  ' * (indent + 1)}  → {value[:50]}...")
                        else:
                            print(f"{'  ' * (indent + 1)}  → {value}")
                elif isinstance(data, list):
                    if data:
                        print(f"{'  ' * indent}📋 Lista con {len(data)} elementos")
                        show_structure(data[0], indent + 1)
                    else:
                        print(f"{'  ' * indent}📋 Lista vacía")

            show_structure(json_data)

            print("─" * 70)
            print(f"\n📌 Metadatos:")
            print(f"  Impresora: {impresora}")
            print(f"  IP: {ip}")
            print(f"  Fecha: {fecha}")

            # Guardar en archivo para referencia
            with open(f'json_real_{cfac_id}.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ JSON guardado en: json_real_{cfac_id}.json")

            return json_data

        except json.JSONDecodeError as e:
            print(f"❌ Error parseando JSON: {e}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


def get_json_from_sp(store_code, cfac_id):
    """Ejecuta el SP para generar JSON en tiempo real"""

    print("\n" + "=" * 70)
    print(f"🔍 GENERANDO JSON DESDE SP para {store_code} - {cfac_id}")
    print("=" * 70)

    try:
        # Extraer número de tienda
        store_number = store_code[1:].lstrip('0')

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=10.110.3.20,1433;"
            f"DATABASE=MAXPOINT_{store_code};"
            f"UID=sis_tercernivel;"
            f"PWD=T3rc3rn1*m4x;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Ejecutar SP
        sql = f"""
            DECLARE @jsonResult NVARCHAR(MAX);

            EXEC [facturacion].[IAE_TipoFacturacion] 
                @cfac = N'{cfac_id}',
                @pJsonOutput = @jsonResult OUTPUT;

            SELECT @jsonResult AS JsonData;
        """

        print(f"📌 Ejecutando SP para {cfac_id}...")
        cursor.execute(sql)
        row = cursor.fetchone()

        if row and row[0]:
            json_str = row[0]

            # Limpiar si viene con comillas
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1].replace('\\"', '"')

            try:
                json_data = json.loads(json_str)
                print(f"\n✅ JSON generado desde SP:")
                print(json.dumps(json_data, indent=2)[:500] + "...")

                # Guardar
                with open(f'json_sp_{cfac_id}.json', 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                print(f"\n✅ JSON guardado en: json_sp_{cfac_id}.json")

                return json_data

            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON del SP: {e}")
                print(f"   JSON raw: {json_str[:200]}...")
                return None
        else:
            print("❌ El SP no generó JSON")
            return None

    except Exception as e:
        print(f"❌ Error ejecutando SP: {e}")
        return None


if __name__ == "__main__":
    import sys

    store_code = "J003"
    cfac_id = "J003F000571791"

    if len(sys.argv) > 1:
        cfac_id = sys.argv[1]
    if len(sys.argv) > 2:
        store_code = sys.argv[2]

    # 1. Obtener JSON de la BD
    json_from_bd = get_json_from_database(store_code, cfac_id)

    # 2. Generar JSON desde SP
    json_from_sp = get_json_from_sp(store_code, cfac_id)

    print("\n" + "=" * 70)
    print("📊 COMPARACIÓN DE FORMATOS")
    print("=" * 70)

    if json_from_bd and json_from_sp:
        # Comparar estructura
        print("\n📌 Estructura desde BD:")
        print(f"  Keys: {list(json_from_bd.keys())}")
        if 'data' in json_from_bd:
            print(
                f"  Data keys: {list(json_from_bd['data'].keys()) if isinstance(json_from_bd['data'], dict) else 'No es dict'}")

        print("\n📌 Estructura desde SP:")
        print(f"  Keys: {list(json_from_sp.keys())}")
        if 'data' in json_from_sp:
            print(
                f"  Data keys: {list(json_from_sp['data'].keys()) if isinstance(json_from_sp['data'], dict) else 'No es dict'}")