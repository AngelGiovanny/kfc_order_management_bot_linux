"""
Módulo para generación de reportes Excel
"""

import os
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def generar_excel_auditoria(datos: List[Dict[str, Any]], store_code: str, fecha, hora) -> str:
    """
    Genera un archivo Excel a partir de los datos de auditoría

    Args:
        datos: Lista de diccionarios con los datos
        store_code: Código de tienda
        fecha: Fecha del reporte
        hora: Hora del reporte

    Returns:
        str: Ruta del archivo Excel generado
    """
    try:
        if not datos:
            logger.warning("No hay datos para generar Excel")
            return None

        # Crear DataFrame
        df = pd.DataFrame(datos)

        # Renombrar columnas para mejor presentación
        columnas_espanol = {
            'codigo_app': 'Código App',
            'estado': 'Estado',
            'fecha': 'Fecha',
            'nombres': 'Nombres',
            'empresa_motorolo': 'Empresa Motorolo',
            'documento': 'Documento'
        }

        # Solo renombrar columnas que existen
        columnas_existentes = {k: v for k, v in columnas_espanol.items() if k in df.columns}
        df.rename(columns=columnas_existentes, inplace=True)

        # Formatear fecha si existe
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # Reemplazar NaN por string vacío
        df = df.fillna('')

        # Crear nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fecha_str = fecha.strftime('%Y%m%d') if hasattr(fecha, 'strftime') else str(fecha).replace('-', '')
        hora_str = hora.strftime('%H%M') if hasattr(hora, 'strftime') else str(hora).replace(':', '')

        filename = f"auditoria_{store_code}_{fecha_str}_{hora_str}_{timestamp}.xlsx"

        # Crear carpeta temp si no existe
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        filepath = os.path.join(temp_dir, filename)

        # Guardar a Excel con formato
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Auditoría', index=False)

            # Obtener worksheet
            worksheet = writer.sheets['Auditoría']

            # Ajustar ancho de columnas automáticamente
            for idx, col in enumerate(df.columns):
                # Calcular ancho máximo
                max_len = max(
                    df[col].astype(str).map(len).max(),  # largo de datos
                    len(str(col))  # largo del encabezado
                ) + 2  # margen adicional

                # Limitar ancho máximo a 50
                column_width = min(max_len, 50)

                # Ajustar columna (openpyxl usa letras, empezando en 65 = 'A')
                col_letter = chr(65 + idx)
                worksheet.column_dimensions[col_letter].width = column_width

            # Dar formato al encabezado
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)

        logger.info(f"✅ Excel generado: {filepath} ({len(datos)} registros)")
        return filepath

    except Exception as e:
        logger.error(f"Error generando Excel: {e}")
        # Intentar guardar versión simple si falla el formateo
        try:
            # Versión simple sin formateo
            df_simple = pd.DataFrame(datos)
            df_simple = df_simple.fillna('')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fecha_str = fecha.strftime('%Y%m%d') if hasattr(fecha, 'strftime') else str(fecha).replace('-', '')

            filename = f"auditoria_simple_{store_code}_{fecha_str}_{timestamp}.xlsx"
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
            os.makedirs(temp_dir, exist_ok=True)

            filepath = os.path.join(temp_dir, filename)
            df_simple.to_excel(filepath, index=False)

            logger.info(f"✅ Excel simple generado: {filepath}")
            return filepath

        except Exception as e2:
            logger.error(f"Error incluso en versión simple: {e2}")
            return None


def limpiar_archivos_temporales(dias: int = 1):
    """
    Limpia archivos temporales más antiguos que 'dias'
    """
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        if not os.path.exists(temp_dir):
            return

        ahora = datetime.now()
        archivos_eliminados = 0

        for filename in os.listdir(temp_dir):
            if filename.startswith('auditoria_') and filename.endswith('.xlsx'):
                filepath = os.path.join(temp_dir, filename)
                fecha_mod = datetime.fromtimestamp(os.path.getmtime(filepath))

                if (ahora - fecha_mod).days >= dias:
                    os.remove(filepath)
                    archivos_eliminados += 1

        if archivos_eliminados > 0:
            logger.info(f"Limpieza: {archivos_eliminados} archivos temporales eliminados")

    except Exception as e:
        logger.error(f"Error limpiando archivos temporales: {e}")