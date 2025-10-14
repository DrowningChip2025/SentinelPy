import time
import re
from collections import defaultdict
import threading

class LogMonitor(threading.Thread):
    def __init__(self, config, alerter, ip_blocker, db_manager):
        super().__init__()
        self.config = config
        self.alerter = alerter
        self.ip_blocker = ip_blocker
        self.db_manager = db_manager
        self.auth_log_path = config['log_monitor']['auth_log']
        self.failed_attempts = defaultdict(list)
        self.max_attempts = int(config['log_monitor']['ssh_bruteforce_attempts'])
        self.window = int(config['log_monitor']['ssh_bruteforce_window'])
        self.running = True

    def run(self):
        try:
            with open(self.auth_log_path, 'r') as f:
                f.seek(0, 2)
                while self.running:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    self.parse_line(line)
        except FileNotFoundError:
            self.alerter.send_alert(f"Arquivo de log não encontrado: {self.auth_log_path}", "CRITICAL")
        except Exception as e:
            self.alerter.send_alert(f"Erro no monitor de logs: {e}", "CRITICAL")

    def parse_line(self, line):
        match = re.search(r'Failed password for(?: invalid user)? (\S+) from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
        if match:
            user, ip_address = match.groups()
            self.detect_brute_force(ip_address)

    def detect_brute_force(self, ip_address):
        current_time = time.time()
        self.failed_attempts[ip_address].append(current_time)
        
        self.failed_attempts[ip_address] = [t for t in self.failed_attempts[ip_address] if current_time - t < self.window]
        
        if len(self.failed_attempts[ip_address]) >= self.max_attempts:
            message = f"Ataque de Brute-Force SSH detectado!\nIP: `{ip_address}`\nTentativas: {len(self.failed_attempts[ip_address])} em {self.window}s."
            self.alerter.send_alert(message, "CRITICAL")
            
            details = f"{len(self.failed_attempts[ip_address])} tentativas em {self.window}s."
            self.db_manager.log_event("SSH_BRUTEFORCE", "CRITICAL", details, ip_address)

            if self.ip_blocker.is_enabled():
                self.ip_blocker.block_ip(ip_address)
                self.alerter.send_alert(f"IP `{ip_address}` bloqueado automaticamente.", "HIGH")

            self.failed_attempts[ip_address] = []

    def stop(self):
        self.running = False