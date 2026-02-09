"""
Utilidades para manejar Markdown en Telegram
"""

import re


def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiales de Markdown V2

    Caracteres a escapar: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return ""

    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def escape_markdown_url(url: str) -> str:
    """Escapa una URL para Markdown V2"""
    return escape_markdown(url)


def safe_markdown_text(text: str) -> str:
    """
    Prepara texto seguro para Markdown
    - Escapa caracteres especiales
    - Limita longitud
    - Reemplaza caracteres problemáticos
    """
    if not text:
        return ""

    # 1. Escapar Markdown
    text = escape_markdown(text)

    # 2. Reemplazar caracteres problemáticos adicionales
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # 3. Limitar longitud (para evitar errores de Telegram)
    max_length = 4000  # Límite seguro de Telegram
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def create_markdown_message(title: str, content: str = "", items: list = None) -> str:
    """
    Crea un mensaje con formato Markdown seguro
    """
    message_parts = []

    if title:
        message_parts.append(f"*{escape_markdown(title)}*")

    if content:
        message_parts.append(escape_markdown(content))

    if items:
        for item in items:
            if isinstance(item, str):
                message_parts.append(f"• {escape_markdown(item)}")
            elif isinstance(item, tuple) and len(item) == 2:
                key, value = item
                message_parts.append(f"• *{escape_markdown(str(key))}:* {escape_markdown(str(value))}")

    return "\n".join(message_parts)