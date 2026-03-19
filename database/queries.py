"""
QUERIES OPTIMIZADAS PARA KFC ORDER MANAGEMENT BOT
CON TABLA pickup_cabecera_pedidos INCLUIDA
"""

# Order status verification - QUERY UNIFICADA Y OPTIMIZADA CON 3 TABLAS
ORDER_STATUS_QUERY = """
    -- Tabla 1: Cabecera_App (pedidos normales)
SELECT 
    codigo_app, 
    estado, 
    cfac_id, 
    medio, 
    fecha_Pedido,
    COALESCE(m.nombres + ' ' + m.apellidos, 'No asignado') as motorizado,
    'App' as fuente
FROM Cabecera_App ca
LEFT JOIN Motorolo m ON ca.IDMotorolo = m.IDMotorolo
WHERE ca.codigo_app LIKE '%' + ? + '%'

UNION ALL

-- Tabla 2: kiosko_cabecera_pedidos (pedidos de kiosko)
SELECT 
    codigo_app,
    estado_maxpoint as estado,
    cfac_id,
    '' as medio,
    GETDATE() as fecha_Pedido,
    'No asignado' as motorizado,
    'Kiosko' as fuente
FROM kiosko_cabecera_pedidos 
WHERE codigo_app LIKE '%' + ? + '%'

UNION ALL

-- Tabla 3: pickup_cabecera_pedidos (pedidos de pickup/recoger)
SELECT 
    codigo_app,
    estado_maxpoint as estado,
    cfac_id,
    '' as medio,
    GETDATE() as fecha_Pedido,
    'No asignado' as motorizado,
    'Pickup' as fuente
FROM pickup_cabecera_pedidos 
WHERE codigo_app LIKE '%' + ? + '%'
"""

# Order audit - QUERY CORREGIDA: SOLO Estado_Pedido_App (historial de estados)
ORDER_AUDIT_QUERY = """
    -- Auditoría de pedidos de App (historial de estados)
    SELECT 
        epa.codigo_app,
        epa.estado,
        epa.fecha,
        COALESCE(m.nombres + ' ' + m.apellidos, 'No asignado') as motorizado,
        'App' as fuente
    FROM Estado_Pedido_App epa WITH(NOLOCK)
    LEFT JOIN Cabecera_App ca WITH(NOLOCK) ON epa.codigo_app = ca.codigo_app
    LEFT JOIN Motorolo m WITH(NOLOCK) ON ca.IDMotorolo = m.IDMotorolo
    WHERE epa.codigo_app LIKE ?
    ORDER BY epa.fecha ASC
"""

# Get comanda URL - QUERY DIRECTA
COMANDA_URL_QUERY = """
    SELECT TOP 1 IDCabeceraordenPedido 
    FROM Cabecera_Factura WITH(NOLOCK)
    WHERE cfac_id = ?
"""

# Get associated code - QUERY CORREGIDA: Cabecera_App + pickup_cabecera_pedidos
ASSOCIATED_CODE_QUERY = """
    -- Códigos asociados de Cabecera_App
    SELECT TOP 1 codigo_app 
    FROM Cabecera_App WITH(NOLOCK) 
    WHERE cfac_id = ?

    UNION ALL

    -- Códigos asociados de pickup_cabecera_pedidos
    SELECT TOP 1 codigo_app 
    FROM pickup_cabecera_pedidos WITH(NOLOCK) 
    WHERE cfac_id = ?
"""

# Get print data for reprints - QUERY OPTIMIZADA
PRINT_DATA_QUERY = """
    SELECT TOP 1 imp_url, Canal_MovimientoVarchar1 
    FROM Canal_Movimiento WITH(NOLOCK)
    WHERE Canal_MovimientoVarchar3 LIKE ? 
    AND imp_varchar1 LIKE ?
"""

# Validación de tienda rápida
VALIDATE_STORE_QUERY = """
    SELECT TOP 1 1 
    FROM information_schema.tables WITH(NOLOCK) 
    WHERE table_catalog = ?
"""

# Get invoice data
INVOICE_DATA_QUERY = """
    SELECT TOP 1 
        cfac_id,
        cfac_numero,
        cfac_fecha,
        cfac_total,
        cli_nombre,
        cli_ruc,
        cli_direccion,
        cli_telefono
    FROM Cabecera_Factura WITH(NOLOCK)
    WHERE cfac_id = ?
"""

