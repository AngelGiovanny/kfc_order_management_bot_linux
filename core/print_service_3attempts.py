"""
Servicio de impresión con 3 intentos - CONFIGURACIÓN EXACTA
Caja1 = .21, Caja2 = .22, Linea = .21
Domi/LineaDomi = .15, .78 o .2 (depende del equipo)
"""

import json
import logging
import asyncio
import requests
from typing import Optional, Dict, Any, Tuple
import urllib3
import re

from telebot import types
from config.database import db_manager
from utils.logger import get_logger

# Deshabilitar warnings de SSL para desarrollo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


class PrintService3Attempts:
    """Servicio de impresión con 3 intentos - CONFIGURACIÓN EXACTA"""

    # CONFIGURACIÓN EXACTA SEGÚN TUS PARÁMETROS
    ID_IMPRESORA_TO_OCTET = {
        # Caja 1 = .21 (igual que línea)
        "caja1": "21",
        "1": "21",

        # Caja 2 = .22
        "caja2": "22",
        "2": "22",

        # Línea = .21 (igual que caja1)
        "linea": "21",

        # Domicilio puede estar en .15, .78 o .2
        "domi": ["15", "78", "2"],  # Lista para probar
        "domicilio": ["15", "78", "2"],

        # LineaDomi también puede estar en .15, .78 o .2
        "lineadomi": ["15", "78", "2"],
        "linea_domi": ["15", "78", "2"],
    }

    def __init__(self, store_code: str):
        self.store_code = store_code
        # Extraer número de tienda quitando la letra inicial y ceros
        if store_code and len(store_code) > 1:
            self.store_number = store_code[1:].lstrip('0')
        else:
            self.store_number = "0"

    def _clean_ip(self, ip_address: str) -> str:
        """Limpia completamente una dirección IP"""
        if not ip_address:
            return ip_address

        parts = ip_address.split('.')
        if len(parts) == 4:
            cleaned_parts = []
            for part in parts:
                if part.isdigit():
                    cleaned_parts.append(str(int(part)))
                else:
                    cleaned_parts.append(part)
            return '.'.join(cleaned_parts)
        return ip_address

    def _get_ips_from_idimpresora(self, id_impresora: str) -> list:
        """
        Obtiene lista de IPs basadas en el idImpresora
        Retorna lista de IPs para probar en orden
        """
        if not id_impresora:
            return [f"10.101.{self.store_number}.21"]  # Default a .21

        # Normalizar
        id_impresora_lower = str(id_impresora).lower().strip()

        # Buscar mapeo exacto
        if id_impresora_lower in self.ID_IMPRESORA_TO_OCTET:
            octets = self.ID_IMPRESORA_TO_OCTET[id_impresora_lower]
            if isinstance(octets, list):
                # Para domi/lineadomi: probar todas las opciones
                return [f"10.101.{self.store_number}.{octet}" for octet in octets]
            else:
                # Para caja1, caja2, linea: IP única
                return [f"10.101.{self.store_number}.{octets}"]

        # Búsqueda parcial
        for key, octets in self.ID_IMPRESORA_TO_OCTET.items():
            if key in id_impresora_lower:
                if isinstance(octets, list):
                    return [f"10.101.{self.store_number}.{octet}" for octet in octets]
                else:
                    return [f"10.101.{self.store_number}.{octets}"]

        # Si no se encuentra, intentar deducir por número
        match = re.search(r'(\d+)', id_impresora_lower)
        if match:
            num = match.group(1)
            if num == "1":
                return [f"10.101.{self.store_number}.21"]  # caja1 = .21
            elif num == "2":
                return [f"10.101.{self.store_number}.22"]  # caja2 = .22

        # Default a .21 (caja1/linea)
        return [f"10.101.{self.store_number}.21"]

    def _get_estacion_name(self, id_impresora: str, ip_used: str = None) -> str:
        """Obtiene nombre de estación para mostrar"""
        if not id_impresora:
            return "Desconocida"

        id_impresora_lower = str(id_impresora).lower()

        if "caja1" in id_impresora_lower or id_impresora == "1":
            return "Caja 1"
        elif "caja2" in id_impresora_lower or id_impresora == "2":
            return "Caja 2"
        elif "linea" in id_impresora_lower:
            return "Línea"
        elif "domi" in id_impresora_lower:
            if ip_used:
                octet = ip_used.split('.')[-1]
                return f"Domicilio (.{octet})"
            return "Domicilio"
        elif "lineadomi" in id_impresora_lower:
            if ip_used:
                octet = ip_used.split('.')[-1]
                return f"Línea Domicilio (.{octet})"
            return "Línea Domicilio"

        return id_impresora

    async def print_document(self, bot, chat_id: int, doc_type: str, document_id: str) -> Dict[str, Any]:
        """Proceso principal de impresión con 3 intentos"""

        result = {
            "success": False,
            "message": "",
            "attempts": [],
            "estacion_impresion": "",
            "id_impresora_used": ""
        }

        try:
            # Validar tipo de documento
            valid_doc_types = ["factura", "nota_credito", "comanda"]
            if doc_type not in valid_doc_types:
                result["message"] = f"❌ *Tipo de documento no válido:* {doc_type}"
                await bot.send_message(
                    chat_id=chat_id,
                    text=result["message"],
                    parse_mode="Markdown"
                )
                return result

            logger.info(f"Iniciando impresión para {doc_type.upper()} {document_id} en tienda {self.store_code}")

            # Intento 1: Usar JSON existente de Canal_Movimiento
            attempt1 = await self._attempt_1_use_json(doc_type, document_id)
            result["attempts"].append(attempt1)

            if attempt1["success"]:
                result["success"] = True
                result["message"] = attempt1["message"]
                result["estacion_impresion"] = attempt1.get("estacion", "")
                result["id_impresora_used"] = attempt1.get("id_impresora", "")
                await bot.send_message(
                    chat_id=chat_id,
                    text=attempt1["message"],
                    parse_mode="Markdown"
                )
                return result

            # Intento 2: Generar nuevo JSON con SP
            attempt2 = await self._attempt_2_use_sp(doc_type, document_id)
            result["attempts"].append(attempt2)

            if attempt2["success"]:
                result["success"] = True
                result["message"] = attempt2["message"]
                result["estacion_impresion"] = attempt2.get("estacion", "")
                result["id_impresora_used"] = attempt2.get("id_impresora", "")
                await bot.send_message(
                    chat_id=chat_id,
                    text=attempt2["message"],
                    parse_mode="Markdown"
                )
                return result

            # Intento 3: Intento de emergencia
            attempt3 = await self._attempt_3_emergency(doc_type, document_id)
            result["attempts"].append(attempt3)

            if attempt3["success"]:
                result["success"] = True
                result["message"] = attempt3["message"]
                result["estacion_impresion"] = attempt3.get("estacion", "")
                result["id_impresora_used"] = attempt3.get("id_impresora", "")
                await bot.send_message(
                    chat_id=chat_id,
                    text=attempt3["message"],
                    parse_mode="Markdown"
                )
                return result

            # Si todos los intentos fallaron
            result["message"] = f"❌ *Todos los intentos de impresión fallaron para {doc_type.upper()} {document_id}*"
            await bot.send_message(
                chat_id=chat_id,
                text=result["message"],
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error en proceso de impresión: {e}", exc_info=True)
            result["message"] = f"❌ *Error crítico en impresión:* `{str(e)[:200]}`"
            await bot.send_message(
                chat_id=chat_id,
                text=result["message"],
                parse_mode="Markdown"
            )

        return result

    async def _attempt_1_use_json(self, doc_type: str, document_id: str) -> Dict[str, Any]:
        """Intento 1: Usar JSON existente de Canal_Movimiento"""
        connection = None
        cursor = None

        try:
            logger.info(f"[Intento 1] Buscando JSON para {document_id}")

            connection = db_manager.get_connection(self.store_code)
            if not connection:
                return {"success": False, "message": "No hay conexión a BD", "attempt": 1}

            cursor = connection.cursor()

            # Buscar JSON en Canal_Movimiento
            query = """
                SELECT TOP 1 Canal_MovimientoVarchar1 
                FROM Canal_Movimiento 
                WHERE Canal_MovimientoVarchar3 = ?
                ORDER BY Fecha DESC
            """

            cursor.execute(query, (document_id,))
            row = cursor.fetchone()

            if not row or not row[0]:
                return {"success": False, "message": "No se encontró JSON", "attempt": 1}

            json_str = row[0]

            if not json_str or json_str.strip() == "":
                return {"success": False, "message": "JSON vacío", "attempt": 1}

            # Parsear JSON
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                return {"success": False, "message": "JSON inválido", "attempt": 1}

            # Obtener idImpresora del JSON
            id_impresora = json_data.get("idImpresora")
            if not id_impresora:
                return {"success": False, "message": "JSON sin idImpresora", "attempt": 1}

            # Obtener IPs basadas en idImpresora
            ips_to_try = self._get_ips_from_idimpresora(id_impresora)
            logger.info(f"idImpresora: {id_impresora} → IPs a probar: {ips_to_try}")

            # Probar cada IP
            for ip in ips_to_try:
                success = await self._send_print_request(ip, json_data)
                if success:
                    estacion = self._get_estacion_name(id_impresora, ip)
                    message = (
                        f"✅ *Re-impresión completada exitosamente*\n\n"
                        f"✅ *Re-impresión exitosa (Intento 1)*\n"
                        f"• Documento: {document_id}\n"
                        f"• Estación: *{estacion}*\n"
                        f"• IP: {ip}\n"
                        f"• idImpresora: *{id_impresora}*"
                    )
                    return {
                        "success": True,
                        "message": message,
                        "attempt": 1,
                        "estacion": estacion,
                        "id_impresora": id_impresora
                    }

            return {"success": False, "message": "Todas las IPs fallaron", "attempt": 1}

        except Exception as e:
            logger.error(f"Error intento 1: {e}")
            return {"success": False, "message": f"Error: {str(e)[:50]}", "attempt": 1}
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    async def _attempt_2_use_sp(self, doc_type: str, document_id: str) -> Dict[str, Any]:
        """Intento 2: Generar JSON con Stored Procedure"""
        connection = None
        cursor = None

        try:
            logger.info(f"[Intento 2] Generando JSON con SP para {document_id}")

            connection = db_manager.get_connection(self.store_code)
            if not connection:
                return {"success": False, "message": "No hay conexión a BD", "attempt": 2}

            cursor = connection.cursor()

            # Ejecutar SP
            sql = f"""
                SET NOCOUNT ON;
                DECLARE @jsonResult NVARCHAR(MAX);
                
                EXEC [facturacion].[IAE_TipoFacturacion] 
                    @pDocumento = N'{document_id}',
                    @pServerAddress = N'10.101.{self.store_number}.21',
                    @pJsonOutput = @jsonResult OUTPUT;
                
                SELECT @jsonResult AS JsonData;
            """

            try:
                cursor.execute(sql)
                result = cursor.fetchone()

                if not result or not result[0]:
                    return {"success": False, "message": "SP no generó JSON", "attempt": 2}

                json_str = result[0]

                # Limpiar JSON
                if json_str.startswith('"') and json_str.endswith('"'):
                    json_str = json_str[1:-1].replace('\\"', '"')

                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError:
                    json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                    json_data = json.loads(json_str)

                # Obtener idImpresora del SP
                id_impresora = json_data.get("idImpresora")
                if not id_impresora:
                    return {"success": False, "message": "SP sin idImpresora", "attempt": 2}

                # Obtener IPs basadas en idImpresora
                ips_to_try = self._get_ips_from_idimpresora(id_impresora)
                logger.info(f"SP idImpresora: {id_impresora} → IPs: {ips_to_try}")

                # Probar cada IP
                for ip in ips_to_try:
                    success = await self._send_print_request(ip, json_data)
                    if success:
                        estacion = self._get_estacion_name(id_impresora, ip)
                        message = (
                            f"✅ *Re-impresión completada exitosamente*\n\n"
                            f"✅ *Re-impresión exitosa (Intento 2 - SP)*\n"
                            f"• Documento: {document_id}\n"
                            f"• Estación: *{estacion}*\n"
                            f"• IP: {ip}\n"
                            f"• idImpresora: *{id_impresora}*"
                        )
                        return {
                            "success": True,
                            "message": message,
                            "attempt": 2,
                            "estacion": estacion,
                            "id_impresora": id_impresora
                        }

                return {"success": False, "message": "Todas las IPs fallaron", "attempt": 2}

            except Exception as sp_error:
                logger.error(f"Error SP: {sp_error}")
                return {"success": False, "message": f"Error SP: {str(sp_error)[:50]}", "attempt": 2}

        except Exception as e:
            logger.error(f"Error intento 2: {e}")
            return {"success": False, "message": f"Error: {str(e)[:50]}", "attempt": 2}
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    async def _attempt_3_emergency(self, doc_type: str, document_id: str) -> Dict[str, Any]:
        """Intento 3: Emergencia - Deducir y probar todas las IPs"""
        try:
            logger.info(f"[Intento 3] Emergencia para {document_id}")

            # Deducir idImpresora basado en tipo
            if doc_type == "comanda":
                id_impresora = "linea"
            elif "F" in document_id or "N" in document_id:
                id_impresora = "caja1"
            else:
                id_impresora = "caja1"

            # Obtener IPs basadas en idImpresora deducido
            ips_to_try = self._get_ips_from_idimpresora(id_impresora)

            # Para emergencia, probar también otras IPs comunes
            all_ips = list(set(ips_to_try + [
                f"10.101.{self.store_number}.21",  # caja1/linea
                f"10.101.{self.store_number}.22",  # caja2
                f"10.101.{self.store_number}.15",  # domi opción 1
                f"10.101.{self.store_number}.78",  # domi opción 2
                f"10.101.{self.store_number}.2",   # domi opción 3
            ]))

            logger.info(f"Emergencia - IPs a probar: {all_ips}")

            # Crear JSON básico
            json_data = {
                "numeroImpresiones": 1,
                "tipo": doc_type,
                "idImpresora": id_impresora,
                "idPlantilla": "",
                "data": {"documento": document_id, "tienda": self.store_number},
                "registros": []
            }

            # Probar todas las IPs
            for ip in all_ips:
                success = await self._send_print_request(ip, json_data)
                if success:
                    # Determinar qué tipo de estación es por la IP
                    octet = ip.split('.')[-1]
                    if octet == "21":
                        estacion = "Caja 1/Línea"
                    elif octet == "22":
                        estacion = "Caja 2"
                    elif octet in ["15", "78", "2"]:
                        estacion = f"Domicilio (.{octet})"
                    else:
                        estacion = f"IP .{octet}"

                    message = (
                        f"✅ *Re-impresión completada exitosamente*\n\n"
                        f"✅ *Re-impresión exitosa (Intento 3 - Emergencia)*\n"
                        f"• Documento: {document_id}\n"
                        f"• Estación: *{estacion}*\n"
                        f"• IP: {ip}\n"
                        f"• idImpresora deducido: *{id_impresora}*"
                    )
                    return {
                        "success": True,
                        "message": message,
                        "attempt": 3,
                        "estacion": estacion,
                        "id_impresora": id_impresora
                    }

            return {"success": False, "message": "Todas las IPs fallaron", "attempt": 3}

        except Exception as e:
            logger.error(f"Error intento 3: {e}")
            return {"success": False, "message": f"Error: {str(e)[:50]}", "attempt": 3}

    async def _send_print_request(self, ip_address: str, json_data: dict) -> bool:
        """Envía solicitud de impresión a la API"""
        try:
            ip_address = self._clean_ip(ip_address)
            url = f"http://{ip_address}:5000/api/ImpresionTickets/Impresion"

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            logger.info(f"Enviando a {url} (idImpresora: {json_data.get('idImpresora', 'N/A')})")

            response = requests.post(
                url,
                json=json_data,
                headers=headers,
                timeout=5,
                verify=False
            )

            if response.status_code == 200:
                logger.info(f"✅ Impresión exitosa en {ip_address}")
                return True
            else:
                logger.warning(f"❌ Error {response.status_code} en {ip_address}")
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout en {ip_address}")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning(f"Conexión rechazada en {ip_address}")
            return False
        except Exception as e:
            logger.error(f"Error en {ip_address}: {e}")
            return False