"""
Servicio de impresión con 3 intentos - CON VALIDACIÓN POR CADENA DE IP
Caja1 = .21, Caja2 = .22, Linea = .21
Domi/LineaDomi = .15, .78 o .2 (depende del equipo)
"""

import json
import logging
import asyncio
import requests
from typing import Optional, Dict, Any
import urllib3
import re

from telebot import types
from config.database import db_manager
from utils.logger import get_logger

# Deshabilitar warnings de SSL para desarrollo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


class PrintService3Attempts:
    """Servicio de impresión con 3 intentos - CON VALIDACIÓN POR CADENA"""

    # CONFIGURACIÓN EXACTA SEGÚN TUS PARÁMETROS
    ID_IMPRESORA_TO_OCTET = {
        "caja1": "21",
        "1": "21",
        "caja2": "22",
        "2": "22",
        "linea": "21",
        "domi": ["15", "78", "2"],
        "domicilio": ["15", "78", "2"],
        "lineadomi": ["15", "78", "2"],
        "linea_domi": ["15", "78", "2"],
    }

    def __init__(self, store_code: str):
        self.store_code = store_code
        if store_code and len(store_code) > 1:
            self.store_number = store_code[1:].lstrip('0')
        else:
            self.store_number = "0"

        from core.os_detector import OSDetector
        self.second_octet = OSDetector.get_second_octet(store_code)
        logger.info(f"✅ PrintService: Tienda={store_code}, Cadena={self.second_octet}, Número={self.store_number}")

    def _clean_ip(self, ip_address: str) -> str:
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

    def _validate_ip_by_chain(self, ip: str) -> bool:
        if not ip:
            return False
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        if parts[0] != "10":
            return False
        if not parts[1].isdigit() or int(parts[1]) != self.second_octet:
            return False
        if not parts[2].isdigit() or int(parts[2]) != int(self.store_number):
            return False
        valid_servers = ["20", "21", "22", "15", "78", "2"]
        if parts[3] not in valid_servers:
            return False
        return True

    def _get_ips_by_chain_validation(self, id_impresora: str = None) -> list:
        validated_ips = []
        octets_to_try = []

        if id_impresora:
            id_impresora_lower = str(id_impresora).lower().strip()
            if id_impresora_lower in self.ID_IMPRESORA_TO_OCTET:
                octet_value = self.ID_IMPRESORA_TO_OCTET[id_impresora_lower]
                octets_to_try = octet_value if isinstance(octet_value, list) else [octet_value]
            else:
                for key, value in self.ID_IMPRESORA_TO_OCTET.items():
                    if key in id_impresora_lower:
                        octets_to_try = value if isinstance(value, list) else [value]
                        break

        if not octets_to_try:
            octets_to_try = ["21", "22", "15", "78", "2"]

        for octet in octets_to_try:
            ip = f"10.{self.second_octet}.{self.store_number}.{octet}"
            if self._validate_ip_by_chain(ip):
                validated_ips.append(ip)

        if not validated_ips:
            fallback_ips = [
                f"10.{self.second_octet}.{self.store_number}.21",
                f"10.{self.second_octet}.{self.store_number}.22",
            ]
            for ip in fallback_ips:
                if self._validate_ip_by_chain(ip):
                    validated_ips.append(ip)

        return validated_ips

    def _get_estacion_name(self, id_impresora: str, ip_used: str = None) -> str:
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

    def _add_watermark(self, json_data: dict) -> dict:
        try:
            watermarked = json_data.copy()
            watermarked["marcaAguaFondo"] = "RE-IMPRESIÓN DE DOCUMENTO"
            watermarked["marcaAguaEstilo"] = {
                "texto": "RE-IMPRESIÓN DE DOCUMENTO",
                "tamaño": "grande",
                "color": "gris",
                "opacidad": "0.3",
                "posicion": "centro",
                "rotacion": "45grados"
            }
            if "observaciones" in watermarked:
                watermarked["observaciones"] = f"RE-IMPRESIÓN DE DOCUMENTO\n{watermarked['observaciones']}"
            else:
                watermarked["observaciones"] = "RE-IMPRESIÓN DE DOCUMENTO"
            return watermarked
        except Exception as e:
            logger.error(f"Error agregando marca de agua: {e}")
            return json_data

    async def _send_message_safe(self, bot, chat_id, text, parse_mode="Markdown"):
        if bot and chat_id:
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            except Exception as e:
                logger.warning(f"No se pudo enviar mensaje: {e}")
        else:
            logger.info(f"Mensaje (no enviado por test): {text[:150]}...")

    async def print_document(self, bot, chat_id: int, doc_type: str, document_id: str) -> Dict[str, Any]:
        result = {
            "success": False,
            "message": "",
            "attempts": [],
            "estacion_impresion": "",
            "id_impresora_used": ""
        }

        try:
            valid_doc_types = ["factura", "nota_credito", "comanda"]
            if doc_type not in valid_doc_types:
                result["message"] = f"❌ *Tipo de documento no válido:* {doc_type}"
                await self._send_message_safe(bot, chat_id, result["message"])
                return result

            logger.info(f"Iniciando impresión para {doc_type.upper()} {document_id} en tienda {self.store_code}")

            attempt1 = await self._attempt_1(document_id)
            result["attempts"].append(attempt1)
            if attempt1["success"]:
                result["success"] = True
                result["message"] = attempt1["message"]
                result["estacion_impresion"] = attempt1.get("estacion", "")
                result["id_impresora_used"] = attempt1.get("id_impresora", "")
                await self._send_message_safe(bot, chat_id, attempt1["message"])
                return result

            attempt2 = await self._attempt_2(doc_type, document_id)
            result["attempts"].append(attempt2)
            if attempt2["success"]:
                result["success"] = True
                result["message"] = attempt2["message"]
                result["estacion_impresion"] = attempt2.get("estacion", "")
                result["id_impresora_used"] = attempt2.get("id_impresora", "")
                await self._send_message_safe(bot, chat_id, attempt2["message"])
                return result

            attempt3 = await self._attempt_3(doc_type, document_id)
            result["attempts"].append(attempt3)
            if attempt3["success"]:
                result["success"] = True
                result["message"] = attempt3["message"]
                result["estacion_impresion"] = attempt3.get("estacion", "")
                result["id_impresora_used"] = attempt3.get("id_impresora", "")
                await self._send_message_safe(bot, chat_id, attempt3["message"])
                return result

            result["message"] = f"❌ *Todos los intentos de impresión fallaron para {doc_type.upper()} {document_id}*"
            await self._send_message_safe(bot, chat_id, result["message"])

        except Exception as e:
            logger.error(f"Error en proceso de impresión: {e}", exc_info=True)
            result["message"] = f"❌ *Error crítico en impresión:* `{str(e)[:200]}`"
            await self._send_message_safe(bot, chat_id, result["message"])

        return result

    async def _attempt_1(self, document_id: str) -> Dict[str, Any]:
        connection = None
        cursor = None

        try:
            logger.info(f"[Intento 1] Buscando JSON para {document_id}")

            try:
                connection = db_manager.get_connection(self.store_code)
                if not connection:
                    logger.warning("No se pudo obtener conexión a BD para JSON")
                    return {"success": False, "message": "No hay conexión a BD", "attempt": 1}
            except Exception as e:
                logger.warning(f"Error conectando a BD: {e}")
                return {"success": False, "message": f"Error BD: {str(e)[:50]}", "attempt": 1}

            cursor = connection.cursor()
            query = """
                SELECT TOP 1 
                    Canal_MovimientoVarchar1,
                    imp_impresora,
                    imp_ip_estacion
                FROM Canal_Movimiento 
                WHERE Canal_MovimientoVarchar3 = ?
                ORDER BY imp_fecha DESC
            """
            cursor.execute(query, (document_id,))
            row = cursor.fetchone()

            if not row or not row[0]:
                return {"success": False, "message": "No se encontró JSON", "attempt": 1}

            json_str, impresora_db, ip_estacion = row

            if not json_str or json_str.strip() == "":
                return {"success": False, "message": "JSON vacío", "attempt": 1}

            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                return {"success": False, "message": "JSON inválido", "attempt": 1}

            id_impresora = json_data.get("idImpresora") or impresora_db
            if not id_impresora:
                id_impresora = "linea"

            json_data_con_agua = self._add_watermark(json_data)

            ips_to_try = self._get_ips_by_chain_validation(id_impresora)

            if ip_estacion and ip_estacion != "0.0.0.0":
                ip_estacion = self._clean_ip(ip_estacion)
                if self._validate_ip_by_chain(ip_estacion) and ip_estacion not in ips_to_try:
                    ips_to_try.insert(0, ip_estacion)

            logger.info(f"idImpresora: {id_impresora} → IPs: {ips_to_try}")

            for ip in ips_to_try:
                success = await self._send_print_request(ip, json_data_con_agua)
                if success:
                    estacion = self._get_estacion_name(id_impresora, ip)
                    return {
                        "success": True,
                        "message": (
                            f"✅ *Re-impresión completada exitosamente*\n\n"
                            f"✅ *Re-impresión exitosa (Intento 1)*\n"
                            f"• Documento: {document_id}\n"
                            f"• Estación: *{estacion}*\n"
                            f"• IP: {ip}\n"
                            f"• idImpresora: *{id_impresora}*\n"
                            f"• 📝 *Incluye marca de agua: RE-IMPRESIÓN DE DOCUMENTO*"
                        ),
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
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()
                except:
                    pass

    async def _attempt_2(self, doc_type: str, document_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"[Intento 2] Creando JSON genérico para {document_id}")

            if doc_type == "comanda":
                id_impresora = "linea"
                tipo = "orden"
            else:
                id_impresora = "caja1"
                tipo = doc_type

            json_data = {
                "numeroImpresiones": 1,
                "tipo": tipo,
                "idImpresora": id_impresora,
                "idPlantilla": "default",
                "data": {
                    "documento": document_id,
                    "tienda": self.store_number,
                    "observaciones": "RE-IMPRESIÓN DE DOCUMENTO"
                },
                "marcaAguaFondo": "RE-IMPRESIÓN DE DOCUMENTO"
            }

            ips_to_try = self._get_ips_by_chain_validation(id_impresora)
            logger.info(f"JSON genérico → IPs: {ips_to_try}")

            for ip in ips_to_try:
                success = await self._send_print_request(ip, json_data)
                if success:
                    estacion = self._get_estacion_name(id_impresora, ip)
                    return {
                        "success": True,
                        "message": (
                            f"✅ *Re-impresión completada exitosamente*\n\n"
                            f"✅ *Re-impresión exitosa (Intento 2)*\n"
                            f"• Documento: {document_id}\n"
                            f"• Estación: *{estacion}*\n"
                            f"• IP: {ip}\n"
                            f"• idImpresora: *{id_impresora}*\n"
                            f"• 📝 *Incluye marca de agua: RE-IMPRESIÓN DE DOCUMENTO*"
                        ),
                        "attempt": 2,
                        "estacion": estacion,
                        "id_impresora": id_impresora
                    }

            return {"success": False, "message": "Todas las IPs fallaron", "attempt": 2}

        except Exception as e:
            logger.error(f"Error intento 2: {e}")
            return {"success": False, "message": f"Error: {str(e)[:50]}", "attempt": 2}

    async def _attempt_3(self, doc_type: str, document_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"[Intento 3] Emergencia para {document_id}")

            if doc_type == "comanda":
                id_impresora = "linea"
                tipo = "orden"
            elif "F" in document_id:
                id_impresora = "caja1"
                tipo = "factura"
            elif "N" in document_id:
                id_impresora = "caja1"
                tipo = "nota_credito"
            else:
                id_impresora = "caja1"
                tipo = "documento"

            all_ips = self._get_ips_by_chain_validation(None)

            json_data = {
                "numeroImpresiones": 1,
                "tipo": tipo,
                "idImpresora": id_impresora,
                "idPlantilla": "default",
                "data": {
                    "documento": document_id,
                    "tienda": self.store_number,
                    "observaciones": "RE-IMPRESIÓN DE DOCUMENTO - EMERGENCIA"
                },
                "marcaAguaFondo": "RE-IMPRESIÓN DE DOCUMENTO"
            }

            logger.info(f"Emergencia - IPs: {all_ips}")

            for ip in all_ips:
                success = await self._send_print_request(ip, json_data)
                if success:
                    octet = ip.split('.')[-1]
                    if octet == "21":
                        estacion = "Caja 1/Línea"
                    elif octet == "22":
                        estacion = "Caja 2"
                    elif octet in ["15", "78", "2"]:
                        estacion = f"Domicilio (.{octet})"
                    else:
                        estacion = f"IP .{octet}"

                    return {
                        "success": True,
                        "message": (
                            f"✅ *Re-impresión completada exitosamente*\n\n"
                            f"✅ *Re-impresión exitosa (Intento 3 - Emergencia)*\n"
                            f"• Documento: {document_id}\n"
                            f"• Estación: *{estacion}*\n"
                            f"• IP: {ip}\n"
                            f"• idImpresora deducido: *{id_impresora}*\n"
                            f"• 📝 *Incluye marca de agua: RE-IMPRESIÓN DE DOCUMENTO*"
                        ),
                        "attempt": 3,
                        "estacion": estacion,
                        "id_impresora": id_impresora
                    }

            return {"success": False, "message": "Todas las IPs fallaron", "attempt": 3}

        except Exception as e:
            logger.error(f"Error intento 3: {e}")
            return {"success": False, "message": f"Error: {str(e)[:50]}", "attempt": 3}

    async def _send_print_request(self, ip_address: str, json_data: dict) -> bool:
        try:
            ip_address = self._clean_ip(ip_address)
            url = f"http://{ip_address}:5000/api/ImpresionTickets/Impresion"

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            id_impresora = json_data.get("idImpresora", "N/A")
            logger.info(f"Enviando a {url} (idImpresora: {id_impresora})")

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