# Get order details
ORDER_DETAILS_QUERY = """
    SELECT 
        producto_nombre,
        cantidad,
        precio_unitario,
        subtotal
    FROM Detalle_Factura WITH(NOLOCK)
    WHERE cfac_id = ?
"""

# QUERY NUEVA: Verificar existencia de órdenes en pickup
CHECK_PICKUP_ORDER_QUERY = """
    SELECT TOP 1 
        codigo_app,
        estado_maxpoint,
        cfac_id,
        fecha_creacion
    FROM pickup_cabecera_pedidos WITH(NOLOCK)
    WHERE codigo_app LIKE ?
    ORDER BY fecha_creacion DESC
"""

# QUERY NUEVA: Buscar orden en todas las tablas
SEARCH_ALL_ORDERS_QUERY = """
    SELECT 
        'App' as fuente,
        codigo_app,
        estado,
        cfac_id,
        fecha_Pedido as fecha
    FROM Cabecera_App WITH(NOLOCK)
    WHERE codigo_app LIKE ?

    UNION ALL

    SELECT 
        'Kiosko' as fuente,
        codigo_app,
        estado_maxpoint as estado,
        cfac_id,
        fecha_creacion as fecha
    FROM kiosko_cabecera_pedidos WITH(NOLOCK)
    WHERE codigo_app LIKE ?

    UNION ALL

    SELECT 
        'Pickup' as fuente,
        codigo_app,
        estado_maxpoint as estado,
        cfac_id,
        fecha_creacion as fecha
    FROM pickup_cabecera_pedidos WITH(NOLOCK)
    WHERE codigo_app LIKE ?

    ORDER BY fecha DESC
"""

# ============================================================================
# QUERY PARA AUDITORÍA POR RANGO
# ============================================================================
AUDITORIA_RANGO_QUERY = """
    SELECT 
        e.codigo_app,
        e.estado,
        e.fecha,
        m.nombres,
        m.empresa_motorolo,
        m.documento
    FROM Estado_Pedido_App e WITH(NOLOCK)
    LEFT JOIN Motorolo m WITH(NOLOCK) ON e.IDMotorolo = m.IDMotorolo
    WHERE CAST(e.fecha AS DATE) BETWEEN ? AND ?
      AND CAST(e.fecha AS TIME) BETWEEN ? AND ?
    ORDER BY e.fecha ASC
"""


class QueryManager:
    """Gestor de consultas"""

    @staticmethod
    def get_order_status_query():
        """Para verificar estado actual - 3 marcadores"""
        return ORDER_STATUS_QUERY

    @staticmethod
    def get_order_audit_query():
        """Para historial de estados - 1 marcador"""
        return ORDER_AUDIT_QUERY

    @staticmethod
    def get_comanda_url_query():
        """Para URL de comanda - 1 marcador"""
        return COMANDA_URL_QUERY

    @staticmethod
    def get_associated_code_query():
        """Para códigos asociados - 2 marcadores (Cabecera_App + pickup)"""
        return ASSOCIATED_CODE_QUERY

    @staticmethod
    def get_print_data_query():
        """Para datos de impresión - 2 marcadores"""
        return PRINT_DATA_QUERY

    @staticmethod
    def get_validate_store_query():
        """Para validar tienda - 1 marcador"""
        return VALIDATE_STORE_QUERY

    @staticmethod
    def get_invoice_data_query():
        """Para datos de factura - 1 marcador"""
        return INVOICE_DATA_QUERY

    @staticmethod
    def get_order_details_query():
        """Para detalles de orden - 1 marcador"""
        return ORDER_DETAILS_QUERY

    @staticmethod
    def get_check_pickup_order_query():
        """Para verificar órdenes en pickup - 1 marcador"""
        return CHECK_PICKUP_ORDER_QUERY

    @staticmethod
    def get_search_all_orders_query():
        """Para buscar en todas las tablas - 3 marcadores"""
        return SEARCH_ALL_ORDERS_QUERY

    @staticmethod
    def get_auditoria_rango_query():
        """Para auditoría por rango de fechas y horas - 4 marcadores"""
        return AUDITORIA_RANGO_QUERY


