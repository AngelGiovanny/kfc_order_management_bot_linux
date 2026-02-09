"""
Test rápido de conectividad de red
"""

import socket
import sys


def test_port(host, port, timeout=3):
    """Test simple de puerto"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✅ {host}:{port} - ABIERTO")
            return True
        elif result == 10035:
            print(f"⚠️  {host}:{port} - WSAEWOULDBLOCK (socket no bloqueante)")
            return False
        else:
            print(f"❌ {host}:{port} - CERRADO (código: {result})")
            return False
    except socket.timeout:
        print(f"⏱️  {host}:{port} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {host}:{port} - ERROR: {e}")
        return False


def test_store(store_code):
    """Test completo de una tienda"""
    store_number = store_code[1:].lstrip('0')

    print(f"\n{'=' * 50}")
    print(f"🧪 TEST DE CONECTIVIDAD PARA {store_code}")
    print(f"{'=' * 50}")

    ips = {
        'Linux': f"10.101.{store_number}.20",
        'Windows': f"10.101.{store_number}.10"
    }

    ports = [1433, 22, 3389, 80, 443]

    for name, ip in ips.items():
        print(f"\n🎯 Probando {name} ({ip}):")
        for port in ports:
            test_port(ip, port)

    print(f"\n{'=' * 50}")
    print("📋 RESUMEN:")
    print(f"{'=' * 50}")

    # Probar también con ping
    import subprocess

    for name, ip in ips.items():
        print(f"\n📡 PING a {name} ({ip}):")
        try:
            result = subprocess.run(['ping', '-n', '2', '-w', '1000', ip],
                                    capture_output=True, text=True)
            if "TTL=" in result.stdout or "ttl=" in result.stdout:
                print(f"   ✅ Responde al ping")
            else:
                print(f"   ❌ No responde al ping")
        except:
            print(f"   ⚠️  No se pudo ejecutar ping")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        store_code = sys.argv[1].upper()
    else:
        store_code = "K096"

    test_store(store_code)