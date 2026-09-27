from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty


def _ensure_columns() -> None:
    """create_all 不会给已存在的表补列，这里幂等添加早到/晚到带宽列。"""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE lines ADD COLUMN IF NOT EXISTS early_tolerance_min FLOAT DEFAULT 0.0"))
        conn.execute(text("ALTER TABLE lines ADD COLUMN IF NOT EXISTS late_tolerance_min FLOAT DEFAULT 0.0"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="BusGap", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
