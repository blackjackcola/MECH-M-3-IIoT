# ===================================================================
# Haupt-Anwendung für das yourmuesli.at IoT Environmental Monitoring
#
# Autor: Christian Vogel, Florian Eder 
# Datum: 02.09.2025
#
# Hardware: Raspberry Pi Pico W
# Sensor: DHT11 (Temperatur & Luftfeuchtigkeit)
# Software: CircuitPython
# ===================================================================

# ----------- Bibliotheken importieren -----------
import time
import board
import digitalio
import wifi
import socketpool
import adafruit_dht
import adafruit_ntp
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import toml
import microcontroller
import rtc
import json
import select

# ===================================================================
# KLASSE: ConfigManager
# ===================================================================


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

# ===================================================================
# KLASSE: NetworkManager
# ===================================================================


class NetworkManager:
    def __init__(self, ssid: str, password: str):
        self.ssid = ssid
        self.password = password
        self.pool = None

    def connect(self) -> bool:
        print("Verbinde mit WLAN:", self.ssid)
        for _ in range(5):
            try:
                wifi.radio.connect(self.ssid, self.password)
                self.pool = socketpool.SocketPool(wifi.radio)
                print("WLAN verbunden, IP:", wifi.radio.ipv4_address)
                return True
            except Exception as e:
                print("Fehler bei WLAN-Verbindung:", e)
                time.sleep(2)
        return False

    def is_connected(self) -> bool:
        return wifi.radio.connected

    def get_ip(self) -> str:
        return str(wifi.radio.ipv4_address)

# ===================================================================
# KLASSE: Sensor
# ===================================================================


class Sensor:
    def __init__(self, pin_number: int):
        self.dht = adafruit_dht.DHT11(getattr(board, f"GP{pin_number}"))

    def read_data(self) -> dict | None:
        try:
            temp = self.dht.temperature
            hum = self.dht.humidity
            if temp is not None and hum is not None:
                return {"temperature": temp, "humidity": hum}
        except Exception:
            pass
        return None

# ===================================================================
# KLASSE: MqttClient
# ===================================================================


class MqttClient:
    def __init__(self, broker, port, username, password, client_id, base_topic, pool):
        self.topic = base_topic or "iiot/test"
        self.client = MQTT.MQTT(
            broker=broker,
            port=port,
            username=username,
            password=password,
            socket_pool=pool,
        )
        self.client_id = client_id

    def connect(self):
        print("Verbinde mit MQTT...")
        self.client.connect()
        print("MQTT verbunden")

    def publish_telemetry(self, data: dict):
        msg = json.dumps(data)
        self.client.publish(self.topic, msg)
        print("Daten gesendet:", msg)

    def loop(self):
        self.client.loop(0.1)

# ===================================================================
# HAUPTPROGRAMM
# ===================================================================


def main():
    # LED Setup
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT

    # Konfiguration laden
    cfg = ConfigManager("settings.toml").load_settings()

    ssid = cfg.get("CIRCUITPY_WIFI_SSID", "")
    password = cfg.get("CIRCUITPY_WIFI_PASSWORD", "")

    broker = cfg.get("MQTT_BROKER", "")
    port = int(cfg.get("MQTT_PORT", 1883))
    username = cfg.get("MQTT_USER", "")
    mqtt_password = cfg.get("MQTT_PASSWORD", "")
    client_id = cfg.get("MQTT_CLIENT_ID", "")
    base_topic = cfg.get("MQTT_BASE_TOPIC", "")

    interval = int(cfg.get("READING_INTERVAL_SECONDS", 30))
    pin = 22    # GPIO Pin für DHT11

    # WLAN verbinden
    net = NetworkManager(ssid, password)
    if not net.connect():
        print("Keine WLAN-Verbindung.")
        return

    # NTP-Zeit synchronisieren
    pool = net.pool
    try:
        ntp = adafruit_ntp.NTP(pool)
        rtc.RTC().datetime = ntp.datetime
        print("Zeit synchronisiert.")
    except Exception as e:
        print("NTP-Fehler:", e)

    # Sensor & MQTT
    sensor = Sensor(pin)
    mqtt = MqttClient(broker, port, username, mqtt_password, client_id, base_topic, pool)
    mqtt.connect()

    print("Starte Hauptschleife...")
    led.value = True
    last = 0

    while True:
        mqtt.loop()
        now = time.monotonic()
        if now - last >= interval:
            last = now
            data = sensor.read_data()
            if data:
                data["timestamp"] = time.time()
                mqtt.publish_telemetry(data)
            else:
                print("Sensorfehler")
                led.value = not led.value
        time.sleep(0.1)


try:
    main()
except Exception as e:
    print("Fehler:", e)
    microcontroller.reset()