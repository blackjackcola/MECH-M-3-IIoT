# yourmuesli.at Pico W Monitor

This repo contains the CircuitPython program that runs on a Raspberry Pi Pico W to read one DHT11 sensor and forward temperature/humidity data to the cloud via MQTT. Everything happens inside `src/project/code.py`. Below is a plain-language tour of the important pieces.

## Configuration Flow
- `ConfigManager` only reads `settings.toml` and returns the entries as a Python dictionary. All credentials (Wi-Fi SSID/password, MQTT broker details, reading interval) are pulled from there, so no secrets live inside the code.

## Networking Flow
- `NetworkManager` handles Wi-Fi. Its `connect()` method tries up to five times to join the configured SSID, remembers the socket pool (`socketpool.SocketPool`) for later networking, and can report the IP address if needed.

## Sensor Flow
- `Sensor` wraps the DHT11 that sits on GPIO 22 (`GP22`). Calling `read_data()` returns a dictionary with `temperature` and `humidity` whenever the sensor responds successfully; otherwise it returns `None`. All sensor error handling is centralized here.

## MQTT Flow
- `MqttClient` stores the base topic (default `iiot/test` when nothing is provided) and the Adafruit MiniMQTT client. After `connect()` is called, `publish_telemetry()` will JSON-encode whatever dictionary it receives (e.g., `{"temperature": 23, "humidity": 52, "timestamp": ...}`) and publish it to the configured topic. `loop()` keeps the MQTT connection alive and should be called frequently.

## Main Loop
1. Set up the onboard LED so it can be toggled as a quick status indicator.
2. Load all settings using `ConfigManager`.
3. Connect to Wi-Fi through `NetworkManager`; stop the program early if Wi-Fi cannot be reached.
4. Sync time using NTP (this is optional but ensures timestamps are meaningful).
5. Create the `Sensor` and `MqttClient` objects with the loaded settings.
6. Call `mqtt.loop()` continuously and, every `READING_INTERVAL_SECONDS` (default 30 s), read the sensor:
   - When data is available, add a `timestamp` using `time.time()` and publish through MQTT.
   - When the sensor read fails, print `Sensorfehler` and toggle the LED so you get a visible warning.

## Error Handling
- The entire `main()` call is wrapped in a `try/except`. On any unhandled exception, the Pico prints the error message and performs a `microcontroller.reset()` so it restarts into a clean state.