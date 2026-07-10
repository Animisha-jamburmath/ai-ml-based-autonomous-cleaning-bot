# AI-Based Autonomous Solar Panel Cleaning System

An intelligent IoT system that automatically monitors and cleans solar panels using AI, ESP32 microcontrollers, and a mobile app.

---

## What This Project Does

Solar panels lose efficiency due to dust accumulation. This system:
- **Monitors** solar panel voltage, current, power, and energy in real time
- **Checks** air quality (dust levels) every 30 minutes using OpenWeatherMap API
- **Automatically cleans** the panel when dust exceeds the threshold
- **Predicts** when the next cleaning will be needed using Machine Learning
- **Allows manual control** from a mobile app when needed

---

## System Overview
Solar Panel
↓
Static ESP32 (measures V, I, W, Wh)
↓ HTTP every 5 seconds
Python FastAPI Backend
↓ checks OpenWeatherMap API every 30 min
If dust AQI > threshold
↓ MQTT command
Bot ESP32 (cleaning robot)
↓
Motors + Water Pump + Roller Brush
↓
Panel gets cleaned automatically!
↓
Mobile App shows everything live

---

## Hardware Used

| Component | Purpose |
|-----------|---------|
| ESP32 (x2) | Microcontrollers |
| TB6612FNG (x2) | Motor drivers |
| Voltage sensor | Measures panel voltage |
| ACS712 | Measures panel current |
| 600 RPM motors (x2) | Bot wheels |
| 100 RPM motor | Roller brush |
| Water pump motor | Water spray |
| Relay module | Charging control |
| Li-ion battery | Powers the bot |

---

## Software Used

| Software | Purpose |
|----------|---------|
| Arduino IDE | ESP32 firmware |
| Python FastAPI | Backend server |
| PostgreSQL | Database |
| Mosquitto | MQTT broker |
| Scikit-learn | ML models |
| React Native + Expo | Mobile app |
| OpenWeatherMap API | Air quality data |

---

## Project Structure
solar-sunroof/
├── code/                    → Python backend
│   ├── main.py              → Entry point
│   ├── config.py            → Settings
│   ├── database.py          → DB connection
│   ├── requirements.txt     → Python packages
│   ├── .env.example         → Environment template
│   ├── models/
│   │   └── models.py        → Database tables
│   ├── routes/
│   │   └── api.py           → All API endpoints
│   ├── services/
│   │   ├── mqtt_service.py  → MQTT publisher
│   │   ├── dust_service.py  → Air quality + threshold
│   │   └── scheduler.py     → Background tasks
│   └── ml/
│       └── ml_service.py    → ML forecasting
├── SolarSunroof/            → React Native mobile app
│   ├── App.js               → Complete app code
│   ├── app.json             → Expo config
│   └── package.json         → Dependencies
├── botcode/
│   └── botcode.ino          → Bot ESP32 firmware
├── staticcode/
│   └── staticcode.ino       → Static ESP32 firmware
└── README.md

---

## How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Mosquitto MQTT broker
- Arduino IDE
- Expo Go app on Android

---

### Step 1 — Clone the project
```bash
git clone https://github.com/YOUR_USERNAME/solar-sunroof.git
cd solar-sunroof
```

### Step 2 — Setup backend
```bash
cd code
pip install -r requirements.txt
```

Create `.env` file (copy from `.env.example`):
HOST=0.0.0.0
PORT=8000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solar_db
DB_USER=postgres
DB_PASSWORD=your_password
MQTT_BROKER=localhost
MQTT_PORT=1883
GOOGLE_API_KEY=your_openweathermap_key
LATITUDE=12.8698
LONGITUDE=74.8431
DUST_THRESHOLD=150
DUST_CHECK_INTERVAL=30

Create database in pgAdmin:
```sql
CREATE DATABASE solar_db;
```

Run backend:
```bash
python main.py
```

### Step 3 — Setup mobile app
```bash
cd SolarSunroof
npm install
npx expo start --clear
```
Scan QR code with Expo Go on your phone.

### Step 4 — Upload ESP32 firmware
- Open `botcode/botcode.ino` in Arduino IDE
- Change WiFi credentials and server IP
- Upload to bot ESP32

- Open `staticcode/staticcode.ino` in Arduino IDE
- Change WiFi credentials and server IP
- Upload to static ESP32

### Step 5 — Start everything (every time)
```bash
# Admin PowerShell
net start mosquitto

# Terminal 1
cd code
python main.py

# Terminal 2
cd SolarSunroof
npx expo start --clear
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/solar/data | ESP32 sends sensor data |
| GET | /api/solar/latest | Latest solar readings |
| GET | /api/solar/history | 24h history for graphs |
| POST | /api/solar/relay | Relay ON/OFF |
| POST | /api/bot/command | Bot commands |
| GET | /api/dust/latest | Latest AQI reading |
| GET | /api/ai/forecast | Power forecast 6h |
| GET | /api/ai/predict-cleaning | Next cleaning prediction |
| GET | /api/cleaning/history | Cleaning events log |

---

## Bot Commands

```json
{ "action": "FORWARD"    }
{ "action": "BACKWARD"   }
{ "action": "STOP"       }
{ "action": "CLEAN"      }
{ "action": "PUMP_ON"    }
{ "action": "PUMP_OFF"   }
{ "action": "ROLLER_ON"  }
{ "action": "ROLLER_OFF" }
```

---

## When IP Address Changes

Every time you connect to a different network update these:

1. `App.js` → `const BASE_URL = 'http://NEW_IP:8000'`
2. `staticcode.ino` → `serverURL` and `mqttBroker`
3. `botcode.ino` → `mqttBroker`
4. `.env` → `MQTT_BROKER=localhost` (never changes)

---

## Circuit Connections

### Static ESP32
| Sensor | Pin |
|--------|-----|
| Voltage sensor OUT | GPIO 34 |
| Current sensor OUT | GPIO 35 |
| Relay IN | GPIO 26 |

### Bot ESP32
| Component | Pins |
|-----------|------|
| Chip1 STBY | GPIO 25 |
| Left wheel | GPIO 27, 26, 14 |
| Right wheel | GPIO 33, 32, 12 |
| Chip2 STBY | GPIO 13 |
| Water pump | GPIO 19, 18, 5 |
| Roller brush | GPIO 17, 16, 4 |

---

## AI Features

**AI Automation** — Fetches AQI every 30 min, auto-cleans when dust > threshold

**AI Forecasting** — Linear Regression predicts power output for next 6 hours

**AI Prediction** — Analyzes AQI trend to predict next cleaning time

---

## Developed By

Animisha P
6th Semester — Electrical and Electronics Engineering
Research Project — 2026
