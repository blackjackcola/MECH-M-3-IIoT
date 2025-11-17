# ===================================================================
# Haupt-Anwendung für das yourmuesli.at IoT Environmental Monitoring
# Autor: Christian Vogel, Florian Eder
# Datum: 02.09.2025 (überarbeitet)
# Hardware: Raspberry Pi Pico W
# Sensor: DHT11 (Temperatur & Luftfeuchtigkeit)
# Software: CircuitPython
# ===================================================================

import time
import board
import digitalio
import wifi
import socketpool
import adafruit_dht
import adafruit_ntp
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_httpserver import Server, Request, Response, JSONResponse, GET, POST
import toml
import rtc
import json
import ssl
import re
import select

# ============================== Config ==============================

class ConfigManager:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load_settings(self) -> dict:
        try:
            with open(self.filepath, "r") as f:
                return toml.load(f)
        except Exception as e:
            print("Fehler beim Laden der settings:", e)
            return {}
    
def update_interval_in_file(filepath: str, new_interval: int) -> bool:
    """
    Ersetzt/fuegt READING_INTERVAL_SECONDS in settings.toml.
    Robuste Zeilenersetzung ohne toml.dumps-Abhaengigkeit.
    """
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception:
        content = ""

    pattern = r'(?m)^\s*READING_INTERVAL_SECONDS\s*=\s*\d+\s*$'
    line = f"READING_INTERVAL_SECONDS = {new_interval}"

    if re.search(pattern, content):
        new_content = re.sub(pattern, line, content)
    else:
        sep = "" if content.endswith("\n") or content == "" else "\n"
        new_content = f"{content}{sep}{line}\n"

    try:
        with open(filepath, "w") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print("Persistenz-Fehler:", e)
        return False

# ============================== Network =============================

class NetworkManager:
    def __init__(self, ssid: str, password: str):
        self.ssid = ssid
        self.password = password
        self.pool = None

    def connect(self) -> bool:
        print("Verbinde mit WLAN:", self.ssid)
        for attempt in range(5):
            try:
                wifi.radio.connect(self.ssid, self.password)
                self.pool = socketpool.SocketPool(wifi.radio)
                print("WLAN verbunden, IP:", wifi.radio.ipv4_address)
                return True
            except Exception as e:
                print(f"Fehler bei WLAN-Verbindung (Versuch {attempt+1}/5):", e)
                time.sleep(2)
        return False

    def get_ip(self) -> str:
        try:
            return str(wifi.radio.ipv4_address)
        except Exception:
            return "0.0.0.0"

# ============================== Sensor ==============================

class Sensor:
    def __init__(self, pin_number: int):
        # DHT11 ist langsam; immer >=2s zwischen Messungen einhalten
        self.dht = adafruit_dht.DHT11(getattr(board, f"GP{pin_number}"))

    def read_data(self) -> dict | None:
        try:
            t = self.dht.temperature
            h = self.dht.humidity
            if (t is not None) and (h is not None):
                return {"temperature": float(t), "humidity": float(h)}
        except Exception:
            pass
        return None

# ============================== MQTT ================================

class MqttClient:
    def __init__(self, broker, port, username, password, client_id, base_topic, pool):
        self.client_id = client_id or "pico-w"
        self.device_id = self.client_id  # oder aus cfg lesen und hier übergeben
        self.base = (base_topic or "iiot/test").rstrip("/")

        # neue Topics:
        self.topic_status = f"{self.base}/{self.client_id}/status"
        self.topic_temp   = f"{self.base}/{self.client_id}/temperature"
        self.topic_hum    = f"{self.base}/{self.client_id}/humidity"

        # TLS optional: wenn dein Broker TLS verlangt, setze use_ssl=True und passenden Port (z.B. 8883)
        use_ssl = (port == 8883)
        ssl_ctx = ssl.create_default_context() if use_ssl else None

        self.client = MQTT.MQTT(
            broker=broker,
            port=port,
            username=username or None,
            password=password or None,
            socket_pool=pool,
            ssl_context=ssl_ctx,
            keep_alive=30,  # wichtig für stabile Verbindung
            client_id=self.client_id,
        )

        # Last Will: wenn Verbindung abbricht → offline
        will_payload = json.dumps({
            "device_id": self.device_id,
            "status": "offline",
            "timestamp": iso_utc(),  # Zeitpunkt der Verbindung
        })
        self.client.will_set(self.topic_status, will_payload, retain=True, qos=1)

        # optionale Callback-Logs
        self.client.on_connect = lambda client, userdata, flags, rc: print("MQTT connected, rc=", rc)
        self.client.on_disconnect = lambda client, userdata, rc: print("MQTT disconnected, rc=", rc)

    def connect(self):
        print("Verbinde mit MQTT…")
        self.client.connect()
        online_payload = json.dumps({
            "device_id": self.device_id,
            "status": "online",
            "timestamp": iso_utc(),
        })
        self.client.publish(self.topic_status, online_payload, retain=True, qos=1)
        print("MQTT verbunden. Status 'online' publiziert.")

    def publish_telemetry(self, t: float, h: float):
        ts = iso_utc()
        temp_msg = json.dumps({
            "device_id": self.device_id,
            "unit": "°C",
            "value": f"{t:.1f}",        # als String, wie von dir gewünscht
            "timestamp": ts,
        })
        hum_msg = json.dumps({
            "device_id": self.device_id,
            "unit": "%",
            "value": f"{h:.0f}",        # ganze %, bei Bedarf auf .1f ändern
            "timestamp": ts,
        })
        self.client.publish(self.topic_temp, temp_msg, qos=1, retain=False)
        self.client.publish(self.topic_hum, hum_msg, qos=1, retain=False)
        print("TEMP →", self.topic_temp, temp_msg)
        print("HUM  →", self.topic_hum, hum_msg)

    def loop(self, timeout: float = 0.5):
        # Regelmäßig aufrufen; hält Verbindung und verarbeitet acks
        self.client.loop(timeout)
        

