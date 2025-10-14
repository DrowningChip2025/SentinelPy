import subprocess
import logging
import threading
import time
from datetime import datetime, timedelta

class IPBlocker(threading.Thread):
    def __init__(self, config, db_manager, alerter):
        super().__init__()
        self.db_manager = db_manager
        self.alerter = alerter
        self.enabled = config.getboolean('ip_blocker', 'enabled')
        self.block_duration = config.getint('ip_blocker', 'block_duration')
        self.check_interval = 60 
        self.running = True

    def run(self):
        if not self.enabled:
            logging.warning("Módulo IPBlocker está desativado na configuração.")
            return

        logging.info("IPBlocker iniciado. Verificando IPs para desbloquear...")

        self.check_and_unblock()

        while self.running:
            time.sleep(self.check_interval)
            self.check_and_unblock()

    def check_and_unblock(self):
        try:
            expired_ips = self.db_manager.get_expired_blocks()
            for ip in expired_ips:
                self.unblock_ip(ip)
        except Exception as e:
            logging.error(f"Erro ao verificar IPs expirados: {e}")

    def block_ip(self, ip_address):
        if not self.enabled:
            return

        if self.db_manager.is_ip_blocked(ip_address):
            logging.info(f"IP {ip_address} já está bloqueado. Ignorando.")
            return

        try:
            command = ['sudo', 'iptables', '-I', 'INPUT', '1', '-s', ip_address, '-j', 'DROP']
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            unblock_time = datetime.now() + timedelta(seconds=self.block_duration)
            self.db_manager.add_blocked_ip(ip_address, unblock_time)

            details = f"IP bloqueado via iptables. Desbloqueio programado para {unblock_time.strftime('%Y-%m-%d %H:%M:%S')}."
            logging.info(f"IP {ip_address} bloqueado com sucesso. {details}")
            self.db_manager.log_event("IP_BLOCKED", "HIGH", details, ip_address)
            
        except FileNotFoundError:
            logging.error("Comando 'iptables' não encontrado. O bloqueio de IP não funcionará.")
            self.enabled = False 
        except subprocess.CalledProcessError as e:
            logging.error(f"Falha ao bloquear o IP {ip_address} com iptables: {e.stderr}")

    def unblock_ip(self, ip_address):
        try:
            check_command = ['sudo', 'iptables', '-C', 'INPUT', '-s', ip_address, '-j', 'DROP']
            if subprocess.run(check_command, capture_output=True).returncode == 0:
                delete_command = ['sudo', 'iptables', '-D', 'INPUT', '-s', ip_address, '-j', 'DROP']
                subprocess.run(delete_command, check=True, capture_output=True, text=True)
                
                message = f"IP {ip_address} desbloqueado automaticamente."
                logging.info(message)
                self.alerter.send_alert(message, "INFO")
                self.db_manager.log_event("IP_UNBLOCKED", "INFO", "Tempo de bloqueio expirado.", ip_address)
            else:
                logging.warning(f"Tentativa de desbloquear {ip_address}, mas a regra não foi encontrada no iptables.")

        except subprocess.CalledProcessError as e:
            logging.error(f"Falha ao desbloquear o IP {ip_address}: {e.stderr}")
        finally:
            self.db_manager.remove_blocked_ip(ip_address)

    def stop(self):
        self.running = False