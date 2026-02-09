# diagnostic_os.py
import os
import sys
import platform

print("=" * 60)
print("DIAGNÓSTICO COMPLETO DEL SISTEMA")
print("=" * 60)

info = {
    "Python": sys.version,
    "Platform": platform.platform(),
    "System": platform.system(),
    "Release": platform.release(),
    "Version": platform.version(),
    "Machine": platform.machine(),
    "Processor": platform.processor(),
    "sys.platform": sys.platform,
    "OSTYPE": os.environ.get('OSTYPE', 'NO DEFINIDO'),
    "OS": os.environ.get('OS', 'NO DEFINIDO'),
    "/etc/os-release": "EXISTE" if os.path.exists('/etc/os-release') else "NO EXISTE",
    "C:\\Windows": "EXISTE" if os.path.exists('C:\\Windows') else "NO EXISTE",
    "/proc/version": "EXISTE" if os.path.exists('/proc/version') else "NO EXISTE",
}

for key, value in info.items():
    print(f"{key:20}: {value}")

print("=" * 60)