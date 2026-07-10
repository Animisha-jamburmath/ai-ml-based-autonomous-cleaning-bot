import paho.mqtt.client as mqtt
import json
import threading
import time
from config import settings

STATIC_CMD_TOPIC = "solar/static/command"
BOT_CMD_TOPIC    = "solar/bot/command"

_client = mqtt.Client(client_id="fastapi_backend")
_connected = False

def _on_connect(client, userdata, flags, rc):
    global _connected
    if rc == 0:
        _connected = True
        print("[MQTT] Connected to broker")
    else:
        print(f"[MQTT] Connection failed rc={rc}")

def _on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    print("[MQTT] Disconnected — reconnecting...")
    # Auto reconnect in background
    threading.Thread(target=_reconnect, daemon=True).start()

def _reconnect():
    while not _connected:
        try:
            print("[MQTT] Trying to reconnect...")
            _client.reconnect()
            time.sleep(2)
        except Exception as e:
            print(f"[MQTT] Reconnect failed: {e}")
            time.sleep(3)

def start():
    _client.on_connect    = _on_connect
    _client.on_disconnect = _on_disconnect
    try:
        _client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
        threading.Thread(target=_client.loop_forever, daemon=True).start()
        print(f"[MQTT] Connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}...")
    except Exception as e:
        print(f"[MQTT] Could not connect: {e}")

def publish_static_command(payload: dict):
    if _connected:
        _client.publish(STATIC_CMD_TOPIC, json.dumps(payload))
        print(f"[MQTT] → static: {payload}")
    else:
        print("[MQTT] Not connected — retrying connection...")
        threading.Thread(target=_reconnect, daemon=True).start()

def publish_bot_command(payload: dict):
    if _connected:
        _client.publish(BOT_CMD_TOPIC, json.dumps(payload))
        print(f"[MQTT] → bot: {payload}")
    else:
        print("[MQTT] Not connected — retrying connection...")
        threading.Thread(target=_reconnect, daemon=True).start()