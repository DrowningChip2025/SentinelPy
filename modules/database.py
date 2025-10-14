import sqlite3
import threading
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SecurityEvent:
    id: int
    timestamp: datetime
    event_type: str
    severity: str
    details: str
    source_ip: str

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=10)
        conn.execute('PRAGMA journal_mode=WAL;')
        return conn


    def init_db(self):
        """Initializes the database by creating tables and indexes if they don't exist."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    details TEXT,
                    source_ip TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocked_ips (
                    ip_address TEXT PRIMARY KEY,
                    unblock_at DATETIME NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_source_ip ON events (source_ip);
            ''')
            
            conn.commit()
            conn.close()

    def log_event(self, event_type, severity, details, source_ip=None):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (timestamp, event_type, severity, details, source_ip)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now(), event_type, severity, details, source_ip))
            conn.commit()
            conn.close()

    def get_events_since(self, start_time) -> list[SecurityEvent]:
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE timestamp >= ?", (start_time,))
            events = cursor.fetchall()
            conn.close()
            rows = cursor.fetchall()
            return [SecurityEvent(*row) for row in rows]


    def add_blocked_ip(self, ip_address, unblock_at):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO blocked_ips (ip_address, unblock_at) VALUES (?, ?)", (ip_address, unblock_at))
            conn.commit()
            conn.close()

    def get_expired_blocks(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ip_address FROM blocked_ips WHERE unblock_at <= ?", (datetime.now(),))
            ips = [row[0] for row in cursor.fetchall()]
            conn.close()
            return ips
            
    def remove_blocked_ip(self, ip_address):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blocked_ips WHERE ip_address = ?", (ip_address,))
            conn.commit()
            conn.close()
    
    def is_ip_blocked(self, ip_address):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM blocked_ips WHERE ip_address = ?", (ip_address,))
            result = cursor.fetchone()
            conn.close()
            return result is not None