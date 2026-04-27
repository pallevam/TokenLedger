from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.interfaces import ITrackerStorage, UsageRecord
from src.storage.models import UsageLog, Base
import os

class PostgresStorage(ITrackerStorage):
    def __init__(self, database_url: str = None):
        # Fallback to local sqlite for dev if DATABASE_URL is not set
        url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./tracker.db")
        self.engine = create_engine(url)
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def log_usage(self, record: UsageRecord) -> None:
        db = self.SessionLocal()
        try:
            log_entry = UsageLog(
                user_id=record.user_id,
                provider=record.provider,
                model=record.model,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_cost=record.total_cost,
                latency_ms=record.latency_ms
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()

    def get_usage(self, user_id: str) -> dict:
        db = self.SessionLocal()
        try:
            logs = db.query(UsageLog).filter(UsageLog.user_id == user_id).all()
            total_cost = sum(log.total_cost for log in logs)
            total_tokens = sum(log.prompt_tokens + log.completion_tokens for log in logs)
            
            # Convert objects to dict for rendering
            log_dicts = []
            for log in logs:
                log_dicts.append({
                    "provider": log.provider,
                    "model": log.model,
                    "prompt_tokens": log.prompt_tokens,
                    "completion_tokens": log.completion_tokens,
                    "total_cost": log.total_cost,
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
                
            return {
                "total_cost": total_cost, 
                "total_tokens": total_tokens, 
                "records": log_dicts
            }
        finally:
            db.close()
