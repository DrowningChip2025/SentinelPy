import threading
import psutil
import time
import logging
from collections import defaultdict, deque, Counter

class NetworkMonitor(threading.Thread):
    """Monitora a atividade de rede para detectar DDoS e Port Scans."""
    def __init__(self, config, alerter, db_manager):
        super().__init__()
        self.alerter = alerter
        self.db_manager = db_manager
        self.running = True

        self.ddos_rate_threshold = config.getint('network_monitor', 'ddos_rate_threshold', fallback=20)
        self.ddos_window = config.getint('network_monitor', 'ddos_rate_window_seconds', fallback=10)
        self.connections_history = defaultdict(lambda: deque())

        self.scan_threshold = config.getint('network_monitor', 'port_scan_threshold', fallback=20)
        self.scan_window = config.getint('network_monitor', 'port_scan_window_seconds', fallback=60)
        self.connection_attempts = defaultdict(list)

        self.alert_cooldown = config.getint('network_monitor', 'alert_cooldown_seconds', fallback=3600)
        self.alerted_ips = defaultdict(float)

    def run(self):
        logging.info("Monitor de Rede iniciado.")
        while self.running:
            try:
                self.detect_ddos_by_rate()
                self.detect_port_scan()
            except Exception as e:
                logging.error(f"Erro inesperado no NetworkMonitor: {e}", exc_info=True)
            time.sleep(5) 

    def detect_ddos_by_rate(self):
        """Detecta DDoS analisando a taxa de novas conexões em uma janela deslizante."""
        current_time = time.time()
        
        try:
            connections = psutil.net_connections(kind='inet')
            established_ips = [conn.raddr.ip for conn in connections if conn.status == 'ESTABLISHED' and conn.raddr]
        except psutil.AccessDenied:
            logging.warning("Acesso negado ao ler conexões de rede. Execute como root.")
            return

        for ip, count in Counter(established_ips).items():
            self.connections_history[ip].append((current_time, count))
        
        for ip, history in list(self.connections_history.items()):
            while history and current_time - history[0][0] > self.ddos_window:
                history.popleft()

            if not history:
                del self.connections_history[ip]
                continue
            
            total_conns_in_window = sum(count for ts, count in history)
            conn_rate = total_conns_in_window / self.ddos_window

            if conn_rate > self.ddos_rate_threshold:
                if current_time - self.alerted_ips[f"ddos-{ip}"] > self.alert_cooldown:
                    message = (f"💥 Potencial ataque DDoS (por taxa) detectado!\n"
                               f"IP: `{ip}`\n"
                               f"Taxa: {conn_rate:.2f} conexões/seg (Limite: {self.ddos_rate_threshold})")
                    self.alerter.send_alert(message, "CRITICAL")
                    self.db_manager.log_event("DDoS_RATE_DETECTED", "CRITICAL", f"{conn_rate:.2f} conn/s", ip)
                    self.alerted_ips[f"ddos-{ip}"] = current_time

    def detect_port_scan(self):
        """Detecta Port Scan monitorando tentativas de conexão a múltiplas portas."""
        current_time = time.time()
        
        try:
            connections = psutil.net_connections(kind='inet')
        except psutil.AccessDenied:
            return

        for conn in connections:
            if conn.raddr and (conn.status == 'SYN_SENT' or conn.status == 'ESTABLISHED'):
                self.connection_attempts[conn.raddr.ip].append((current_time, conn.raddr.port))

        for ip, attempts in list(self.connection_attempts.items()):
            recent_attempts = [(ts, port) for ts, port in attempts if current_time - ts < self.scan_window]
            self.connection_attempts[ip] = recent_attempts

            if not recent_attempts:
                del self.connection_attempts[ip]
                continue
            
            unique_ports = len(set(port for ts, port in recent_attempts))
            if unique_ports > self.scan_threshold:
                if current_time - self.alerted_ips[f"scan-{ip}"] > self.alert_cooldown:
                    message = (f"🚨 Port Scan detectado!\n"
                               f"IP: `{ip}`\n"
                               f"Portas únicas: {unique_ports} em {self.scan_window}s (Limite: {self.scan_threshold})")
                    self.alerter.send_alert(message, "HIGH")
                    self.db_manager.log_event("PORT_SCAN_DETECTED", "HIGH", f"{unique_ports} portas distintas.", ip)
                    self.alerted_ips[f"scan-{ip}"] = current_time

    def stop(self):
        self.running = False
        logging.info("Monitor de Rede parado.")