"""
Generador de imágenes desde JSON de impresión - EXCLUSIVO PARA LINUX
Versión simplificada que usa JSON directo de tablas existentes
"""

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from PIL import Image, ImageDraw, ImageFont

from utils.logger import get_logger

logger = get_logger(__name__)


class LinuxJsonImager:
    """Genera imágenes desde JSON de impresión - SOLO LINUX - SIMPLIFICADO"""

    def __init__(self):
        # Verificar que estamos en Linux
        self.system = platform.system()
        if self.system != "Linux":
            logger.error(f"❌ Este módulo es solo para Linux. Sistema: {self.system}")
            raise RuntimeError("Este módulo es exclusivo para Linux")

        logger.info("✅ LinuxJsonImager inicializado (solo Linux)")

        # Directorio para imágenes generadas
        self.output_dir = Path("linux_json_images")
        self.output_dir.mkdir(exist_ok=True)

        # Configuración
        self.page_width = 800
        self.page_height = 1200
        self.margin = 40
        self.line_height = 25

        # Cargar fuentes Linux
        self._load_linux_fonts()

    def _load_linux_fonts(self):
        """Carga fuentes comunes de Linux"""
        try:
            # Fuentes Linux más comunes
            linux_font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            ]

            self.font_normal = None
            self.font_bold = None
            self.font_large = None

            for font_path in linux_font_paths:
                if os.path.exists(font_path):
                    try:
                        self.font_normal = ImageFont.truetype(font_path, 12)
                        self.font_bold = ImageFont.truetype(font_path, 12)  # Mismo para simplificar
                        self.font_large = ImageFont.truetype(font_path, 18)
                        logger.info(f"✅ Fuente cargada: {font_path}")
                        break
                    except Exception as e:
                        continue

            # Fallback
            if not self.font_normal:
                self.font_normal = ImageFont.load_default()
                self.font_bold = self.font_normal
                self.font_large = self.font_normal
                logger.warning("⚠️ Usando fuente por defecto")

        except Exception as e:
            logger.error(f"Error cargando fuentes: {e}")
            self.font_normal = ImageFont.load_default()
            self.font_bold = self.font_normal
            self.font_large = self.font_normal

    def get_json_from_canal_movimiento(self, store_code: str, cfac_id: str) -> Optional[Dict]:
        """Obtiene JSON directamente de Canal_Movimiento"""
        try:
            from config.database import db_manager

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"❌ No hay conexión a BD para {store_code}")
                return None

            cursor = connection.cursor()

            # BUSCAR JSON EN Canal_MovimientoVarchar1 (como en tu código de impresión)
            query = """
                SELECT TOP 1
                    cm.Canal_MovimientoVarchar1 AS json_data,
                    cm.imp_impresora,
                    cf.cfac_fecha,
                    cf.cli_nombre,
                    cf.cli_ruc,
                    cf.cli_direccion
                FROM Canal_Movimiento cm
                JOIN Cabecera_Factura cf ON cf.cfac_id = cm.Canal_MovimientoVarchar3
                WHERE cf.cfac_id = ?
                ORDER BY cm.Canal_MovimientoFecha DESC
            """

            cursor.execute(query, (cfac_id,))
            row = cursor.fetchone()

            if row and row[0]:
                json_str = row[0]
                try:
                    # Parsear JSON
                    json_data = json.loads(json_str)

                    # Agregar metadatos adicionales
                    json_data["_metadata"] = {
                        "impresora": row[1],
                        "fecha": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else None,
                        "cliente_nombre": row[3],
                        "cliente_ruc": row[4],
                        "cliente_direccion": row[5]
                    }

                    logger.info(f"✅ JSON obtenido de Canal_Movimiento para {cfac_id}")
                    return json_data

                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON inválido en Canal_MovimientoVarchar1: {e}")

            logger.warning(f"⚠️ No se encontró JSON en Canal_Movimiento para {cfac_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo JSON de Canal_Movimiento: {e}")
            return None
        finally:
            try:
                cursor.close()
                connection.close()
            except:
                pass

    def get_json_from_sp_result(self, store_code: str, cfac_id: str) -> Optional[Dict]:
        """Obtiene JSON ejecutando el stored procedure de impresión"""
        try:
            from config.database import db_manager

            connection = db_manager.get_connection(store_code)
            if not connection:
                logger.error(f"❌ No hay conexión a BD para {store_code}")
                return None

            cursor = connection.cursor()

            # Extraer número de tienda
            store_number = store_code[1:] if store_code.startswith('K') else store_code
            store_number = store_number.lstrip('0') or "1"

            # Ejecutar SP como en tu código de impresión (versión simplificada)
            sql = f"""
                DECLARE @jsonResult NVARCHAR(MAX);

                EXEC [facturacion].[IAE_TipoFacturacion] 
                    @pDocumento = N'{cfac_id}',
                    @pServerAddress = N'10.101.{store_number}.21',
                    @pJsonOutput = @jsonResult OUTPUT;

                SELECT @jsonResult AS JsonData;
            """

            logger.info(f"🔄 Ejecutando SP para obtener JSON de {cfac_id}")

            cursor.execute(sql)
            row = cursor.fetchone()

            if row and row[0]:
                json_str = row[0]

                # Limpiar JSON si viene entre comillas
                if json_str.startswith('"') and json_str.endswith('"'):
                    json_str = json_str[1:-1].replace('\\"', '"')

                try:
                    json_data = json.loads(json_str)
                    logger.info(f"✅ JSON obtenido del SP para {cfac_id}")
                    return json_data
                except json.JSONDecodeError:
                    # Intentar limpiar más
                    json_str = json_str.replace('\\\\', '\\')
                    try:
                        json_data = json.loads(json_str)
                        return json_data
                    except:
                        logger.error(f"❌ JSON del SP no se pudo parsear: {json_str[:100]}...")

            return None

        except Exception as e:
            logger.error(f"❌ Error ejecutando SP: {e}")
            return None
        finally:
            try:
                cursor.close()
                connection.close()
            except:
                pass

    def generate_image_from_json(self, json_data: Dict, store_code: str,
                                 cfac_id: str, doc_type: str = "FACTURA") -> Optional[bytes]:
        """Genera imagen desde JSON - Versión simplificada para Linux"""
        try:
            logger.info(f"🔄 Generando imagen desde JSON para {cfac_id}")

            # Verificar que tenemos datos
            if not json_data:
                logger.error("❌ JSON data está vacío")
                return None

            # Crear imagen
            image = Image.new('RGB', (self.page_width, self.page_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)

            y = self.margin

            # 1. ENCABEZADO KFC
            draw.text(
                (self.page_width // 2, y),
                "🍗 KENTUCKY FRIED CHICKEN",
                fill=(227, 0, 43),  # Rojo KFC
                font=self.font_large,
                anchor="mm"
            )
            y += 40

            # 2. TIPO DE DOCUMENTO
            doc_title = "FACTURA"
            if doc_type.upper() == "NOTA_CREDITO":
                doc_title = "NOTA DE CRÉDITO"
            elif doc_type.upper() == "COMANDA":
                doc_title = "COMANDA"

            draw.text(
                (self.page_width // 2, y),
                doc_title,
                fill=(0, 0, 0),
                font=self.font_large,
                anchor="mm"
            )
            y += 40

            # Línea divisoria
            draw.line(
                [(self.margin, y), (self.page_width - self.margin, y)],
                fill=(200, 200, 200),
                width=2
            )
            y += 20

            # 3. INFORMACIÓN BÁSICA
            draw.text(
                (self.margin, y),
                f"🏪 Tienda: {store_code}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += self.line_height

            draw.text(
                (self.margin, y),
                f"📄 Documento: {cfac_id}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += self.line_height

            # Fecha
            fecha = json_data.get("_metadata", {}).get("fecha", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            draw.text(
                (self.margin, y),
                f"📅 Fecha: {fecha}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += self.line_height

            # Cliente (si está disponible)
            cliente_nombre = json_data.get("_metadata", {}).get("cliente_nombre", "")
            if cliente_nombre:
                draw.text(
                    (self.margin, y),
                    f"👤 Cliente: {cliente_nombre}",
                    fill=(0, 0, 0),
                    font=self.font_normal
                )
                y += self.line_height

            y += 10  # Espacio extra

            # 4. DATOS DEL JSON (estructura principal)
            # Extraer datos principales del JSON
            tipo = json_data.get("tipo", "desconocido")
            impresora = json_data.get("idImpresora", "desconocida")
            numero_impresiones = json_data.get("numeroImpresiones", 1)

            draw.text(
                (self.margin, y),
                "📊 DATOS DE IMPRESIÓN:",
                fill=(100, 100, 100),
                font=self.font_bold
            )
            y += 30

            draw.text(
                (self.margin, y),
                f"• Tipo: {tipo}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += self.line_height

            draw.text(
                (self.margin, y),
                f"• Impresora: {impresora}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += self.line_height

            draw.text(
                (self.margin, y),
                f"• Impresiones: {numero_impresiones}",
                fill=(0, 0, 0),
                font=self.font_normal
            )
            y += 40

            # 5. DATOS ESPECÍFICOS (data field)
            if "data" in json_data and isinstance(json_data["data"], dict):
                data_field = json_data["data"]
                if data_field:
                    draw.text(
                        (self.margin, y),
                        "📋 INFORMACIÓN ESPECÍFICA:",
                        fill=(100, 100, 100),
                        font=self.font_bold
                    )
                    y += 30

                    # Mostrar hasta 5 campos principales
                    items_shown = 0
                    for key, value in data_field.items():
                        if items_shown >= 5:
                            break

                        if isinstance(value, (str, int, float)):
                            display_value = str(value)[:50]
                            draw.text(
                                (self.margin, y),
                                f"• {key}: {display_value}",
                                fill=(0, 0, 0),
                                font=self.font_normal
                            )
                            y += self.line_height
                            items_shown += 1

            y += 20

            # 6. REGISTROS (si existen)
            if "registros" in json_data and isinstance(json_data["registros"], list) and json_data["registros"]:
                registros = json_data["registros"]
                if len(registros) > 0:
                    draw.text(
                        (self.margin, y),
                        f"📝 REGISTROS ({len(registros)} items):",
                        fill=(100, 100, 100),
                        font=self.font_bold
                    )
                    y += 30

                    # Mostrar primeros 3 registros
                    for i, registro in enumerate(registros[:3]):
                        if isinstance(registro, dict):
                            reg_str = str(registro)[:80] + "..." if len(str(registro)) > 80 else str(registro)
                        else:
                            reg_str = str(registro)[:80] + "..." if len(str(registro)) > 80 else str(registro)

                        draw.text(
                            (self.margin, y),
                            f"{i + 1}. {reg_str}",
                            fill=(0, 0, 0),
                            font=self.font_normal
                        )
                        y += self.line_height

                    if len(registros) > 3:
                        draw.text(
                            (self.margin, y),
                            f"... y {len(registros) - 3} más",
                            fill=(150, 150, 150),
                            font=self.font_normal
                        )
                        y += self.line_height

            y += 30

            # 7. PIE DE PÁGINA
            draw.line(
                [(self.margin, y), (self.page_width - self.margin, y)],
                fill=(200, 200, 200),
                width=1
            )
            y += 20

            draw.text(
                (self.page_width // 2, y),
                f"Generado desde JSON de impresión • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                fill=(150, 150, 150),
                font=self.font_normal,
                anchor="mm"
            )

            # 8. GUARDAR IMAGEN
            import io
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG', optimize=True, quality=90)
            img_bytes.seek(0)

            # Guardar localmente para debug
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"json_{doc_type.lower()}_{store_code}_{cfac_id}_{timestamp}.png"
            filepath = self.output_dir / filename
            image.save(filepath, 'PNG', optimize=True, quality=90)

            logger.info(f"✅ Imagen generada desde JSON: {filepath}")

            return img_bytes.getvalue()

        except Exception as e:
            logger.error(f"❌ Error generando imagen desde JSON: {e}", exc_info=True)
            return None

    def get_json_any_method(self, store_code: str, cfac_id: str) -> Optional[Dict]:
        """Obtiene JSON por cualquier método disponible"""
        # Método 1: Canal_Movimiento (más confiable)
        json_data = self.get_json_from_canal_movimiento(store_code, cfac_id)

        if json_data:
            logger.info("✅ JSON obtenido de Canal_Movimiento")
            return json_data

        # Método 2: Stored Procedure (fallback)
        logger.info("🔄 Intentando obtener JSON del Stored Procedure...")
        json_data = self.get_json_from_sp_result(store_code, cfac_id)

        if json_data:
            logger.info("✅ JSON obtenido del Stored Procedure")
            return json_data

        logger.warning("⚠️ No se pudo obtener JSON por ningún método")
        return None


# Instancia global solo para Linux
try:
    if platform.system() == "Linux":
        linux_imager = LinuxJsonImager()
        logger.info("✅ LinuxJsonImager inicializado (solo para Linux)")
    else:
        linux_imager = None
        logger.info("ℹ️ LinuxJsonImager no inicializado (solo funciona en Linux)")
except Exception as e:
    logger.error(f"❌ Error inicializando LinuxJsonImager: {e}")
    linux_imager = None