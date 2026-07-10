from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base
from routes.api import router
from services import mqtt_service
from services.scheduler import start_scheduler, stop_scheduler
from config import settings

# ── Create all DB tables on startup ──
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    print("=" * 50)
    print("  Solar Sunroof Backend — Starting up")
    print("=" * 50)
    mqtt_service.start()
    start_scheduler()
    yield
    # ── Shutdown ──
    stop_scheduler()
    print("[SERVER] Shutting down")

app = FastAPI(
    title       = "Solar Sunroof Backend",
    description = "Controls solar panel cleaning bot, tracks power, AI forecasting",
    version     = "1.0.0",
    lifespan    = lifespan
)

# ── Allow mobile app to connect ──
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register all routes under /api ──
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "server" : "Solar Sunroof Backend v1.0",
        "status" : "running",
        "docs"   : "http://10.164.79.23:8000/docs",
        "routes" : [
            "POST /api/solar/data          ← ESP32 sends sensor data",
            "GET  /api/solar/latest        ← latest solar readings",
            "GET  /api/solar/history       ← history for graphs",
            "POST /api/solar/relay         ← relay ON/OFF",
            "POST /api/bot/command         ← bot FORWARD/BACKWARD/CLEAN etc",
            "GET  /api/bot/status/latest   ← latest bot status",
            "GET  /api/dust/latest         ← latest AQI reading",
            "GET  /api/dust/fetch          ← manually trigger Google API",
            "GET  /api/ai/forecast         ← power forecast next 6h",
            "GET  /api/ai/predict-cleaning ← next cleaning prediction",
            "GET  /api/ai/summary          ← full AI tab summary",
            "GET  /api/cleaning/history    ← cleaning events log",
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
