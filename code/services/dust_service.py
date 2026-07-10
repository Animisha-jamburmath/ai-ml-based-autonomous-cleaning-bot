import httpx
from sqlalchemy.orm import Session
from models.models import DustReading, CleaningEvent
from services import mqtt_service
from config import settings

# OpenWeatherMap Air Pollution API
OWM_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

async def fetch_dust_data(db: Session) -> dict:
    try:
        params = {
            "lat"   : settings.LATITUDE,
            "lon"   : settings.LONGITUDE,
            "appid" : settings.GOOGLE_API_KEY  # we reuse same env variable
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(OWM_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Parse OpenWeatherMap response
        components = data["list"][0]["components"]
        aqi_index  = data["list"][0]["main"]["aqi"]

        pm25 = components.get("pm2_5", 0.0)
        pm10 = components.get("pm10",  0.0)

        # OWM AQI is 1-5 scale — convert to 0-500 scale
        aqi_map = {1: 25, 2: 75, 3: 150, 4: 250, 5: 400}
        aqi = aqi_map.get(aqi_index, 0)

        # Category based on AQI
        if aqi <= 50:
            category = "Good"
        elif aqi <= 100:
            category = "Moderate"
        elif aqi <= 200:
            category = "Unhealthy for Sensitive"
        elif aqi <= 250:
            category = "Unhealthy"
        elif aqi <= 300:
            category = "Very Unhealthy"
        else:
            category = "Hazardous"

        print(f"[DUST] AQI={aqi} PM2.5={pm25} PM10={pm10} — {category}")

        # Store in DB
        reading = DustReading(
            aqi=aqi, pm25=pm25, pm10=pm10, category=category
        )
        db.add(reading)
        db.commit()

        # Threshold check
        threshold_triggered = check_threshold_and_act(aqi, db)

        return {
            "aqi"                 : aqi,
            "pm25"                : pm25,
            "pm10"                : pm10,
            "category"            : category,
            "threshold_triggered" : threshold_triggered
        }

    except Exception as e:
        print(f"[DUST] Error fetching air quality: {e}")
        return {"error": str(e)}


def check_threshold_and_act(aqi: int, db: Session) -> bool:
    if aqi >= settings.DUST_THRESHOLD:
        print(f"[DUST] AQI {aqi} >= threshold {settings.DUST_THRESHOLD} → cleaning!")
        mqtt_service.publish_bot_command({"action": "CLEAN"})

        event = CleaningEvent(
            trigger        = "auto_dust",
            aqi_at_trigger = aqi,
            status         = "started",
            notes          = f"Auto triggered: AQI {aqi} exceeded {settings.DUST_THRESHOLD}"
        )
        db.add(event)
        db.commit()
        return True

    print(f"[DUST] AQI {aqi} < threshold — no action")
    return False