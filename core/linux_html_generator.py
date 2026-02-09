"""
Generador de HTML optimizado para Linux
"""

import urllib.parse
from datetime import datetime
from typing import Dict, Any
import platform
from utils.logger import get_logger

logger = get_logger(__name__)


class LinuxHTMLGenerator:
    """Genera HTML optimizado para Linux"""

    def __init__(self):
        self.system = platform.system()
        self.is_linux = (self.system == "Linux")

    def generate_invoice_html(self, url: str) -> str:
        """Genera HTML para factura/nota crédito"""
        return self._generate_document_html(url, "invoice")

    def generate_comanda_html(self, url: str) -> str:
        """Genera HTML para comanda"""
        return self._generate_document_html(url, "comanda")

    def _generate_document_html(self, url: str, doc_type: str) -> str:
        """Genera HTML según tipo de documento"""
        parsed_url = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed_url.query)

        # Extraer parámetros
        cfac_id = params.get('cfac_id', [''])[0]
        tipo = params.get('tipo_comprobante', [''])[0]
        order_id = params.get('odp_id', [''])[0]

        # Determinar tipo de documento
        if doc_type == "comanda":
            title = f"COMANDA #{order_id[:8] if order_id else 'N/A'}"
            icon = "🍗"
        else:
            if tipo == 'N':
                title = f"NOTA DE CRÉDITO #{cfac_id}"
                icon = "📋"
            else:
                title = f"FACTURA #{cfac_id}"
                icon = "📄"

        # HTML ultra simple que SI funciona en Linux
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - KFC</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f2f5;
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(90deg, #e63946, #d90429);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .info-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #e63946;
        }}
        .info-row {{
            display: flex;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #dee2e6;
        }}
        .info-label {{
            font-weight: bold;
            width: 150px;
            color: #495057;
        }}
        .info-value {{
            flex: 1;
            color: #212529;
            word-break: break-word;
        }}
        .footer {{
            background: #343a40;
            color: white;
            padding: 15px;
            text-align: center;
            font-size: 12px;
            margin-top: 30px;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 12px;
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{icon} {title}</h1>
            <p>Sistema de Gestión KFC</p>
        </div>

        <div class="content">
            <div class="info-card">
                <h3>📋 Información del Documento</h3>

                <div class="info-row">
                    <div class="info-label">Documento:</div>
                    <div class="info-value">{title}</div>
                </div>

                <div class="info-row">
                    <div class="info-label">ID Principal:</div>
                    <div class="info-value">{cfac_id or order_id or 'N/A'}</div>
                </div>

                <div class="info-row">
                    <div class="info-label">Tipo:</div>
                    <div class="info-value">{'COMANDA' if doc_type == 'comanda' else ('NOTA DE CRÉDITO' if tipo == 'N' else 'FACTURA')}</div>
                </div>

                <div class="info-row">
                    <div class="info-label">URL Origen:</div>
                    <div class="info-value" style="font-size: 11px;">{url[:80]}...</div>
                </div>
            </div>

            <div class="info-card" style="background: #fff3cd; border-left-color: #ffc107;">
                <h3>⚠️ Nota del Sistema</h3>
                <p>Este es un documento generado automáticamente por el sistema KFC.</p>
                <p>Para el documento oficial completo, consulte el sistema POS.</p>
                <p><strong>Sistema:</strong> Bot KFC - Servidor Linux</p>
            </div>
        </div>

        <div class="timestamp">
            Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}
        </div>

        <div class="footer">
            <p>© {datetime.now().year} International Food Services - Grupo KFC</p>
            <p>Documento generado automáticamente - Sistema Linux</p>
        </div>
    </div>
</body>
</html>"""

        return html


# Instancia global
linux_html_generator = LinuxHTMLGenerator()