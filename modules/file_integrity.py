import time
from collections import defaultdict
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileIntegrityMonitor(FileSystemEventHandler, threading.Thread):
    def __init__(self, config, alerter, db_manager):
        super().__init__()
        self.config = config
        self.alerter = alerter
        self.db_manager = db_manager
        self.watched_dirs = config['file_integrity']['watched_dirs'].split(',')
        self.ransomware_threshold = int(config['file_integrity']['ransomware_threshold'])
        self.file_changes = defaultdict(int)
        self.running = True

    def run(self):
        observer = Observer()
        for path in self.watched_dirs:
            try:
                observer.schedule(self, path, recursive=True)
            except FileNotFoundError:
                self.alerter.send_alert(f"Diretório para monitoramento não encontrado: {path}", "MEDIUM")
        
        observer.start()
        
        try:
            while self.running:
                self.check_ransomware_activity()
                time.sleep(10)
        finally:
            observer.stop()
            observer.join()

    def on_modified(self, event):
        if not event.is_directory:
            self.alerter.send_alert(f"Arquivo crítico modificado: `{event.src_path}`", "MEDIUM")
            self.db_manager.log_event("FILE_MODIFIED", "MEDIUM", f"Arquivo: {event.src_path}", None)
            self.file_changes[int(time.time() / 60)] += 1

    def on_created(self, event):
        self.alerter.send_alert(f"Arquivo criado em diretório crítico: `{event.src_path}`", "MEDIUM")

    def check_ransomware_activity(self):
        current_minute = int(time.time() / 60)
        changes_last_minute = self.file_changes.get(current_minute - 1, 0)
        if self.file_changes[current_minute - 1] > self.ransomware_threshold:
            message = f"Atividade suspeita de Ransomware detectada!\n{self.file_changes[current_minute - 1]} arquivos modificados em 60 segundos."
            self.alerter.send_alert(message, "CRITICAL")
            details = f"{changes_last_minute} arquivos modificados em 60s nos diretórios monitorados."
            self.db_manager.log_event("RANSOMWARE_SUSPECTED", "CRITICAL", details, None)
        
        for minute in list(self.file_changes.keys()):
            if current_minute - minute > 5:
                del self.file_changes[minute]
    
    def stop(self):
        self.running = False