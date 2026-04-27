from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.storage.database import PostgresStorage
import os

app = FastAPI(title="Token Tracker Dashboard")

# Initialize storage
storage = PostgresStorage()

# Setup Jinja templates
# Assumes the app is run from the root directory where templates/ exists
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: str = "default_user"):
    """
    Renders the simple Jinja dashboard.
    """
    usage_data = storage.get_usage(user_id=user_id)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_id": user_id,
        "total_cost": usage_data["total_cost"],
        "total_tokens": usage_data["total_tokens"],
        "records": usage_data["records"]
    })

@app.get("/health")
def health_check():
    return {"status": "ok"}
