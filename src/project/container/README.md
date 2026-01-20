# IoT Monitoring Container

Das Repository enthält einen containerisierten IoT-Monitoring-Stack bestehend aus:

- **Telegraf** – Datensammlung
- **InfluxDB 2.7** – Datenbank
- **Grafana** – Visualisierung

Der gesamte Stack wird über Docker Compose gestartet. Dabei werden die Dashboards und die Datasource automatisch für die Grafana-Visualisierung bereitgestellt.

## Projektstruktur

```text
/container
├── grafana/
│    ├── dashboards/
│    │    ├── dashboard.yaml
│    │    └── IoT_Enviroment_Monitoring.json
│    └── datasources/
│         └── datasources.yaml
├── telegraf/
│    └── telegraf.conf
├── docker-compose.yaml
└── README.md

## Installation und Start

1. .env.example dient als template die .env, welche für die Umgebungsvariablen verwendet wird.
Zunächst müssen folgende Platzhalter mit den eigenen Werten gefüllt werden:

```text
# InfluxDB Configuration
INFLUXDB_TOKEN=<Your_Superstrong_Token>
INFLUXDB_PASSWORD=<Your_Password>

# Grafana Configuration
GRAFANA_ADMIN_PASSWORD=<Your_Password>

# Telegraf Configuration
TELEGRAF_SERVERS=<Your_Server>
TELEGRAF_CLIENT_ID=<Your_Client_ID>
TELEGRAF_USERNAME=<Your_Username>
TELEGRAF_PASSWORD=<Your_Password>
```

passwort zwischen 8 und 72 zeichen
Anschließen muss das .env.example in .env umbenannt werden.

Danach kann das docker compose gestartet oder gestoppt werden:

```bash
docker compose up -d
docker compose down -v
```