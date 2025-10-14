# modules/reporter.py
import threading
import time
import logging
from datetime import datetime, timedelta
from collections import Counter
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Nota: WeasyPrint pode exigir a instalação de dependências de sistema.
# Ex: sudo apt-get install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0

class Reporter(threading.Thread):
    """Gera relatórios periódicos em PDF com estatísticas e um resumo executivo."""
    def __init__(self, config, db_manager, alerter):
        super().__init__()
        self.db_manager = db_manager
        self.alerter = alerter
        self.running = True
        self.interval = config.getint('reporter', 'report_interval_hours', fallback=24) * 3600
        self.output_dir = config.get('reporter', 'output_dir', fallback='reports')
        
        try:
            self.env = Environment(loader=FileSystemLoader('templates/'))
            self.template = self.env.get_template('report_template.html')
        except Exception as e:
            logging.critical(f"Falha ao carregar template de relatório: {e}. O módulo Reporter não funcionará.")
            self.running = False # Impede a thread de iniciar se o template não for encontrado

    def run(self):
        if not self.running:
            return
        logging.info(f"Reporter iniciado. Próximo relatório em {self.interval / 3600} horas.")
        time.sleep(self.interval) # Espera o primeiro intervalo antes de gerar o relatório
        while self.running:
            self.generate_report()
            time.sleep(self.interval)

    def generate_report(self):
        logging.info("Gerando relatório de segurança...")
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=self.interval)
            events = self.db_manager.get_events_since(start_time)

            if not events:
                logging.info("Nenhum evento de segurança a ser reportado neste período.")
                return

            # Análise de dados
            total_events = len(events)
            events_by_type = Counter(event[2] for event in events)
            events_by_severity = Counter(event[3] for event in events)
            source_ips = [event[5] for event in events if event[5]]
            top_ips = Counter(source_ips).most_common(10)

            # Geração do resumo em linguagem natural
            summary_text = self._generate_summary_text(
                start_time, end_time, total_events, events_by_type, top_ips
            )

            context = {
                'start_date': start_time.strftime('%d/%m/%Y %H:%M'),
                'end_date': end_time.strftime('%d/%m/%Y %H:%M'),
                'total_events': total_events,
                'events_by_severity': events_by_severity.items(),
                'events_by_type': events_by_type.most_common(),
                'top_ips': top_ips,
                'summary_text': summary_text,
                'recent_events': [dict(zip(['id', 'timestamp', 'type', 'severity', 'details', 'ip'], event)) for event in events[-20:]]
            }

            html_out = self.template.render(context)
            pdf_filename = f"{self.output_dir}/Security_Report_{end_time.strftime('%Y-%m-%d_%H-%M')}.pdf"
            HTML(string=html_out).write_pdf(pdf_filename)

            logging.info(f"Relatório gerado com sucesso: {pdf_filename}")
            self.alerter.send_alert(f"📄 Relatório de segurança gerado com sucesso e salvo em `{self.output_dir}`.", "INFO")

        except Exception as e:
            logging.error(f"Falha crítica ao gerar o relatório: {e}", exc_info=True)
            self.alerter.send_alert(f"Falha crítica ao gerar relatório de segurança: {e}", "CRITICAL")

    def _generate_summary_text(self, start_time, end_time, total_events, events_by_type, top_ips) -> str:
        """Cria um resumo executivo dos eventos do período."""
        most_common_event = events_by_type.most_common(1)[0] if events_by_type else ('Nenhum', 0)
        
        summary = (
            f"No período de {start_time.strftime('%d/%m')} a {end_time.strftime('%d/%m')}, "
            f"o sistema detectou um total de *{total_events} eventos* de segurança. "
            f"A ameaça mais frequente foi *{most_common_event[0].replace('_', ' ')}*, com {most_common_event[1]} ocorrências. "
        )
        if top_ips:
            most_active_ip = top_ips[0]
            summary += (
                f"O endereço de IP mais ativo foi `{most_active_ip[0]}`, responsável por *{most_active_ip[1]} eventos*. "
                "As ações de mitigação, como bloqueios automáticos, foram aplicadas conforme a política configurada."
            )
        else:
            summary += "Não houve atividade de IPs externos que gerasse alertas significativos."

        return summary

    def stop(self):
        self.running = False
        logging.info("Reporter parado.")