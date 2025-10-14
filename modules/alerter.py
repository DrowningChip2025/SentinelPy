# modules/alerter.py
import os
import time
import logging
import requests
from collections import defaultdict

class Alerter:
    """
    Responsável por enviar notificações com controle de 'muting' para evitar spam.
    Prioriza credenciais de variáveis de ambiente para maior segurança.
    """
    def __init__(self, config):
        # Prioriza variáveis de ambiente sobre o config.ini
        self.token = os.getenv('SENTINEL_TELEGRAM_TOKEN', config.get('alerter', 'telegram_token', fallback=''))
        self.chat_id = os.getenv('SENTINEL_CHAT_ID', config.get('alerter', 'telegram_chat_id', fallback=''))
        
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        self.mute_duration = config.getint('alerter', 'mute_duration_seconds', fallback=300)
        
        # Dicionário para rastrear o timestamp do último alerta por chave
        self.alert_timestamps = defaultdict(float)

    def send_alert(self, message: str, severity: str = "MEDIUM"):
        """
        Envia um alerta formatado, respeitando o período de 'mute'.
        
        A chave de 'muting' é gerada a partir da severidade e da primeira linha da mensagem.
        """
        alert_key = f"{severity}:{message.splitlines()[0]}"
        current_time = time.time()

        if current_time - self.alert_timestamps[alert_key] < self.mute_duration:
            logging.info(f"Alerta repetido silenciado (muting): {alert_key}")
            return

        self.alert_timestamps[alert_key] = current_time
        
        severity_emojis = {
            "INFO": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "🚨",
            "CRITICAL": "💥"
        }
        emoji = severity_emojis.get(severity, "⚫")

        formatted_message = (
            f"{emoji} *SentinelPy Alert* {emoji}\n\n"
            f"*Severity:* {severity}\n\n"
            f"*Details:*\n{message}"
        )
        
        if not self.token or not self.chat_id or "SEU_TOKEN_AQUI" in self.token:
            logging.warning("Alerta não enviado: Token/Chat ID do Telegram não configurado.")
            print("--- ALERTA (SIMULADO) ---")
            print(formatted_message)
            print("-------------------------")
            return

        try:
            response = requests.post(self.api_url, json={
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }, timeout=10)
            if response.status_code != 200:
                logging.error(f"Falha ao enviar alerta para o Telegram: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logging.error(f"Erro de conexão ao enviar alerta para o Telegram: {e}")