# IoT Monitoring Stack – InfluxDB + Telegraf + Grafana

Das Repository enthält einen containerisierten IoT-Monitoring-Stack bestehend aus:

- **Telegraf** – Datensammlung (z. B. via MQTT)
- **InfluxDB 2.x** – Zeitreihen-Datenbank
- **Grafana** – Visualisierung und Dashboards

Der gesamte Stack wird über Docker Compose gestartet und speichert Daten und Dashboards persistent in lokalen Verzeichnissen.

## Projektstruktur

├── docker-compose.yml
├── telegraf.conf
└── data/
     ├── influxdb/
     └── grafana/

## Installation und Start

Im Root-Verzeichnis des Projekts:

```bash
docker compose up -d
Nach dem Start stehen folgende Dienste bereit:

- InfluxDB: http://localhost:8086
- Grafana: http://localhost:3000

Zugangsdaten
InfluxDB

Die Initial-Zugangsdaten kommen aus der docker-compose.yml, z. B.:

Benutzername: ###
Passwort: ###
Organisation: ###
Bucket: iot_monitoring
Token: im Compose-File definiert (DOCKER_INFLUXDB_INIT_ADMIN_TOKEN)

Grafana
Benutzername: ###
Passwort: ###

Persistente Speicherung

Die Docker-Container nutzen lokale Ordner zur dauerhaften Speicherung:

./data/influxdb:/var/lib/influxdb2
./data/grafana:/var/lib/grafana

Dienste stoppen
docker compose down