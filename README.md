# Czech Parliamentary Elections 2025 Dashboard

Kompletní řešení pro sledování průběžných výsledků voleb do Poslanecké sněmovny ČR 2025.

## Funkce
- Sběr dat z veřejných XML rozhraní volby.cz v sekundových intervalech
- Agregace do minutových intervalů a ukládání do SQLite
- REST API a WebSocket rozhraní pro živá data
- Responzivní frontend s grafy v Chart.js
- Porovnání regionů, historická osa, export dat

## Struktura projektu
```
volby25/
├── backend/
│   ├── aggregator.py
│   ├── data_collector.py
│   ├── db_models.py
│   └── xml_parser.py
├── webapp/
│   ├── api_routes.py
│   ├── app.py
│   └── websocket.py
├── frontend/
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/app.js
│   └── templates/index.html
├── database/volby.db
├── start_collector.py
├── start_webapp.py
├── start_all.sh
├── config.py
└── requirements.txt
```

## Instalace
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Spuštění
- `python start_collector.py` – spustí sběr dat a agregaci
- `python start_webapp.py` – spustí webovou aplikaci na portu 8000
- `./start_all.sh` – spustí oba procesy naráz

## Poznámky
- Při výpadku volby.cz aplikace pokračuje s posledními dostupnými daty.
- Všechna důležitá chování jsou logována do složky `logs/`.
- WebSocket rozhraní poskytuje aktualizace každých 10 sekund.
