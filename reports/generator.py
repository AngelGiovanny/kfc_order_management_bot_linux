import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')  # Para usar en servidor sin GUI

from config.settings import REPORTS_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generador de reportes y gráficos"""

    def __init__(self, store_code: str):
        self.store_code = store_code
        self.report_date = datetime.now()

        # Crear estructura de directorios
        self.report_path = self._create_report_structure()

    def _create_report_structure(self) -> Path:
        """Crea estructura de directorios para reportes"""
        year = self.report_date.year
        month = self.report_date.month
        day = self.report_date.day

        store_path = REPORTS_DIR / self.store_code / str(year) / f"{month:02d}" / f"{day:02d}"
        store_path.mkdir(parents=True, exist_ok=True)

        return store_path

    def generate_daily_report(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera reporte diario con gráficos"""

        report = {
            "store_code": self.store_code,
            "report_date": self.report_date.strftime("%Y-%m-%d"),
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": self._generate_summary(data),
            "charts": self._generate_charts(data),
            "data": data
        }

        # Guardar reporte
        self._save_report(report)

        return report

    def _generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera resumen estadístico"""
        if not data:
            return {}

        total_sales = sum(item.get('total_monto', 0) for item in data)
        total_orders = sum(item.get('total_ventas', 0) for item in data)
        avg_order = total_sales / total_orders if total_orders > 0 else 0

        # Encontrar horas pico
        hourly_data = {}
        for item in data:
            hour = item.get('hora', '00')
            hourly_data[hour] = hourly_data.get(hour, 0) + item.get('total_ventas', 0)

        peak_hour = max(hourly_data.items(), key=lambda x: x[1]) if hourly_data else ('00', 0)

        return {
            "total_ventas": total_sales,
            "total_ordenes": total_orders,
            "promedio_orden": round(avg_order, 2),
            "hora_pico": f"{peak_hour[0]}:00",
            "ordenes_hora_pico": peak_hour[1],
            "venta_maxima": max((item.get('venta_maxima', 0) for item in data), default=0),
            "venta_minima": min((item.get('venta_minima', 0) for item in data), default=0)
        }

    def _generate_charts(self, data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Genera gráficos y retorna rutas de archivos"""
        charts = {}

        try:
            # Gráfico 1: Ventas por hora
            if len(data) > 1:
                hours = [item.get('hora', f"{i:02d}") for i, item in enumerate(data)]
                sales = [item.get('total_monto', 0) for item in data]

                plt.figure(figsize=(10, 6))
                plt.bar(hours, sales, color='skyblue')
                plt.title(f'Ventas por Hora - {self.store_code}')
                plt.xlabel('Hora')
                plt.ylabel('Ventas ($)')
                plt.xticks(rotation=45)
                plt.tight_layout()

                chart1_path = self.report_path / "ventas_hora.png"
                plt.savefig(chart1_path, dpi=100)
                plt.close()

                charts['ventas_hora'] = str(chart1_path)

            # Gráfico 2: Órdenes por hora
            if len(data) > 1:
                orders = [item.get('total_ventas', 0) for item in data]

                plt.figure(figsize=(10, 6))
                plt.plot(hours, orders, marker='o', color='orange', linewidth=2)
                plt.title(f'Órdenes por Hora - {self.store_code}')
                plt.xlabel('Hora')
                plt.ylabel('Número de Órdenes')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()

                chart2_path = self.report_path / "ordenes_hora.png"
                plt.savefig(chart2_path, dpi=100)
                plt.close()

                charts['ordenes_hora'] = str(chart2_path)

            # Gráfico 3: Resumen diario (pie chart)
            summary = self._generate_summary(data)
            if summary:
                labels = ['Ventas Totales', 'Órdenes', 'Promedio']
                sizes = [
                    summary.get('total_ventas', 0),
                    summary.get('total_ordenes', 0),
                    summary.get('promedio_orden', 0) * 10  # Escalado
                ]

                plt.figure(figsize=(8, 8))
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.title(f'Resumen Diario - {self.store_code}')
                plt.tight_layout()

                chart3_path = self.report_path / "resumen_diario.png"
                plt.savefig(chart3_path, dpi=100)
                plt.close()

                charts['resumen_diario'] = str(chart3_path)

        except Exception as e:
            logger.error(f"Error generando gráficos: {e}")

        return charts

    def _save_report(self, report: Dict[str, Any]):
        """Guarda reporte en diferentes formatos"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Guardar como JSON
        json_path = self.report_path / f"report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Guardar como CSV (datos principales)
        csv_path = self.report_path / f"data_{timestamp}.csv"
        if report.get('data'):
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=report['data'][0].keys())
                writer.writeheader()
                writer.writerows(report['data'])

        # Guardar resumen en texto
        txt_path = self.report_path / f"summary_{timestamp}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"REPORTE DIARIO - {self.store_code}\n")
            f.write(f"Fecha: {report['report_date']}\n")
            f.write(f"Generado: {report['generation_time']}\n")
            f.write("\n" + "=" * 50 + "\n")
            f.write("RESUMEN ESTADÍSTICO\n")
            f.write("=" * 50 + "\n")

            summary = report['summary']
            for key, value in summary.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")

    def generate_store_report(self, start_date: str, end_date: str, os_type: str) -> Dict[str, Any]:
        """Genera reporte completo de tienda"""
        from database.queries import QueryManager
        from database.windows_db import WindowsDatabase
        from database.linux_db import LinuxDatabase

        # Obtener datos
        query = QueryManager.get_store_report(self.store_code, start_date, end_date)

        if os_type == "windows":
            db = WindowsDatabase()
        else:
            db = LinuxDatabase()

        data = db.execute_query(self.store_code, query)

        # Generar reporte
        return self.generate_daily_report(data)


class ReportManager:
    """Gestor de reportes del sistema"""

    @staticmethod
    async def send_daily_report(bot, chat_id, store_code: str):
        """Envía reporte diario al chat"""
        from core.os_detector import OSDetector

        os_type, _ = OSDetector.detect_os(store_code)

        # Generar reporte
        generator = ReportGenerator(store_code)

        today = datetime.now().strftime("%Y-%m-%d")
        report = generator.generate_store_report(today, today, os_type)

        # Enviar resumen
        summary_text = f"""
📊 *REPORTE DIARIO - {store_code}*
Fecha: {report['report_date']}

*RESUMEN:*
• Ventas Totales: ${report['summary'].get('total_ventas', 0):,.2f}
• Total Órdenes: {report['summary'].get('total_ordenes', 0)}
• Promedio por Orden: ${report['summary'].get('promedio_orden', 0):,.2f}
• Hora Pico: {report['summary'].get('hora_pico', 'N/A')}
• Órdenes en Hora Pico: {report['summary'].get('ordenes_hora_pico', 0)}

_Reporte generado automáticamente_
        """

        await bot.send_message(
            chat_id=chat_id,
            text=summary_text,
            parse_mode="Markdown"
        )

        # Enviar gráficos si existen
        for chart_name, chart_path in report.get('charts', {}).items():
            if Path(chart_path).exists():
                with open(chart_path, 'rb') as photo:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=f"📈 {chart_name.replace('_', ' ').title()}"
                    )