from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.storage.database import PostgresStorage

# ---------------------------------------------------------------------------
# Application lifespan – runs init_db() once on startup before any request
# is served, and cleans up the connection pool on shutdown.
# ---------------------------------------------------------------------------
storage = PostgresStorage()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.init_db()   # create tables if they don't exist yet
    yield
    await storage.engine.dispose()  # clean shutdown of the connection pool

app = FastAPI(title="Token Tracker Dashboard", lifespan=lifespan)

# Setup Jinja templates
# Assumes the app is run from the root directory where templates/ exists
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: str = "default_user"):
    """
    Renders the dashboard with full usage stats: overall totals, per-provider
    breakdown, daily cost timeline, and recent usage logs.
    """
    usage_data = await storage.get_usage(user_id=user_id)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_id": user_id,
        "total_cost": usage_data["total_cost"],
        "total_tokens": usage_data["total_tokens"],
        "total_requests": usage_data["total_requests"],
        "avg_latency_ms": usage_data["avg_latency_ms"],
        "provider_stats": usage_data["provider_stats"],
        "timeline": usage_data["timeline"],
        "records": usage_data["records"],
    })


@app.get("/health")
async def health_check():
    return {"status": "ok"}
