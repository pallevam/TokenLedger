from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from src.core.interfaces import ITrackerStorage, UsageRecord
from src.storage.models import UsageLog, Base
import os


class PostgresStorage(ITrackerStorage):
    def __init__(self, database_url: str = None):
        url = database_url or os.environ.get("DATABASE_URL", "")

        if not url:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Add it to your .env file (see .env.example for options)."
            )

        # Transparently upgrade the dialect to asyncpg if the caller passed a
        # plain postgresql:// URL (e.g. copied from Supabase dashboard).
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(
            url,
            echo=False,          # Set True temporarily to log SQL for debugging
            pool_pre_ping=True,  # Recycle stale connections automatically
        )
        self.SessionLocal = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def init_db(self) -> None:
        """Create all tables if they do not already exist.

        Call this once at application startup via the FastAPI lifespan hook.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def log_usage(self, record: UsageRecord) -> None:
        """Persist a single token-usage record to the database."""
        async with self.SessionLocal() as session:
            log_entry = UsageLog(
                user_id=record.user_id,
                provider=record.provider,
                model=record.model,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_cost=record.total_cost,
                latency_ms=record.latency_ms,
            )
            session.add(log_entry)
            await session.commit()

    async def get_usage(self, user_id: str) -> dict:
        """
        Returns a rich summary of usage data for the given user, including:
        - Overall totals (cost, tokens, request count, avg latency)
        - Per-provider breakdown for pie/bar charts
        - Daily cost timeline for the cost-over-time chart
        - Recent raw log records for the usage table
        """
        async with self.SessionLocal() as session:
            result = await session.execute(
                select(UsageLog).where(UsageLog.user_id == user_id)
            )
            logs = result.scalars().all()

        # --- Overall Totals ---
        total_cost = sum(log.total_cost for log in logs)
        total_tokens = sum(log.prompt_tokens + log.completion_tokens for log in logs)
        total_requests = len(logs)
        latency_values = [log.latency_ms for log in logs if log.latency_ms is not None]
        avg_latency_ms = int(sum(latency_values) / len(latency_values)) if latency_values else 0

        # --- Per-Provider Breakdown ---
        provider_stats: dict[str, dict] = {}
        for log in logs:
            p = log.provider
            if p not in provider_stats:
                provider_stats[p] = {"cost": 0.0, "tokens": 0, "requests": 0}
            provider_stats[p]["cost"] += log.total_cost
            provider_stats[p]["tokens"] += log.prompt_tokens + log.completion_tokens
            provider_stats[p]["requests"] += 1

        # --- Daily Cost Timeline (sorted ascending) ---
        daily_cost: dict[str, float] = {}
        for log in logs:
            day = log.timestamp.strftime("%Y-%m-%d")
            daily_cost[day] = daily_cost.get(day, 0.0) + log.total_cost
        timeline = [{"date": d, "cost": round(c, 6)} for d, c in sorted(daily_cost.items())]

        # --- Recent Records (last 50, newest first) for the usage table ---
        sorted_logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)
        records = [
            {
                "provider": log.provider,
                "model": log.model,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "total_cost": log.total_cost,
                "latency_ms": log.latency_ms,
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for log in sorted_logs[:50]
        ]

        return {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "avg_latency_ms": avg_latency_ms,
            "provider_stats": provider_stats,
            "timeline": timeline,
            "records": records,
        }
