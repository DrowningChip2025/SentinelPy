from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, agent_instance):
        self.agent = agent_instance

    def on_modified(self, event):
        if event.src_path.endswith('config.ini'):
            logging.info("Arquivo config.ini modificado. Recarregando configuração...")
            self.agent.reload_config()
