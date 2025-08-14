# PPE Local – Sistema de Detecção de EPI via Imagens Estáticas do DVR/NVR

Sistema **local** com acesso via navegador para monitoramento de **Equipamentos de Proteção Individual (EPI)**, analisando **imagens estáticas** capturadas diretamente do DVR/NVR via **ISAPI `/ISAPI/Streaming/channels/{channel}/picture`** e utilizando um modelo YOLOv8 treinado para detectar **pessoa**, **capacete** e **máscara**.

## Funcionalidades

- **Acesso Web Multiusuário** (FastAPI + HTML/CSS/JS com HTMX)
- **Análise de imagens estáticas** de até **32 câmeras simultâneas**
- **Modelo YOLOv8** (`model/ppe.pt`) para detecção de pessoa/capacete/máscara
- Associação **pessoa ↔ capacete/máscara** via IoU
- **Eventos automáticos** quando detectado:
  - Pessoa sem capacete (`no_helmet`)
  - Pessoa sem máscara (`no_mask`)
  - Pessoa sem capacete e sem máscara (`no_helmet_no_mask`)
- **Debounce/Dedupe** por câmera para evitar alertas duplicados
- **Hot-reload** de configurações de câmeras sem reiniciar servidor
- **RBAC** (admin, supervisor, operador, auditor)
- **Retenção automática** de eventos e imagens (limpeza por dias configurados)
- **Relatórios** com filtros e exportação CSV
- **Métricas Prometheus**: FPS por câmera, latências, eventos/min, uso CPU/RAM
- **Logs de auditoria**: quem alterou o quê e quando
- Interface responsiva e em português

## Estrutura do Projeto

ppe-local/
├─ README.md
├─ requirements.txt
├─ .env
├─ .gitignore
├─ model/
│ └─ ppe.pt
├─ data/
│ ├─ app.db
│ ├─ images/
│ └─ thumbs/
└─ app/
├─ main.py
├─ auth.py
├─ deps.py
├─ models.py
├─ schemas.py
├─ templates/
│ └─ base.html
├─ static/
│ ├─ app.js
│ └─ styles.css
├─ services/
│ ├─ yolo.py
│ ├─ ppe_rules.py
│ ├─ metrics.py
│ └─ utils.py
├─ workers/
│ ├─ picture_worker.py
│ └─ manager.py
└─ routers/
├─ cameras.py
├─ events.py
├─ reports.py
├─ users.py
├─ metrics.py
└─ logs.py


## Requisitos

- Python 3.10+
- Pacotes listados em `requirements.txt`
- DVR/NVR Hikvision (ou compatível ISAPI) com acesso HTTP/HTTPS
- Modelo YOLOv8 treinado para PPE (`model/ppe.pt`)

## Instalação

```bash
git clone https://github.com/jeckemark/ppe-local.git ppe-local
cd ppe-local

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate  # Windows

pip install -r requirements.txt

Configure o arquivo .env com:
JWT_SECRET=chave_secreta
JWT_EXPIRES_MIN=480
DB_URL=sqlite:///./data/app.db
RETENTION_DAYS=15
MODEL_PATH=./model/ppe.pt

Uso
uvicorn app.main:app --host 0.0.0.0 --port 8000

Acesse no navegador:
http://localhost:8000

Usuário inicial:
E-mail: admin@example.com
Senha: admin123 (altere após login)

Licença
MIT License
