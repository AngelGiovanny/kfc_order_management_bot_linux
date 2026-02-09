import logging
import json
import requests
from telegram import Update
from telegram.ext import ContextTypes
from config.database import get_db_connection

logger = logging.getLogger(__name__)


async def print_document(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         doc_type: str, doc_id: str, store_code: str):
    """Proceso de impresión con 3 intentos"""

    logger.info(f"Iniciando impresión de {doc_type} {doc_id} para tienda {store_code}")

    # Intento 1: Usar datos de Canal_Movimiento
    success = await try_print_method_1(update, doc_type, doc_id, store_code)
    if success:
        return

    # Intento 2: Generar JSON con stored procedure
    success = await try_print_method_2(update, doc_type, doc_id, store_code)
    if success:
        return

    # Intento 3: Usar API directa
    await try_print_method_3(update, doc_type, doc_id, store_code)


async def try_print_method_1(update: Update, doc_type: str, doc_id: str, store_code: str) -> bool:
    """Intento 1: Usar datos existentes en Canal_Movimiento"""
    try:
        conn = get_db_connection(store_code)
        cursor = conn.cursor()

        # Consulta diferente según tipo de documento
        if doc_type == 'factura':
            query = """
                SELECT 
                    cm.imp_ip_estacion,
                    cm.imp_impresora,
                    cm.Canal_MovimientoVarchar1,
                    cf.cfac_id AS Valor
                FROM Canal_Movimiento cm
                JOIN Cabecera_Factura cf
                    ON cf.cfac_id = cm.Canal_MovimientoVarchar3
                WHERE cf.cfac_id = ?
            """
            cursor.execute(query, (doc_id,))

        elif doc_type == 'comanda':
            query = """
                SELECT 
                    cm.imp_ip_estacion,
                    cm.imp_impresora,
                    cm.Canal_MovimientoVarchar1,
                    cf.IDCabeceraOrdenPedido AS Valor
                FROM Canal_Movimiento cm
                JOIN Cabecera_Factura cf
                    ON cf.cfac_id = cm.Canal_MovimientoVarchar3
                WHERE cf.cfac_id = ?
            """
            cursor.execute(query, (doc_id,))

        elif doc_type == 'nota_credito':
            query = """
                SELECT 
                    cm.imp_ip_estacion,
                    cm.imp_impresora,
                    cm.Canal_MovimientoVarchar1,
                    cf.cfac_id AS Valor
                FROM Canal_Movimiento cm
                JOIN Cabecera_Factura cf
                    ON cf.cfac_id = cm.Canal_MovimientoVarchar3
                WHERE cf.cfac_id = ?
            """
            cursor.execute(query, (doc_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            ip_estacion, impresora, json_data, valor = row

            if json_data:
                # Parsear JSON y enviar a impresión
                json_dict = json.loads(json_data)
                id_impresora = json_dict.get("idImpresora", "desconocida")

                # Construir URL de impresión
                print_url = f"http://{ip_estacion}:5000/api/ImpresionTickets/Impresion"

                # Enviar a impresión
                response = requests.post(print_url, json=json_dict, timeout=10)

                if response.status_code == 200:
                    await update.message.reply_text(
                        f"✅ Re-impresión enviada a {id_impresora}, por favor verificar."
                    )
                    return True

        return False

    except Exception as e:
        logger.error(f"Error en método 1 de impresión: {e}")
        return False


async def try_print_method_2(update: Update, doc_type: str, doc_id: str, store_code: str) -> bool:
    """Intento 2: Generar JSON con stored procedure"""
    try:
        conn = get_db_connection(store_code)
        cursor = conn.cursor()

        # Primero obtener la IP de la estación
        cursor.execute("""
            SELECT TOP 1 imp_ip_estacion 
            FROM Canal_Movimiento 
            WHERE Canal_MovimientoVarchar3 LIKE ?
        """, (f'%{doc_id}%',))

        row = cursor.fetchone()
        if not row:
            return False

        ip_estacion = row[0]

        # Ejecutar stored procedure para generar JSON
        sql = """
            DECLARE @impresiones TABLE
            (
                numeroImpresiones   INT,
                tipo			    VARCHAR(50), 
                impresora		    VARCHAR(50), 
                formatoXML	        NVARCHAR(MAX), 
                jsonData		    NVARCHAR(MAX), 
                jsonRegistros	    NVARCHAR(MAX)
            );

            INSERT INTO @impresiones
            EXEC [facturacion].[IAE_TipoFacturacion] ?, ?

            SELECT 
                '{"numeroImpresiones": '+ CONVERT(VARCHAR,numeroImpresiones) +', "tipo": "'+ tipo +'", "idImpresora": "'+ impresora +'", "idPlantilla": "'+ REPLACE(formatoXML,'/\\\\/g','') +'", "data": '+ jsonData +', "registros": '+ jsonRegistros +' }' 
            FROM @impresiones 
        """

        cursor.execute(sql, (doc_id, f'10.101.{store_code.lower()}.{ip_estacion.split(".")[-1]}'))

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            json_str = result[0]
            json_dict = json.loads(json_str)

            # Enviar a impresión
            print_url = f"http://{ip_estacion}:5000/api/ImpresionTickets/Impresion"
            response = requests.post(print_url, json=json_dict, timeout=10)

            if response.status_code == 200:
                id_impresora = json_dict.get("idImpresora", "desconocida")
                await update.message.reply_text(
                    f"✅ Re-impresión enviada a {id_impresora}, por favor verificar."
                )
                return True

        return False

    except Exception as e:
        logger.error(f"Error en método 2 de impresión: {e}")
        return False


async def try_print_method_3(update: Update, doc_type: str, doc_id: str, store_code: str):
    """Intento 3: API directa"""
    try:
        # Obtener IP de estación por defecto
        default_ip = f"10.101.{store_code.lower()}.20"

        # Construir objeto JSON básico
        json_data = {
            "numeroImpresiones": 1,
            "tipo": doc_type,
            "idImpresora": "default",
            "idPlantilla": "",
            "data": {"documento": doc_id},
            "registros": []
        }

        # Enviar a API
        print_url = f"http://{default_ip}:5000/api/ImpresionTickets/Impresion"
        response = requests.post(print_url, json=json_data, timeout=10)

        if response.status_code == 200:
            await update.message.reply_text(
                "✅ Re-impresión enviada a impresora por defecto, por favor verificar."
            )
        else:
            await update.message.reply_text(
                f"❌ No se pudo enviar la re-impresión después de 3 intentos.\n"
                f"Documento: {doc_id}\n"
                f"Tienda: {store_code}"
            )

    except Exception as e:
        logger.error(f"Error en método 3 de impresión: {e}")
        await update.message.reply_text(
            f"❌ Error en el proceso de impresión: {str(e)}"
        )