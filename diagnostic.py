#!/usr/bin/env python3
"""
Script de diagnóstico del sistema KFC Bot
"""

import os
import sys
import pyodbc
from pathlib import Path

# Agregar directorio actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    WINDOWS_SERVER, WINDOWS_INSTANCE, LINUX_SERVER_PREFIX,
    DEFAULT_PORT, DATABASE_NAME, DB_USERNAME, DB_PASSWORD
)
from core.os_detector import OSDetector, ConnectionTester


def print_header(text):
    """Imprime un encabezado"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_odbc_driver():
    """Prueba el driver ODBC"""
    print_header("PRUEBA DE DRIVER ODBC")

    try:
        # Listar drivers disponibles
        drivers = pyodbc.drivers()
        print("✅ Drivers ODBC disponibles:")
        for driver in drivers:
            print(f"   • {driver}")

        # Verificar driver específico
        target_driver = "ODBC Driver 17 for SQL Server"
        if target_driver in drivers:
            print(f"\n✅ Driver {target_driver} encontrado")
            return True
        else:
            print(f"\n❌ Driver {target_driver} NO encontrado")
            print("   Instale: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_windows_connection(store_code="K169"):
    """Prueba conexión Windows"""
    print_header(f"PRUEBA CONEXIÓN WINDOWS - {store_code}")

    connection_strings = [
        # Método 1: Trusted Connection
        (
            "Método 1 (Trusted)",
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={WINDOWS_SERVER}\\{WINDOWS_INSTANCE};"
            f"DATABASE={DATABASE_NAME};"
            f"Trusted_Connection=yes;"
            f"Connection Timeout=10;"
        ),
        # Método 2: Sin instancia
        (
            "Método 2 (Sin instancia)",
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={WINDOWS_SERVER};"
            f"DATABASE={DATABASE_NAME};"
            f"Trusted_Connection=yes;"
            f"Connection Timeout=10;"
        ),
        # Método 3: SQL Authentication
        (
            "Método 3 (SQL Auth)",
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={WINDOWS_SERVER}\\{WINDOWS_INSTANCE};"
            f"DATABASE={DATABASE_NAME};"
            f"UID={DB_USERNAME};"
            f"PWD={DB_PASSWORD};"
            f"Connection Timeout=10;"
        ),
    ]

    success = False
    for name, conn_str in connection_strings:
        print(f"\n🔧 Probando {name}...")
        print(f"   Cadena: {conn_str[:80]}...")

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            print(f"   ✅ EXITOSO")
            print(f"   📋 Servidor: {version[:80]}...")
            success = True
            break

        except Exception as e:
            print(f"   ❌ FALLIDO: {str(e)[:100]}")

    return success


def test_linux_connection(store_code="K004"):
    """Prueba conexión Linux"""
    print_header(f"PRUEBA CONEXIÓN LINUX - {store_code}")

    store_number = store_code[1:]
    linux_ip = f"{LINUX_SERVER_PREFIX}.{store_number}.20"

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={linux_ip},{DEFAULT_PORT};"
        f"DATABASE={DATABASE_NAME};"
        f"UID={DB_USERNAME};"
        f"PWD={DB_PASSWORD};"
        f"Connection Timeout=10;"
    )

    print(f"🔧 Probando conexión a {linux_ip}...")
    print(f"   Cadena: {conn_str[:80]}...")

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        print(f"   ✅ EXITOSO")
        print(f"   📋 Servidor: {version[:80]}...")
        return True

    except Exception as e:
        print(f"   ❌ FALLIDO: {str(e)[:100]}")
        return False


def test_store_detection():
    """Prueba detección de tiendas"""
    print_header("PRUEBA DE DETECCIÓN DE TIENDAS")

    test_stores = ["K004", "K169", "K025", "K999"]

    for store in test_stores:
        print(f"\n🔍 Probando {store}...")

        try:
            os_type, address = OSDetector.detect_os(store)
            print(f"   ✅ Detectado: {os_type.upper()} - {address}")

            # Test de conexión
            tester = ConnectionTester()
            results = tester.test_all_connections(store)
            print(f"   📊 Linux ODBC: {'✅' if results['linux_odbc'] else '❌'}")
            print(f"   📊 Windows ODBC: {'✅' if results['windows_odbc'] else '❌'}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")


def check_configuration():
    """Verifica la configuración"""
    print_header("CONFIGURACIÓN ACTUAL")

    config_vars = [
        ("WINDOWS_SERVER", WINDOWS_SERVER),
        ("WINDOWS_INSTANCE", WINDOWS_INSTANCE),
        ("LINUX_SERVER_PREFIX", LINUX_SERVER_PREFIX),
        ("DEFAULT_PORT", DEFAULT_PORT),
        ("DATABASE_NAME", DATABASE_NAME),
        ("DB_USERNAME", DB_USERNAME),
        ("DB_PASSWORD", "***" if DB_PASSWORD else "No configurado"),
    ]

    for name, value in config_vars:
        print(f"   {name}: {value}")


def main():
    """Función principal de diagnóstico"""
    print("🔧 DIAGNÓSTICO DEL SISTEMA KFC BOT")
    print("=" * 60)

    # 1. Verificar configuración
    check_configuration()

    # 2. Verificar driver ODBC
    if not test_odbc_driver():
        print("\n⚠️  Instale el driver ODBC antes de continuar")
        return

    # 3. Pruebas de conexión
    print("\n" + "=" * 60)
    print("  RESUMEN DE CONEXIONES")
    print("=" * 60)

    # Probar K169 (tu tienda problemática)
    print("\n🔬 TIENDA K169 (Problemática):")
    win_success = test_windows_connection("K169")

    # Probar K004 (Linux de ejemplo)
    print("\n🔬 TIENDA K004 (Linux ejemplo):")
    linux_success = test_linux_connection("K004")

    # 4. Detección automática
    test_store_detection()

    # 5. Recomendaciones
    print_header("RECOMENDACIONES")

    if not win_success and not linux_success:
        print("❌ No hay conexiones disponibles")
        print("\n💡 SOLUCIONES:")
        print("1. Verificar que MAXPOINT esté ejecutándose")
        print("2. Verificar permisos de red")
        print("3. Probar con autenticación SQL:")
        print("   - Configure DB_USERNAME y DB_PASSWORD en .env")
        print("   - Cambie USE_TRUSTED_CONNECTION=False")
    elif win_success:
        print("✅ Conexión Windows funcionando")
        print("\n💡 Configuración recomendada:")
        print(f"   WINDOWS_SERVER={WINDOWS_SERVER}")
        print(f"   WINDOWS_INSTANCE={WINDOWS_INSTANCE}")
        print(f"   USE_TRUSTED_CONNECTION=True")
    elif linux_success:
        print("✅ Conexión Linux funcionando")
        print("\n💡 Configuración recomendada:")
        print(f"   LINUX_SERVER_PREFIX={LINUX_SERVER_PREFIX}")
        print(f"   DB_USERNAME y DB_PASSWORD configurados")

    print("\n" + "=" * 60)
    print("  DIAGNÓSTICO COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()