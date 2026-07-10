#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>

// ── WiFi ──
const char* ssid     = "animishajamburmath";
const char* password = "animisha";

// ── Backend ──
const char* serverURL = "http://10.166.252.23:8000/api/solar/data";

// ── MQTT ──
const char* mqttBroker   = "10.166.252.23";
const int   mqttPort     = 1883;
const char* mqttClientID = "static_esp32";
const char* mqttSubTopic = "solar/static/command";
const char* mqttPubTopic = "solar/static/status";

// ── Pins ──
const int voltagePin = 33;
const int currentPin = 32;
const int relayPin   = 26;

// ── Calibration ──
const float voltageCalibration = 5.12;
const float currentCalibration = 1.1;

// ── State ──
bool  relayState   = false;
float energyWh     = 0.0;
unsigned long lastTime     = 0;
unsigned long lastSendTime = 0;
const int SEND_INTERVAL    = 5000;

WiFiClient   espClient;
PubSubClient mqtt(espClient);

// ────────────────────────────────────────────
//  MQTT callback
// ────────────────────────────────────────────
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) message += (char)payload[i];
  Serial.println("[MQTT] Received: " + message);

  StaticJsonDocument<128> cmd;
  if (deserializeJson(cmd, message) != DeserializationError::Ok) {
    Serial.println("[MQTT] JSON parse error");
    return;
  }

  if (cmd.containsKey("relay")) {
    relayState = cmd["relay"].as<bool>();
    digitalWrite(relayPin, relayState ? HIGH : LOW);
    Serial.println(relayState ? "Relay: ON  (app command)"
                               : "Relay: OFF (app command)");
  }
}

// ────────────────────────────────────────────
//  MQTT connect
// ────────────────────────────────────────────
void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqtt.connect(mqttClientID)) {
      Serial.println(" connected!");
      mqtt.subscribe(mqttSubTopic);
      Serial.println("Subscribed to: " + String(mqttSubTopic));
    } else {
      Serial.printf(" failed (rc=%d), retrying in 3s\n", mqtt.state());
      delay(3000);
    }
  }
}

// ────────────────────────────────────────────
//  Send data to backend
// ────────────────────────────────────────────
void sendToBackend(float voltage, float current,
                   float power,   float energyWh) {
  HTTPClient http;
  http.begin(serverURL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["device_id"] = "static_esp32";
  doc["voltage"]   = round(voltage  * 100) / 100.0;
  doc["current"]   = round(current  * 100) / 100.0;
  doc["power"]     = round(power    * 100) / 100.0;
  doc["energy_wh"] = round(energyWh * 10000) / 10000.0;
  doc["relay"]     = relayState;

  String jsonBody;
  serializeJson(doc, jsonBody);
  Serial.println("POST → " + jsonBody);

  int responseCode = http.POST(jsonBody);
  if (responseCode > 0) {
    Serial.printf("Server response: %d\n", responseCode);
  } else {
    Serial.printf("POST failed: %s\n",
                  http.errorToString(responseCode).c_str());
  }
  http.end();
}

// ────────────────────────────────────────────
//  SETUP
// ────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW);
  analogReadResolution(12);

  // ── WiFi ──
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected! IP: " + WiFi.localIP().toString());

  // ── MQTT ──
  mqtt.setServer(mqttBroker, mqttPort);
  mqtt.setKeepAlive(60);
  mqtt.setCallback(onMqttMessage);
  connectMQTT();

  lastTime     = millis();
  lastSendTime = millis();
}

// ────────────────────────────────────────────
//  LOOP
// ────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) 
  connectMQTT();
  mqtt.loop();

  // ── Read sensors ──
  int voltageADC = analogRead(voltagePin);
  int currentADC = analogRead(currentPin);

  float adcVoltage = (voltageADC / 4095.0) * 3.3;
  float adcCurrent = (currentADC / 4095.0) * 3.3;

  float voltage = adcVoltage * voltageCalibration;
  float current = adcCurrent * currentCalibration;
  float power   = voltage * current;

  // ── Energy accumulation ──
  unsigned long now  = millis();
  float elapsedHours = (now - lastTime) / 3600000.0;
  energyWh          += power * elapsedHours;
  lastTime           = now;

  Serial.printf("V: %.2fV | I: %.2fA | P: %.2fW | E: %.4fWh | Relay: %s\n",
                voltage, current, power, energyWh,
                relayState ? "ON" : "OFF");

  // ── Send every 5 seconds ──
  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;
    if (WiFi.status() == WL_CONNECTED) {
      sendToBackend(voltage, current, power, energyWh);
    } else {
      Serial.println("WiFi lost! Reconnecting...");
      WiFi.reconnect();
    }
  }
}