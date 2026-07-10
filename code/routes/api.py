from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db
from models.models import SolarReading, BotStatus, DustReading, CleaningEvent
from services import mqtt_service, dust_service
from ml import ml_service

router = APIRouter()

# ─────────────────────────────────────────────
#  Pydantic schemas (request bodies)
# ─────────────────────────────────────────────

class SolarData(BaseModel):
    device_id : str
    voltage   : float
    current   : float
    power     : float
    energy_wh : float
    relay     : bool

class BotStatusIn(BaseModel):
    device_id: str
    status   : str

class RelayCommand(BaseModel):
    relay: bool

class BotCommand(BaseModel):
    action: str

class DustThreshold(BaseModel):
    threshold: int

# ─────────────────────────────────────────────
#  SOLAR — Static ESP32
# ─────────────────────────────────────────────

@router.post("/solar/data")
def receive_solar_data(data: SolarData, db: Session = Depends(get_db)):
    reading = SolarReading(
        device_id = data.device_id,
        voltage   = data.voltage,
        current   = data.current,
        power     = data.power,
        energy_wh = data.energy_wh,
        relay     = data.relay
    )
    db.add(reading)
    db.commit()
    print(f"[DATA] V={data.voltage}V I={data.current}A P={data.power}W E={data.energy_wh}Wh")
    return {"status": "ok", "id": reading.id}


@router.get("/solar/latest")
def get_latest_solar(db: Session = Depends(get_db)):
    r = db.query(SolarReading).order_by(desc(SolarReading.timestamp)).first()
    if not r:
        return {"message": "No data yet"}
    return {
        "voltage"  : r.voltage,
        "current"  : r.current,
        "power"    : r.power,
        "energy_wh": r.energy_wh,
        "relay"    : r.relay,
        "timestamp": r.timestamp
    }


@router.get("/solar/history")
def get_solar_history(hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(hours=hours)
    readings = (
        db.query(SolarReading)
        .filter(SolarReading.timestamp >= since)
        .order_by(SolarReading.timestamp)
        .all()
    )
    return {
        "count": len(readings),
        "hours": hours,
        "readings": [{
            "timestamp": r.timestamp,
            "voltage"  : r.voltage,
            "current"  : r.current,
            "power"    : r.power,
            "energy_wh": r.energy_wh
        } for r in readings]
    }


@router.post("/solar/relay")
def control_relay(cmd: RelayCommand):
    mqtt_service.publish_static_command({"relay": cmd.relay})
    return {
        "status" : "ok",
        "relay"  : cmd.relay,
        "message": f"Relay {'ON' if cmd.relay else 'OFF'} command sent"
    }


# ─────────────────────────────────────────────
#  BOT — Bot ESP32
# ─────────────────────────────────────────────

VALID_ACTIONS = [
    "FORWARD", "BACKWARD", "STOP",
    "CLEAN", "PUMP_ON", "PUMP_OFF",
    "ROLLER_ON", "ROLLER_OFF"
]

@router.post("/bot/command")
def send_bot_command(cmd: BotCommand, db: Session = Depends(get_db)):
    if cmd.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400,
                            detail=f"Invalid action. Valid: {VALID_ACTIONS}")

    mqtt_service.publish_bot_command({"action": cmd.action})

    # Log if it's a cleaning command
    if cmd.action == "CLEAN":
        event = CleaningEvent(
            trigger = "manual",
            status  = "started",
            notes   = "Manual clean triggered from app"
        )
        db.add(event)
        db.commit()

    return {"status": "ok", "action": cmd.action}


@router.post("/bot/status")
def receive_bot_status(data: BotStatusIn, db: Session = Depends(get_db)):
    status = BotStatus(device_id=data.device_id, status=data.status)
    db.add(status)
    db.commit()
    return {"status": "ok"}


@router.get("/bot/status/latest")
def get_bot_status(db: Session = Depends(get_db)):
    s = db.query(BotStatus).order_by(desc(BotStatus.timestamp)).first()
    if not s:
        return {"status": "unknown"}
    return {"status": s.status, "timestamp": s.timestamp}


@router.get("/bot/history")
def get_bot_history(hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(hours=hours)
    logs  = (
        db.query(BotStatus)
        .filter(BotStatus.timestamp >= since)
        .order_by(BotStatus.timestamp)
        .all()
    )
    return {"count": len(logs),
            "logs": [{"status": l.status, "timestamp": l.timestamp} for l in logs]}


# ─────────────────────────────────────────────
#  DUST — Google Air Quality
# ─────────────────────────────────────────────

@router.get("/dust/fetch")
async def trigger_dust_fetch(db: Session = Depends(get_db)):
    """Manually trigger a dust data fetch from Google API"""
    result = await dust_service.fetch_dust_data(db)
    return result


@router.get("/dust/latest")
def get_latest_dust(db: Session = Depends(get_db)):
    d = db.query(DustReading).order_by(desc(DustReading.timestamp)).first()
    if not d:
        return {"message": "No dust data yet"}
    return {
        "aqi"      : d.aqi,
        "pm25"     : d.pm25,
        "pm10"     : d.pm10,
        "category" : d.category,
        "timestamp": d.timestamp
    }


@router.get("/dust/history")
def get_dust_history(hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(hours=hours)
    readings = (
        db.query(DustReading)
        .filter(DustReading.timestamp >= since)
        .order_by(DustReading.timestamp)
        .all()
    )
    return {
        "count": len(readings),
        "readings": [{
            "aqi"      : r.aqi,
            "pm25"     : r.pm25,
            "pm10"     : r.pm10,
            "category" : r.category,
            "timestamp": r.timestamp
        } for r in readings]
    }


@router.post("/dust/threshold")
def update_threshold(body: DustThreshold):
    from config import settings
    settings.DUST_THRESHOLD = body.threshold
    return {"status": "ok", "new_threshold": body.threshold}


# ─────────────────────────────────────────────
#  CLEANING EVENTS
# ─────────────────────────────────────────────

@router.get("/cleaning/history")
def get_cleaning_history(db: Session = Depends(get_db)):
    events = (
        db.query(CleaningEvent)
        .order_by(desc(CleaningEvent.timestamp))
        .limit(50)
        .all()
    )
    return {
        "count": len(events),
        "events": [{
            "trigger"        : e.trigger,
            "aqi_at_trigger" : e.aqi_at_trigger,
            "status"         : e.status,
            "notes"          : e.notes,
            "timestamp"      : e.timestamp
        } for e in events]
    }


# ─────────────────────────────────────────────
#  ML / AI
# ─────────────────────────────────────────────

@router.get("/ai/forecast")
def power_forecast(db: Session = Depends(get_db)):
    return ml_service.forecast_power(db)


@router.get("/ai/predict-cleaning")
def predict_cleaning(db: Session = Depends(get_db)):
    return ml_service.predict_next_cleaning(db)


@router.get("/ai/summary")
def ai_summary(db: Session = Depends(get_db)):
    return ml_service.get_ai_summary(db)
