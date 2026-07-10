import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from models.models import SolarReading, DustReading, MLPrediction

# ─────────────────────────────────────────────
#  1. Power forecast — predict next 6 hours
# ─────────────────────────────────────────────
def forecast_power(db: Session) -> dict:
    """
    Uses last 100 solar readings to forecast
    power output for the next 6 hours.
    """
    readings = (
        db.query(SolarReading)
        .order_by(desc(SolarReading.timestamp))
        .limit(100)
        .all()
    )

    if len(readings) < 10:
        return {"error": "Not enough data yet — need at least 10 readings"}

    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "power"    : r.power
    } for r in readings])

    df = df.sort_values("timestamp")
    df["hour"]    = df["timestamp"].dt.hour
    df["minute"]  = df["timestamp"].dt.minute
    df["time_num"] = df["hour"] * 60 + df["minute"]

    X = df[["time_num"]].values
    y = df["power"].values

    model = LinearRegression()
    model.fit(X, y)

    # Predict for next 6 hours (every 30 min)
    now        = datetime.now()
    forecasts  = []
    predictions_to_save = []

    for i in range(1, 13):   # 12 steps × 30 min = 6 hours
        future_time = now + timedelta(minutes=30 * i)
        time_num    = future_time.hour * 60 + future_time.minute
        pred_power  = max(0, float(model.predict([[time_num]])[0]))

        forecasts.append({
            "time"         : future_time.strftime("%H:%M"),
            "predicted_power_w": round(pred_power, 2)
        })

        predictions_to_save.append(MLPrediction(
            prediction_type = "power_forecast",
            predicted_value = pred_power,
            predicted_at    = future_time,
            notes           = f"Linear regression on {len(readings)} readings"
        ))

    # Save predictions to DB
    db.add_all(predictions_to_save)
    db.commit()

    avg_predicted = round(np.mean([f["predicted_power_w"] for f in forecasts]), 2)

    return {
        "model"         : "linear_regression",
        "based_on_readings": len(readings),
        "forecast_hours": 6,
        "avg_predicted_w": avg_predicted,
        "forecasts"     : forecasts
    }


# ─────────────────────────────────────────────
#  2. Next cleaning prediction — based on dust trend
# ─────────────────────────────────────────────
def predict_next_cleaning(db: Session) -> dict:
    """
    Looks at dust AQI trend over last 7 days
    and predicts when AQI will next exceed threshold.
    """
    from config import settings

    readings = (
        db.query(DustReading)
        .order_by(desc(DustReading.timestamp))
        .limit(50)
        .all()
    )

    if len(readings) < 5:
        return {"error": "Not enough dust data yet — need at least 5 readings"}

    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "aqi"      : r.aqi
    } for r in readings])

    df = df.sort_values("timestamp")
    df["time_num"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() / 3600

    X = df[["time_num"]].values
    y = df["aqi"].values

    model = LinearRegression()
    model.fit(X, y)

    # Find when predicted AQI will hit threshold
    threshold    = settings.DUST_THRESHOLD
    current_time = df["time_num"].max()
    hours_ahead  = None

    for h in range(1, 73):   # check up to 72 hours ahead
        pred_aqi = float(model.predict([[current_time + h]])[0])
        if pred_aqi >= threshold:
            hours_ahead = h
            break

    if hours_ahead:
        predicted_time = datetime.now() + timedelta(hours=hours_ahead)
        message = f"Cleaning likely needed in ~{hours_ahead} hours"

        db.add(MLPrediction(
            prediction_type = "next_cleaning",
            predicted_value = float(hours_ahead),
            predicted_at    = predicted_time,
            notes           = f"AQI predicted to reach {threshold} in {hours_ahead}h"
        ))
        db.commit()

        return {
            "hours_until_cleaning": hours_ahead,
            "predicted_cleaning_time": predicted_time.strftime("%Y-%m-%d %H:%M"),
            "current_avg_aqi": round(float(np.mean(y)), 1),
            "threshold"      : threshold,
            "message"        : message
        }
    else:
        return {
            "hours_until_cleaning": None,
            "message": "AQI trend stable — no cleaning predicted in next 72 hours",
            "current_avg_aqi": round(float(np.mean(y)), 1),
            "threshold": threshold
        }


# ─────────────────────────────────────────────
#  3. AI Automation decision summary
# ─────────────────────────────────────────────
def get_ai_summary(db: Session) -> dict:
    """Returns a combined AI status for the app's AI Control tab"""

    latest_solar = (
        db.query(SolarReading)
        .order_by(desc(SolarReading.timestamp))
        .first()
    )

    latest_dust = (
        db.query(DustReading)
        .order_by(desc(DustReading.timestamp))
        .first()
    )

    from config import settings

    solar_status = {
        "voltage" : latest_solar.voltage  if latest_solar else 0,
        "power"   : latest_solar.power    if latest_solar else 0,
        "energy"  : latest_solar.energy_wh if latest_solar else 0,
    } if latest_solar else {}

    dust_status = {
        "aqi"      : latest_dust.aqi      if latest_dust else 0,
        "pm25"     : latest_dust.pm25     if latest_dust else 0,
        "category" : latest_dust.category if latest_dust else "Unknown",
        "threshold": settings.DUST_THRESHOLD,
        "exceeded" : (latest_dust.aqi >= settings.DUST_THRESHOLD) if latest_dust else False
    } if latest_dust else {}

    return {
        "solar"       : solar_status,
        "dust"        : dust_status,
        "automation"  : "active",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