# ============================== MAIN =================================

def iso_utc(ts: float | None = None) -> str:
    if ts is None:
        ts = time.time()
    tm = time.localtime(ts)
    # localtime ist nach NTP-Set UTC, daher "Z"
    return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}T{tm.tm_hour:02d}:{tm.tm_min:02d}:{tm.tm_sec:02d}Z"

def main():
    # LED
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False

    cfg = ConfigManager("settings.toml").load_settings()

    ssid       = cfg.get("CIRCUITPY_WIFI_SSID", "")
    password   = cfg.get("CIRCUITPY_WIFI_PASSWORD", "")
    broker     = cfg.get("MQTT_BROKER", "")
    port       = int(cfg.get("MQTT_PORT", 1883))
    username   = cfg.get("MQTT_USER", "")
    mqtt_pass  = cfg.get("MQTT_PASSWORD", "")
    client_id  = cfg.get("MQTT_CLIENT_ID", "Sensor")
    base_topic = cfg.get("MQTT_BASE_TOPIC", "iiot/test")
    interval_s = max(3, int(cfg.get("READING_INTERVAL_SECONDS", 30)))  # DHT11 >= 3s

    # physikalisch Pin 29 = GPIO22 (= board.GP22)
    pin = 22

    # WLAN
    net = NetworkManager(ssid, password)
    if not net.connect():
        print("Keine WLAN-Verbindung.")
        return

    # NTP
    try:
        ntp = adafruit_ntp.NTP(net.pool, server="pool.ntp.org", tz_offset=0)
        rtc.RTC().datetime = ntp.datetime
        print("Zeit synchronisiert:", iso_utc())
    except Exception as e:
        print("NTP-Fehler:", e)

    # Sensor
    sensor = Sensor(pin)

    mqtt = None  # für finally
    try:
        # MQTT
        mqtt = MqttClient(broker, port, username, mqtt_pass, client_id, base_topic, net.pool)

        # Verbindungsaufbau + einfacher Reconnect-Versuch
        for attempt in range(3):
            try:
                mqtt.connect()
                break
            except Exception as e:
                print(f"MQTT-Verbindungsfehler (Versuch {attempt+1}/3):", e)
                time.sleep(2)
        else:
            print("MQTT konnte nicht verbunden werden.")
            return

        # Commands über MQTT abonnieren (als Alternative zu HTTP)
        def setup_cmd_subscription():
            cmd_topic = f"{mqtt.base}/{mqtt.client_id}/cmd"
            def _on_message(client, topic, message):
                try:
                    msg = json.loads(message)
                    if "interval" in msg:
                        nonlocal interval_s
                        new_i = max(3, int(msg["interval"]))
                        interval_s = new_i
                        state["interval_s"] = new_i
                        if msg.get("persist"):
                            update_interval_in_file("settings.toml", new_i)
                        print("Intervall via MQTT gesetzt auf:", new_i)
                except Exception as e:
                    print("CMD-Fehler:", e)
            mqtt.client.on_message = _on_message
            mqtt.client.subscribe(cmd_topic, qos=1)
            print("Höre auf Commands:", cmd_topic)

        setup_cmd_subscription()

        # --- HTTP-Server mit adafruit_httpserver ---
        api_key = cfg.get("API_KEY", "") or None
        SETTINGS_PATH = "settings.toml"

        # Shared State für Routen
        state = {"interval_s": interval_s}

        server = Server(net.pool, debug=False)
        server.headers = {"Access-Control-Allow-Origin": "*"}

        # Für optionalen Sofort-Tick nach Änderung:
        last = 0.0  # wird in der Loop genutzt

        @server.route("/", GET)
        def root(request: Request):
            return Response(request, "OK", content_type="text/plain")

        @server.route("/config", GET)
        def get_config(request: Request):
            return JSONResponse(request, {
                "interval": state["interval_s"],
                "timestamp": iso_utc(),
            })

        # Einfacher URL-Setter: /config/set?interval=20[&persist=1]
        @server.route("/config/set", GET)
        def set_config_via_query(request: Request):
            nonlocal interval_s, last
            if api_key and request.headers.get("x-api-key") != api_key:
                return JSONResponse(request, {"error": "unauthorized"}, status=401)

            qp = request.query_params or {}
            if "interval" not in qp:
                return JSONResponse(request, {"error": "missing 'interval'"}, status=400)

            try:
                new_interval = max(3, int(qp.get("interval", "0")))  # DHT11 >= 3s
            except Exception:
                return JSONResponse(request, {"error": "invalid 'interval'"}, status=400)

            persist = str(qp.get("persist", "0")).lower() in ("1", "true", "yes", "on")

            interval_s = new_interval
            state["interval_s"] = new_interval

            persisted = False
            if persist:
                persisted = update_interval_in_file(SETTINGS_PATH, new_interval)

            # Sofortigen Tick auslösen (optional, hier aktiv)
            last = 0.0

            return JSONResponse(request, {
                "ok": True,
                "interval": new_interval,
                "persisted": persisted,
                "timestamp": iso_utc(),
            })

        # JSON-Setter: POST /config  { "interval": 20, "persist": true }
        @server.route("/config", POST)
        def set_config(request: Request):
            nonlocal interval_s, last  # wir ändern das laufende Intervall
            if api_key and request.headers.get("x-api-key") != api_key:
                return JSONResponse(request, {"error": "unauthorized"}, status=401)

            try:
                payload = request.json()
            except Exception:
                return JSONResponse(request, {"error": "invalid json"}, status=400)

            if not isinstance(payload, dict) or "interval" not in payload:
                return JSONResponse(request, {"error": "missing 'interval'"}, status=400)

            new_interval = int(payload.get("interval", state["interval_s"]))
            persist = bool(payload.get("persist", False))

            # DHT11 braucht >= 3s
            new_interval = max(3, new_interval)

            interval_s = new_interval
            state["interval_s"] = new_interval

            persisted = False
            if persist:
                persisted = update_interval_in_file(SETTINGS_PATH, new_interval)

            # Sofortigen Tick auslösen (optional, hier aktiv)
            last = 0.0

            return JSONResponse(request, {
                "ok": True,
                "interval": new_interval,
                "persisted": persisted,
                "timestamp": iso_utc(),
            })

        try:
            server.start(str(wifi.radio.ipv4_address), 8080)
            print("REST-API lauscht auf :8080")
        except Exception as e:
            print("HTTP-Server Start fehlgeschlagen:", e)

        print("Starte Hauptschleife… (Intervall:", interval_s, "s)")
        led.value = True

        while True:
            # MQTT am Leben halten (Timeout >= socket_timeout)
            try:
                mqtt.loop(1.0)
            except Exception as e:
                print("MQTT loop Fehler:", e)
                time.sleep(2)
                try:
                    mqtt.connect()
                    setup_cmd_subscription()  # nach Reconnect erneut abonnieren
                except Exception as e2:
                    print("MQTT Reconnect fehlgeschlagen:", e2)

            # HTTP-Server poll (non-blocking)
            try:
                server.poll()
            except Exception:
                pass

            now = time.monotonic()
            if now - last >= interval_s:
                last = now
                data = sensor.read_data()
                if data:
                    try:
                        mqtt.publish_telemetry(data["temperature"], data["humidity"])
                    except Exception as e:
                        print("Publish-Fehler:", e)
                else:
                    print("Sensorfehler/ungültige Messung")
                    led.value = not led.value

            time.sleep(0.1)

    finally:
        # „sauberes“ Offline beim geordneten Beenden
        try:
            if mqtt:
                mqtt.client.publish(mqtt.topic_status, "offline", retain=True, qos=1)
                mqtt.client.disconnect()
        except Exception:
            pass


try:
    main()
except Exception as e:
    print("Fehler:", e)
    try:
        # vor einem geordneten Disconnect explizit offline setzen
        mqtt.client.publish(mqtt.topic_status, "offline", retain=True, qos=1)
        mqtt.client.disconnect()
    except Exception as _:
        pass
