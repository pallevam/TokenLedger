from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.engine import URL
from sqlalchemy import select
from src.core.interfaces import ITrackerStorage, UsageRecord
from src.storage.models import UsageLog, DailyProviderUsage, Base
from datetime import date as _date
import os
import urllib.parse


def _build_async_url(raw_url: str) -> URL:
    """
    Parse a raw DATABASE_URL string (with or without +asyncpg dialect,
    with or without percent-encoded special chars in the password) and
    return a SQLAlchemy URL object that asyncpg can consume safely.

    Using URL.create() instead of passing the raw string avoids double-
    encoding / misparse issues when passwords contain '@', '+', etc.
    """
    parsed = urllib.parse.urlparse(raw_url)

    # urllib.parse.urlparse correctly splits host from userinfo even when
    # the password contains a literal '@' (as long as it's percent-encoded).
    # unquote() gives us the raw password back so URL.create() can re-encode.
    password = urllib.parse.unquote(parsed.password) if parsed.password else None
    database = parsed.path.lstrip("/")

    return URL.create(
        drivername="postgresql+asyncpg",
        username=parsed.username,
        password=password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=database,
    )


class PostgresStorage(ITrackerStorage):
    def __init__(self, database_url: str = None):
        raw_url = database_url or os.environ.get("DATABASE_URL", "")

        if not raw_url:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Add it to your .env file (see .env.example for options)."
            )

        self.engine = create_async_engine(
            _build_async_url(raw_url),
            echo=False,           # Set True temporarily to log SQL for debugging
            pool_pre_ping=True,   # Recycle stale connections automatically
            connect_args={
                "ssl": "require", # Supabase mandates SSL; also fixes IPv6 resolution
                                  # on macOS where asyncpg's auto-negotiate path fails
            },
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

    async def upsert_daily_usage(
        self,
        day: _date,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Insert or update a daily aggregate row pulled from a provider API."""
        async with self.SessionLocal() as session:
            existing = await session.execute(
                select(DailyProviderUsage).where(
                    and_(
                        DailyProviderUsage.date == day,
                        DailyProviderUsage.provider == provider,
                        DailyProviderUsage.model == model,
                    )
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.input_tokens = input_tokens
                row.output_tokens = output_tokens
                row.cost_usd = cost_usd
            else:
                session.add(
                    DailyProviderUsage(
                        date=day,
                        provider=provider,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=cost_usd,
                    )
                )
            await session.commit()

    async def get_daily_usage(
        self,
        start: _date | None = None,
        end: _date | None = None,
    ) -> list[dict]:
        """Return daily provider usage rows in [start, end], newest first."""
        async with self.SessionLocal() as session:
            stmt = select(DailyProviderUsage)
            if start:
                stmt = stmt.where(DailyProviderUsage.date >= start)
            if end:
                stmt = stmt.where(DailyProviderUsage.date <= end)
            result = await session.execute(stmt)
            rows = result.scalars().all()
        rows.sort(key=lambda r: (r.date, r.provider, r.model), reverse=True)
        return [
            {
                "date": r.date.isoformat(),
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": round(r.cost_usd, 6),
                "pulled_at": r.pulled_at.isoformat() if r.pulled_at else None,
            }
            for r in rows
        ]
