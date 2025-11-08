# ===================================================================
# Haupt-Anwendung für das yourmuesli.at IoT Environmental Monitoring
#
# Autor: Christian Vogel, Florian Eder 
# Datum: 02.09.2025
#
# Hardware: Raspberry Pi Pico W
# Sensor: DHT22 (Temperatur & Luftfeuchtigkeit)
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
        self.dht = adafruit_dht.DHT22(getattr(board, f"GP{pin_number}"))

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
    def __init__(self, config: dict, pool):
        mqtt_conf = config["mqtt"]
        self.topic = mqtt_conf.get("topic", "yourmuesli/env")
        self.client = MQTT.MQTT(
            broker=mqtt_conf["broker"],
            port=int(mqtt_conf.get("port", 1883)),
            username=mqtt_conf.get("username", ""),
            password=mqtt_conf.get("password", ""),
            socket_pool=pool,
        )

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
    ssid = cfg["wifi"]["ssid"]
    password = cfg["wifi"]["password"]
    pin = int(cfg["sensor"]["pin"])
    interval = int(cfg["app"]["reading_interval_seconds"])

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
    mqtt = MqttClient(cfg, pool)
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


# Programm starten
try:
    main()
except Exception as e:
    print("Fehler:", e)
    microcontroller.reset()
