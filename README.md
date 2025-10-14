
# SentinelPy

**SentinelPy** é um agente de segurança modular para Linux, desenvolvido em Python, projetado para monitorar, detectar e reagir a ameaças em tempo real.

## Principais Recursos
- **Monitoramento de Logs:** SSH, sudo, auth.log e eventos de sistema.
- **Detecção de Ataques:** DDoS, port scan, brute-force.
- **Proteção Anti-Ransomware:** Verificação de integridade e alterações suspeitas.
- **Bloqueio Automático de IPs:** Integração com iptables/nftables.
- **Alertas Imediatos:** Notificações via Telegram, Slack ou Email.
- **Relatórios Automáticos:** Geração mensal em PDF com estatísticas e gráficos.

Estrutura do Projeto
```

sentinelpy/
├── agent.py                 # Núcleo do agente
├── config.ini               # Configurações do sistema
├── sentinel.service         # Arquivo systemd
│
├── modules/                 # Módulos de segurança
│   ├── alerter.py
│   ├── database.py
│   ├── file_integrity.py
│   ├── ip_blocker.py
│   ├── log_monitor.py
│   ├── network_monitor.py
│   └── reporter.py
│
├── templates/               # Templates de relatórios
│   └── report_template.html
│
├── logs/                    # Logs de operação
├── storage/                 # Banco de dados SQLite
└── reports/                 # Relatórios gerados

````

## Crie config.ini
```bash
[main]
log_file = logs/agent.log
db_file = storage/security_events.db

[alerter]
telegram_token = TOKEN_HERE
telegram_chat_id = ID_CHAT_HERE
mute_duration_seconds = 300

[reporter]
report_interval_hours = 24
output_dir = reports

[ip_blocker]
enabled = true
block_duration = 3600

[log_monitor]
auth_log = /var/log/auth.log
ssh_bruteforce_attempts = 5
ssh_bruteforce_window = 300

[file_integrity]
watched_dirs = /etc,/usr/bin,/var/www
ransomware_threshold = 50

[network_monitor]
ddos_rate_threshold = 20
ddos_rate_window_seconds = 10
port_scan_threshold = 20
port_scan_window_seconds = 60
alert_cooldown_seconds = 1800
````


## Instalação

```bash
git clone https://github.com/<seu-usuario>/SentinelPy.git
cd SentinelPy
pip install -r requirements.txt
sudo systemctl enable sentinel.service
sudo systemctl start sentinel.service
````

## Requisitos

* Python 3.9+
* psutil
* watchdog
* Jinja2
* sqlite3
* requests
* weasyprint

## Relatórios

Relatórios mensais são gerados automaticamente no diretório `reports/`, com resumo de eventos e gráficos.

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.


---

