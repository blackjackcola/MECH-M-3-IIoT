import os
import time
import pytest

from swagger_client import Configuration, ApiClient
from swagger_client.api.default_api import DefaultApi
from swagger_client.models.config_set_request import ConfigSetRequest


HOST = os.getenv("PICO_HOST", "192.168.1.50")
PORT = int(os.getenv("PICO_PORT", "8080"))
API_KEY = os.getenv("PICO_API_KEY", "")  # leer lassen, wenn ihr keinen API_KEY gesetzt habt

BASE_URL = f"http://{HOST}:{PORT}"


def make_api():
    cfg = Configuration()
    # swagger-codegen python client uses "host" as base url in many templates
    cfg.host = BASE_URL

    client = ApiClient(configuration=cfg)

    # Wenn API-Key genutzt wird: Header setzen
    if API_KEY:
        client.default_headers["x-api-key"] = API_KEY

    return DefaultApi(api_client=client)


def test_root_ok():
    api = make_api()
    resp = api.root_get()  # rootGet -> root_get
    # swagger-codegen liefert hier meist einen String (OK)
    assert str(resp).strip() == "OK"


def test_get_config():
    api = make_api()
    cfg = api.config_get()
    assert cfg.interval >= 3
    assert cfg.timestamp  # string


def test_post_config_set_interval():
    api = make_api()

    # Intervall setzen (persist False, damit settings.toml nicht verändert werden muss)
    req = ConfigSetRequest(interval=7, persist=False)

    try:
        resp = api.config_post(body=req)
    except Exception as e:
        # Falls API_KEY gesetzt ist und fehlt, wirft der Client oft eine ApiException
        pytest.fail(f"config_post failed: {e}")

    assert resp.ok is True
    assert resp.interval == 7

    # Nachprüfen per GET
    cfg = api.config_get()
    assert cfg.interval == 7


def test_post_config_rejects_invalid_interval_type():
    api = make_api()

    # absichtlich falscher Typ (string statt int)
    # swagger-codegen könnte hier schon clientseitig meckern; dann ist das auch ok.
    with pytest.raises(Exception):
        req = ConfigSetRequest(interval="abc", persist=False)  # type: ignore
        api.config_post(body=req)


def test_get_status_has_fields():
    api = make_api()

    # kurz warten, damit last_sensor/last_published eher gefüllt sind
    time.sleep(1)

    st = api.status_get()
    assert st.device_id
    assert st.uptime_s >= 0

    assert st.wifi is not None
    assert st.wifi.connected in (True, False)
    assert st.wifi.ip

    assert st.mqtt is not None
    assert st.mqtt.connected in (True, False)
    assert st.mqtt.port is not None
    assert st.mqtt.base_topic

    assert st.config is not None
    assert st.config.interval_s >= 3

    # last_sensor / last_published können am Anfang None sein
    # swagger-codegen modelliert nullable je nach Converter evtl. als None oder Model
    # daher keine harten asserts auf Inhalte.
