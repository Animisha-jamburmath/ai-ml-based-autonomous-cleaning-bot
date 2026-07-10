#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ── WiFi ──
const char* ssid     = "animishajamburmath";
const char* password = "animisha";

// ── MQTT ──
const char* mqttBroker   = "10.166.252.23";
const int   mqttPort     = 1883;
const char* mqttClientID = "bot_esp32";
const char* mqttSubTopic = "solar/bot/command";
const char* mqttPubTopic = "solar/bot/status";

// ── CHIP 1 — Left + Right wheels ──
const int STBY1 = 25;
const int AIN1  = 27;
const int AIN2  = 26;
const int PWMA  = 14;
const int BIN1  = 33;
const int BIN2  = 32;
const int PWMB  = 12;

// ── CHIP 2 — Pump + Roller ──
const int STBY2  = 13;
const int AIN1_P = 19;
const int AIN2_P = 18;
const int PWMA_P = 5;
const int BIN1_R = 17;
const int BIN2_R = 16;
const int PWMB_R = 4;

// ── PWM ──
const int PWM_FREQ     = 1000;
const int PWM_RES      = 8;
const int WHEEL_SPEED  = 200;
const int PUMP_SPEED   = 180;
const int ROLLER_SPEED = 150;

// ── State ──
String botStatus = "idle";

WiFiClient   espClient;
PubSubClient mqtt(espClient);

// ────────────────────────────────────────────
//  Motor helpers
// ────────────────────────────────────────────
void leftWheel(int dir, int spd) {
  if (dir == 1)       { digitalWrite(AIN1, HIGH); digitalWrite(AIN2, LOW); }
  else if (dir == -1) { digitalWrite(AIN1, LOW);  digitalWrite(AIN2, HIGH); }
  else                { digitalWrite(AIN1, LOW);  digitalWrite(AIN2, LOW); }
  ledcWrite(PWMA, spd);
}

void rightWheel(int dir, int spd) {
  if (dir == 1)       { digitalWrite(BIN1, HIGH); digitalWrite(BIN2, LOW); }
  else if (dir == -1) { digitalWrite(BIN1, LOW);  digitalWrite(BIN2, HIGH); }
  else                { digitalWrite(BIN1, LOW);  digitalWrite(BIN2, LOW); }
  ledcWrite(PWMB, spd);
}

void pumpControl(bool on) {
  if (on) {
    digitalWrite(AIN1_P, HIGH);
    digitalWrite(AIN2_P, LOW);
    ledcWrite(PWMA_P, PUMP_SPEED);
  } else {
    digitalWrite(AIN1_P, LOW);
    digitalWrite(AIN2_P, LOW);
    ledcWrite(PWMA_P, 0);
  }
}

void rollerControl(bool on) {
  if (on) {
    digitalWrite(BIN1_R, HIGH);
    digitalWrite(BIN2_R, LOW);
    ledcWrite(PWMB_R, ROLLER_SPEED);
  } else {
    digitalWrite(BIN1_R, LOW);
    digitalWrite(BIN2_R, LOW);
    ledcWrite(PWMB_R, 0);
  }
}

void stopAll() {
  leftWheel(0, 0);
  rightWheel(0, 0);
  pumpControl(false);
  rollerControl(false);
  digitalWrite(STBY1, LOW);
  digitalWrite(STBY2, LOW);
  botStatus = "idle";
  Serial.println("[BOT] All stopped");
}

void moveForward() {
  digitalWrite(STBY1, HIGH);
  leftWheel(1, WHEEL_SPEED);
  rightWheel(1, WHEEL_SPEED);
  botStatus = "moving_forward";
  Serial.println("[BOT] Moving forward");
}

void moveBackward() {
  digitalWrite(STBY1, HIGH);
  leftWheel(-1, WHEEL_SPEED);
  rightWheel(-1, WHEEL_SPEED);
  botStatus = "moving_backward";
  Serial.println("[BOT] Moving backward");
}

void startCleaning() {
  digitalWrite(STBY1, HIGH);
  digitalWrite(STBY2, HIGH);
  leftWheel(1, WHEEL_SPEED);
  rightWheel(1, WHEEL_SPEED);
  pumpControl(true);
  rollerControl(true);
  botStatus = "cleaning";
  Serial.println("[BOT] Cleaning started — fwd + pump + roller ON");
}

// ────────────────────────────────────────────
//  Publish status
// ────────────────────────────────────────────
void publishStatus() {
  StaticJsonDocument<128> doc;
  doc["device_id"] = "bot_esp32";
  doc["status"]    = botStatus;
  String payload;
  serializeJson(doc, payload);
  mqtt.publish(mqttPubTopic, payload.c_str());
  Serial.println("[MQTT] Status sent: " + payload);
}

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

  String action = cmd["action"].as<String>();

  if      (action == "FORWARD")    moveForward();
  else if (action == "BACKWARD")   moveBackward();
  else if (action == "STOP")       stopAll();
  else if (action == "CLEAN")      startCleaning();
  else if (action == "PUMP_ON")  {
    digitalWrite(STBY2, HIGH);
    pumpControl(true);
    botStatus = "pump_on";
  }
  else if (action == "PUMP_OFF") {
    pumpControl(false);
    botStatus = "idle";
  }
  else if (action == "ROLLER_ON") {
    digitalWrite(STBY2, HIGH);
    rollerControl(true);
    botStatus = "roller_on";
  }
  else if (action == "ROLLER_OFF") {
    rollerControl(false);
    botStatus = "idle";
  }
  else Serial.println("[MQTT] Unknown action: " + action);

  publishStatus();
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
//  SETUP
// ────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(STBY1, OUTPUT); digitalWrite(STBY1, LOW);
  pinMode(AIN1,  OUTPUT); pinMode(AIN2,  OUTPUT);
  pinMode(BIN1,  OUTPUT); pinMode(BIN2,  OUTPUT);

  pinMode(STBY2,  OUTPUT); digitalWrite(STBY2, LOW);
  pinMode(AIN1_P, OUTPUT); pinMode(AIN2_P, OUTPUT);
  pinMode(BIN1_R, OUTPUT); pinMode(BIN2_R, OUTPUT);

  ledcAttach(PWMA,   PWM_FREQ, PWM_RES);
  ledcAttach(PWMB,   PWM_FREQ, PWM_RES);
  ledcAttach(PWMA_P, PWM_FREQ, PWM_RES);
  ledcAttach(PWMB_R, PWM_FREQ, PWM_RES);

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

  Serial.println("[BOT] Ready and waiting for commands...");
}

// ────────────────────────────────────────────
//  LOOP
// ────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();
}