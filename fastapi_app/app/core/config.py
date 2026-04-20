# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # секрет для JWT-токенов
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "your-very-secret-key-change-me",  # лучше поменяй :)
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
