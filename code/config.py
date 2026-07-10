from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "solar_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "yourpassword"

    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883

    GOOGLE_API_KEY: str = ""
    LATITUDE: float = 12.9716
    LONGITUDE: float = 77.5946

    DUST_THRESHOLD: int = 100
    DUST_CHECK_INTERVAL: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
