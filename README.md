
# 🛡️ SentinelPy

**SentinelPy** é um agente de segurança modular para Linux, desenvolvido em Python, projetado para monitorar, detectar e reagir a ameaças em tempo real.

## 🚀 Principais Recursos
- **Monitoramento de Logs:** SSH, sudo, auth.log e eventos de sistema.
- **Detecção de Ataques:** DDoS, port scan, brute-force.
- **Proteção Anti-Ransomware:** Verificação de integridade e alterações suspeitas.
- **Bloqueio Automático de IPs:** Integração com iptables/nftables.
- **Alertas Imediatos:** Notificações via Telegram, Slack ou Email.
- **Relatórios Automáticos:** Geração mensal em PDF com estatísticas e gráficos.

## 🧩 Estrutura do Projeto
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

## ⚙️ Instalação

```bash
git clone https://github.com/<seu-usuario>/SentinelPy.git
cd SentinelPy
pip install -r requirements.txt
sudo systemctl enable sentinel.service
sudo systemctl start sentinel.service
````

## 🧠 Requisitos

* Python 3.9+
* psutil
* watchdog
* Jinja2
* sqlite3
* requests
* weasyprint

## 📈 Relatórios

Relatórios mensais são gerados automaticamente no diretório `reports/`, com resumo de eventos e gráficos.

## 📜 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.


---

