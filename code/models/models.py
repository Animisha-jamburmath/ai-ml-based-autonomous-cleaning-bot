from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base

# ── Solar sensor readings from static ESP32 ──
class SolarReading(Base):
    __tablename__ = "solar_readings"

    id         = Column(Integer, primary_key=True, index=True)
    device_id  = Column(String, default="static_esp32")
    voltage    = Column(Float)
    current    = Column(Float)
    power      = Column(Float)
    energy_wh  = Column(Float)
    relay      = Column(Boolean, default=False)
    timestamp  = Column(DateTime, server_default=func.now(), index=True)


# ── Bot status from bot ESP32 ──
class BotStatus(Base):
    __tablename__ = "bot_status"

    id        = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, default="bot_esp32")
    status    = Column(String)   # idle, moving_forward, cleaning, etc.
    timestamp = Column(DateTime, server_default=func.now(), index=True)


# ── Dust / air quality readings from Google API ──
class DustReading(Base):
    __tablename__ = "dust_readings"

    id        = Column(Integer, primary_key=True, index=True)
    aqi       = Column(Integer)
    pm25      = Column(Float)
    pm10      = Column(Float)
    category  = Column(String)   # Good, Moderate, Unhealthy, etc.
    timestamp = Column(DateTime, server_default=func.now(), index=True)


# ── Cleaning events log ──
class CleaningEvent(Base):
    __tablename__ = "cleaning_events"

    id         = Column(Integer, primary_key=True, index=True)
    trigger    = Column(String)   # "auto_dust", "manual", "scheduled"
    aqi_at_trigger = Column(Integer, nullable=True)
    status     = Column(String)   # "started", "completed", "failed"
    notes      = Column(Text, nullable=True)
    timestamp  = Column(DateTime, server_default=func.now(), index=True)


# ── ML predictions storage ──
class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id             = Column(Integer, primary_key=True, index=True)
    prediction_type = Column(String)   # "power_forecast", "next_cleaning"
    predicted_value = Column(Float)
    predicted_at   = Column(DateTime)  # what time this prediction is for
    created_at     = Column(DateTime, server_default=func.now())
    notes          = Column(Text, nullable=True)
