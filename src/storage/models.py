from sqlalchemy import Column, Integer, String, Float, DateTime, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class DailyProviderUsage(Base):
    """Aggregated daily usage pulled from a provider's billing/usage API.

    Distinct from UsageLog (per-request, written by our app). This row is
    authoritative for what the provider says you used on a given day.
    """
    __tablename__ = "daily_provider_usage"
    __table_args__ = (
        UniqueConstraint("date", "provider", "model", name="uq_daily_provider_model"),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    provider = Column(String, index=True, nullable=False)
    model = Column(String, nullable=False, default="all")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    pulled_at = Column(DateTime, default=datetime.datetime.utcnow)

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class UserLimit(Base):
    __tablename__ = "user_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    monthly_budget = Column(Float, default=0.0)
    current_spend = Column(Float, default=0.0)
