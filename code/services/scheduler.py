from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal
from services import dust_service
from config import settings

scheduler = AsyncIOScheduler()

async def scheduled_dust_check():
    print("[SCHEDULER] Running dust check...")
    db = SessionLocal()
    try:
        await dust_service.fetch_dust_data(db)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(
        scheduled_dust_check,
        trigger  = "interval",
        minutes  = settings.DUST_CHECK_INTERVAL,
        id       = "dust_check",
        replace_existing = True
    )
    scheduler.start()
    print(f"[SCHEDULER] Dust check every {settings.DUST_CHECK_INTERVAL} min")

def stop_scheduler():
    scheduler.shutdown()