# ============================================================================
# FUNCIÓN PARA CONSULTAR POR RANGO (VERSIÓN ORIGINAL)
# ============================================================================
async def consultar_pedidos_por_rango(store_code: str, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
    """
    Ejecuta consulta de auditoría por rango de fechas y horas
    Retorna lista de diccionarios con los resultados
    """
    try:
        from config.database import db_manager
        import logging
        logger = logging.getLogger(__name__)

        # Obtener conexión
        connection = db_manager.get_connection(store_code)
        if not connection:
            logger.error(f"No se pudo conectar a la tienda {store_code}")
            return []

        cursor = connection.cursor()
        try:
            # Ejecutar consulta
            query = AUDITORIA_RANGO_QUERY

            # Convertir fechas y horas a string para la consulta
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d') if hasattr(fecha_inicio, 'strftime') else str(fecha_inicio)
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d') if hasattr(fecha_fin, 'strftime') else str(fecha_fin)
            hora_inicio_str = hora_inicio.strftime('%H:%M:%S') if hasattr(hora_inicio, 'strftime') else str(hora_inicio)
            hora_fin_str = hora_fin.strftime('%H:%M:%S') if hasattr(hora_fin, 'strftime') else str(hora_fin)

            cursor.execute(query, (fecha_inicio_str, fecha_fin_str, hora_inicio_str, hora_fin_str))

            # Obtener resultados
            results = cursor.fetchall()

            # Convertir a lista de diccionarios
            datos = []
            for row in results:
                datos.append({
                    'codigo_app': row[0],
                    'estado': row[1],
                    'fecha': row[2],
                    'nombres': row[3],
                    'empresa_motorolo': row[4],
                    'documento': row[5]
                })

            logger.info(f"Consulta por rango: {len(datos)} registros encontrados")
            return datos

        except Exception as e:
            logger.error(f"Error ejecutando consulta por rango: {e}")
            return []
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en consultar_pedidos_por_rango: {e}")
        return []


# ============================================================================
# NUEVA FUNCIÓN: CONSULTA POR RANGO SIMPLE (SIN CONVERSIÓN COMPLEJA)
# ============================================================================
async def consultar_pedidos_por_rango_simple(store_code: str, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
    """
    Ejecuta consulta de auditoría por rango de fechas y horas - VERSIÓN SIMPLIFICADA
    Retorna lista de diccionarios con los resultados
    """
    try:
        from config.database import db_manager
        import logging
        logger = logging.getLogger(__name__)

        # Obtener conexión
        connection = db_manager.get_connection(store_code)
        if not connection:
            logger.error(f"No se pudo conectar a la tienda {store_code}")
            return []

        cursor = connection.cursor()
        try:
            # Consulta SQL directa SIN DECLARE
            query = """
                SELECT 
                    e.codigo_app,
                    e.estado,
                    e.fecha,
                    m.nombres,
                    m.empresa_motorolo,
                    m.documento
                FROM Estado_Pedido_App e WITH(NOLOCK)
                LEFT JOIN Motorolo m WITH(NOLOCK) ON e.IDMotorolo = m.IDMotorolo
                WHERE CAST(e.fecha AS DATE) BETWEEN ? AND ?
                  AND CAST(e.fecha AS TIME) BETWEEN ? AND ?
                ORDER BY e.fecha ASC
            """

            # Convertir fechas a string
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d') if hasattr(fecha_inicio, 'strftime') else str(fecha_inicio)
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d') if hasattr(fecha_fin, 'strftime') else str(fecha_fin)

            cursor.execute(query, (fecha_inicio_str, fecha_fin_str, hora_inicio, hora_fin))

            # Obtener resultados
            results = cursor.fetchall()

            # Convertir a lista de diccionarios
            datos = []
            for row in results:
                datos.append({
                    'codigo_app': row[0],
                    'estado': row[1],
                    'fecha': row[2],
                    'nombres': row[3],
                    'empresa_motorolo': row[4],
                    'documento': row[5]
                })

            logger.info(f"Consulta por rango simple: {len(datos)} registros encontrados")
            return datos

        except Exception as e:
            logger.error(f"Error ejecutando consulta por rango simple: {e}")
            return []
        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Error en consultar_pedidos_por_rango_simple: {e}")
        return []