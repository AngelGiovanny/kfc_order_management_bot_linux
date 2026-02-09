#!/usr/bin/env python3
"""
Verifica que todas las importaciones funcionen
"""

import os
import sys

print("🔍 Verificando importaciones...")

# Agregar directorio actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config.settings import BOT_TOKEN, WINDOWS_SERVER, WINDOWS_INSTANCE

    print("✅ config.settings: OK")
    print(f"   BOT_TOKEN: {'Configurado' if BOT_TOKEN else 'NO configurado'}")
    print(f"   WINDOWS_SERVER: {WINDOWS_SERVER}")
    print(f"   WINDOWS_INSTANCE: {WINDOWS_INSTANCE}")
except ImportError as e:
    print(f"❌ config.settings: {e}")

try:
    from core.os_detector import OSDetector

    print("✅ core.os_detector: OK")

    # Probar detección
    result = OSDetector.detect_os("K004", quick=True)
    print(f"   K004 -> {result}")
except ImportError as e:
    print(f"❌ core.os_detector: {e}")
except Exception as e:
    print(f"⚠️  core.os_detector error: {e}")

try:
    from core.network_detector import NetworkDetector

    print("✅ core.network_detector: OK")
except ImportError as e:
    print(f"❌ core.network_detector: {e}")

try:
    from config.database import db_manager

    print("✅ config.database: OK")
except ImportError as e:
    print(f"❌ config.database: {e}")

try:
    from utils.logger import get_logger

    print("✅ utils.logger: OK")
except ImportError as e:
    print(f"❌ utils.logger: {e}")

print("\n🎯 Prueba completada")