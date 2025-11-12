# ===================================================================
# Haupt-Anwendung für das yourmuesli.at IoT Environmental Monitoring
# Autor: Christian Vogel, Florian Eder, Anton Maurus
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
import toml
import rtc
import json
import ssl

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
        self.base = (base_topic or "iiot/test").rstrip("/")
        self.topic_telemetry = f"{self.base}/{self.client_id}/Daten"
        self.topic_status    = f"{self.base}/{self.client_id}/status"

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
        self.client.will_set(self.topic_status, "offline", retain=True, qos=1)

        # optionale Callback-Logs
        self.client.on_connect = lambda client, userdata, flags, rc: print("MQTT connected, rc=", rc)
        self.client.on_disconnect = lambda client, userdata, rc: print("MQTT disconnected, rc=", rc)

    def connect(self):
        print("Verbinde mit MQTT…")
        self.client.connect()
        # Online-Flag setzen
        self.client.publish(self.topic_status, "online", retain=True, qos=1)
        print("MQTT verbunden. Status 'online' publiziert.")

    def publish_telemetry(self, payload: dict):
        msg = json.dumps(payload)
        self.client.publish(self.topic_telemetry, msg, qos=1, retain=False)
        print("Daten gesendet →", self.topic_telemetry, msg)

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

    ssid         = cfg.get("CIRCUITPY_WIFI_SSID", "")
    password     = cfg.get("CIRCUITPY_WIFI_PASSWORD", "")
    broker       = cfg.get("MQTT_BROKER", "")
    port         = int(cfg.get("MQTT_PORT", 1883))
    username     = cfg.get("MQTT_USER", "")
    mqtt_pass    = cfg.get("MQTT_PASSWORD", "")
    client_id    = cfg.get("MQTT_CLIENT_ID", "Sensor")
    base_topic   = cfg.get("MQTT_BASE_TOPIC", "iiot/test")
    interval_s   = max(3, int(cfg.get("READING_INTERVAL_SECONDS", 30)))  # DHT11 >=2s

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

    # Sensor & MQTT
    sensor = Sensor(pin)
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

    print("Starte Hauptschleife… (Intervall:", interval_s, "s)")
    led.value = True
    last = 0.0

    while True:
        try:
            mqtt.loop(1)
        except Exception as e:
            print("MQTT loop Fehler:", e)
            # Kurz warten und nochmal verbinden
            time.sleep(2)
            try:
                mqtt.connect()
            except Exception as e2:
                print("MQTT Reconnect fehlgeschlagen:", e2)

        now = time.monotonic()
        if now - last >= interval_s:
            last = now
            data = sensor.read_data()
            if data:
                payload = {
                    #"client_id": client_id,
                    #"ip": net.get_ip(),
                    "temperature": data["temperature"],  # °C
                    "humidity": data["humidity"],        # %rH
                    #"timestamp": iso_utc(),              # ISO-8601 UTC
                    #"sensor": {"type": "DHT11", "pin": f"GP{pin}"},
                }
                try:
                    mqtt.publish_telemetry(payload)
                except Exception as e:
                    print("Publish-Fehler:", e)
            else:
                print("Sensorfehler/ungültige Messung")
                # DHT11 zickt manchmal → LED flippen als Hinweis
                led.value = not led.value

        time.sleep(0.2)

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
