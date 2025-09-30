# Volby 2025 Realtime Dashboard

A complete Python project for monitoring and visualising the ongoing results of the Czech parliamentary elections 2025. The solution downloads XML feeds from [volby.cz](https://volby.cz), stores them in SQLite, aggregates the results per minute, and exposes an interactive FastAPI dashboard with real-time updates.

## Project structure

```
volby2025/
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
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── dashboard.js
│   └── templates/
│       └── index.html
├── database/
│   └── volby.db
├── config.py
├── requirements.txt
├── start_all.sh
├── start_collector.py
├── start_webapp.py
└── README.md
```

## Installation

The project uses Python 3.11+ and has been tested on macOS and Linux. Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Initialise the database and start the background collector:

```bash
python start_collector.py
```

In another terminal run the web application:

```bash
python start_webapp.py
```

To run both processes at once use the helper script:

```bash
./start_all.sh
```

Open `http://localhost:8000` in the browser to view the dashboard.

## Features

- Continuous polling of volby.cz XML feeds every second
- Robust XML parsing with validation and logging
- Minute-level aggregation and storage of election snapshots
- Real-time FastAPI dashboard with WebSocket-triggered refresh
- Timeline chart of counted districts and bar chart of party results
- Historical slider and export to JSON/CSV
- Simple prediction and counting speed statistics

## Notes

- All comments in the source code are intentionally written in Czech as required.
- The application keeps working with cached data if the external service is temporarily unavailable.
- The database file is created automatically under `database/volby.db`.
- Set `BATCH_RANGE` in `config.py` to adjust the number of detailed batch files downloaded per cycle.
