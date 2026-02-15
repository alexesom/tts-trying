from fastapi import FastAPI

from app.config.settings import get_settings
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository
from app.interfaces.http.router import router

settings = get_settings()
repo = SQLiteJobRepository(settings.db_path)
repo.init_schema()

app = FastAPI(title="TTS Service", version="0.1.0")
app.include_router(router)
