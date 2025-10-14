# agent.py
import sys
import os
import time
import signal
import configparser
import logging
from typing import List, Type
import threading

# Importação dos módulos do agente
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
        
        # Configura a captura de sinais UNIX para um desligamento limpo
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)

        # Carrega a configuração e prepara o ambiente
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
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout)) # Log para console também

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

        # 1. Inicializa componentes principais (não são threads)
        alerter = Alerter(self.config)
        db_manager = DatabaseManager(self.config['main']['db_file'])

        # 2. Define a lista de módulos (threads) a serem executados
        module_classes: List[Type[threading.Thread]] = [
            IPBlocker,
            LogMonitor,
            FileIntegrityMonitor,
            NetworkMonitor,
            Reporter
        ]
        
        # 3. Instancia e prepara os módulos com suas dependências
        # O IPBlocker é especial, pois é dependência de outros
        ip_blocker_instance = IPBlocker(self.config, db_manager, alerter)

        # Mapeamento de dependências para cada módulo
        dependencies = {
            IPBlocker: (self.config, db_manager, alerter),
            LogMonitor: (self.config, alerter, ip_blocker_instance, db_manager),
            FileIntegrityMonitor: (self.config, alerter, db_manager),
            NetworkMonitor: (self.config, alerter, db_manager),
            Reporter: (self.config, db_manager, alerter)
        }

        self.modules.append(ip_blocker_instance)
        # Instancia os outros módulos
        for module_cls in module_classes:
            if module_cls != IPBlocker:
                instance = module_cls(*dependencies[module_cls])
                self.modules.append(instance)

        # 4. Inicia todas as threads
        for module in self.modules:
            module.name = module.__class__.__name__
            module.start()
            logging.info(f"Módulo {module.name} iniciado.")

        alerter.send_alert("Agente SentinelPy iniciado com sucesso.", "INFO")

        # 5. Loop de supervisão principal
        self._supervisor_loop()

    def _supervisor_loop(self):
        """Monitora a saúde dos módulos e reinicia se necessário."""
        while self.running:
            for module in self.modules:
                if not module.is_alive():
                    logging.critical(f"MÓDULO CRÍTICO CAIU: {module.getName()}!")
                    # A lógica de reinicialização pode ser complexa e será adicionada no futuro.
                    # Por enquanto, o agente será encerrado para evitar um estado inconsistente.
                    self.shutdown_handler(signal.SIGABRT, None)
            time.sleep(30) # Verifica a saúde a cada 30 segundos

    def shutdown_handler(self, signum, frame):
        """Lida com sinais de encerramento (SIGINT, SIGTERM) de forma ordenada."""
        if not self.running:
            return
        
        logging.warning(f"Sinal de desligamento recebido ({signal.Signals(signum).name}). Encerrando módulos...")
        self.running = False

        # 1. Sinaliza para todas as threads pararem
        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()

        # 2. Aguarda a finalização de cada thread com um timeout
        for module in self.modules:
            module.join(timeout=10)
            if module.is_alive():
                logging.error(f"Módulo {module.getName()} não encerrou a tempo.")

        logging.info("Agente SentinelPy desligado de forma ordenada. ✅")
        sys.exit(0)


if __name__ == "__main__":
    agent = Agent()
    agent.run()