# test_api.py
import requests


def test_api():
    """Prueba la conectividad con la API de impresión"""

    # IP de la estación (la que usaste en la prueba)
    ip = "10.110.3.21"  # Cambia por la IP de tu estación
    url = f"http://{ip}:5000/api/ImpresionTickets/Impresion"

    print(f"🔍 Probando API en: {url}")

    # 1. Probar si el servidor responde (ping al puerto)
    try:
        # Intentar conectar al puerto 5000
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, 5000))
        sock.close()

        if result == 0:
            print(f"✅ Puerto 5000 abierto en {ip}")
        else:
            print(f"❌ Puerto 5000 CERRADO en {ip} (código: {result})")
            print("   ⚠️ La API de impresión NO está activa")
            return False
    except Exception as e:
        print(f"❌ Error probando puerto: {e}")
        return False

    # 2. Probar enviar un JSON de prueba
    test_json = {
        "numeroImpresiones": 1,
        "tipo": "factura",
        "idImpresora": "caja1",
        "idPlantilla": "default",
        "data": {
            "documento": "TEST_001",
            "tienda": "003",
            "observaciones": "PRUEBA DE IMPRESIÓN"
        }
    }

    try:
        print("\n📤 Enviando JSON de prueba...")
        response = requests.post(
            url,
            json=test_json,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )

        print(f"📥 Código de respuesta: {response.status_code}")
        print(f"📥 Respuesta: {response.text[:200]}")

        if response.status_code == 200:
            print("✅ API respondió exitosamente")
            return True
        else:
            print(f"❌ API respondió con error: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar a la API (ConnectionError)")
        print("   → La API NO está corriendo en esa IP")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout - La API no responde")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    test_api()