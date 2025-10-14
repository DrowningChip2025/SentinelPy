import sys
import os
import time
import signal
import configparser
import logging
from typing import List, Type
import threading

from modules.alerter import Alerter
from modules.database import DatabaseManager
from modules.ip_blocker import IPBlocker
from modules.log_monitor import LogMonitor
from modules.file_integrity import FileIntegrityMonitor
from modules.network_monitor import NetworkMonitor
from modules.reporter import Reporter

class Agent:
    """
    O orquestrador principal do SentinelPy.
    Gerencia o ciclo de vida de todos os módulos de monitoramento,
    supervisiona sua execução e garante um desligamento ordenado.
    """
    def __init__(self):
        self.running = True
        self.modules: List[threading.Thread] = []
        
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)

        self.config = self._load_config()
        self._setup_logging()
        self._setup_directories()

    def _load_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if not os.path.exists('config.ini'):
            print("ERRO: Arquivo config.ini não encontrado. Por favor, crie um.")
            sys.exit(1)
        config.read('config.ini')
        return config

    def _setup_logging(self):
        logging.basicConfig(
            filename=self.config['main']['log_file'],
            level=logging.INFO,
            format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
        )
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout)) 

    def _setup_directories(self):
        """Garante que todos os diretórios necessários existam."""
        try:
            os.makedirs(os.path.dirname(self.config['main']['log_file']), exist_ok=True)
            os.makedirs(os.path.dirname(self.config['main']['db_file']), exist_ok=True)
            os.makedirs(self.config['reporter']['output_dir'], exist_ok=True)
            os.makedirs('templates', exist_ok=True)
        except OSError as e:
            logging.critical(f"Falha ao criar diretórios necessários: {e}")
            sys.exit(1)

    def run(self):
        """Inicia todos os módulos e começa o loop de supervisão."""
        logging.info("🚀 Iniciando o agente SentinelPy...")

        alerter = Alerter(self.config)
        db_manager = DatabaseManager(self.config['main']['db_file'])

        module_classes: List[Type[threading.Thread]] = [
            IPBlocker,
            LogMonitor,
            FileIntegrityMonitor,
            NetworkMonitor,
            Reporter
        ]

        ip_blocker_instance = IPBlocker(self.config, db_manager, alerter)

        dependencies = {
            IPBlocker: (self.config, db_manager, alerter),
            LogMonitor: (self.config, alerter, ip_blocker_instance, db_manager),
            FileIntegrityMonitor: (self.config, alerter, db_manager),
            NetworkMonitor: (self.config, alerter, db_manager),
            Reporter: (self.config, db_manager, alerter)
        }

        self.modules.append(ip_blocker_instance)
        for module_cls in module_classes:
            if module_cls != IPBlocker:
                instance = module_cls(*dependencies[module_cls])
                self.modules.append(instance)

        for module in self.modules:
            module.name = module.__class__.__name__
            module.start()
            logging.info(f"Módulo {module.name} iniciado.")

        alerter.send_alert("Agente SentinelPy iniciado com sucesso.", "INFO")

        self._supervisor_loop()

    def _supervisor_loop(self):
        """Monitora a saúde dos módulos e reinicia se necessário."""
        while self.running:
            for module in self.modules:
                if not module.is_alive():
                    logging.critical(f"MÓDULO CRÍTICO CAIU: {module.getName()}!")
                    self.shutdown_handler(signal.SIGABRT, None)
            time.sleep(30) 

    def shutdown_handler(self, signum, frame):
        """Lida com sinais de encerramento (SIGINT, SIGTERM) de forma ordenada."""
        if not self.running:
            return
        
        logging.warning(f"Sinal de desligamento recebido ({signal.Signals(signum).name}). Encerrando módulos...")
        self.running = False

        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()

        for module in self.modules:
            module.join(timeout=10)
            if module.is_alive():
                logging.error(f"Módulo {module.getName()} não encerrou a tempo.")

        logging.info("Agente SentinelPy desligado de forma ordenada. ✅")
        sys.exit(0)


if __name__ == "__main__":
    agent = Agent()
    agent.run()