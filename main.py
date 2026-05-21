import os
import uuid
import secrets

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from webull_client import (
    get_client, ACCOUNT_ID,
    fetch_balance, fetch_positions, fetch_orders,
    place_order as wb_place_order,
    cancel_order as wb_cancel_order,
)

app = FastAPI(title="SSIF Dashboard")
security = HTTPBasic()

# ── Auth ──────────────────────────────────────────────────────────────────────
TEAM_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")


def auth(creds: HTTPBasicCredentials = Depends(security)):
    valid = secrets.compare_digest(
        creds.password.encode("utf-8"),
        TEAM_PASSWORD.encode("utf-8"),
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Unauthorised",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


# ── Portfolio routes ───────────────────────────────────────────────────────────

@app.get("/api/balance")
def get_balance(user: str = Depends(auth)):
    return fetch_balance(get_client(), ACCOUNT_ID)


@app.get("/api/positions")
def get_positions(user: str = Depends(auth)):
    return fetch_positions(get_client(), ACCOUNT_ID)


@app.get("/api/orders")
def get_orders(user: str = Depends(auth)):
    return fetch_orders(get_client(), ACCOUNT_ID)


# ── Trade routes ───────────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    symbol: str
    side: str              # "BUY" or "SELL"
    order_type: str        # "MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_LIMIT", "TRAILING_STOP_LOSS"
    quantity: str          # number of shares as string
    limit_price: str | None = None
    time_in_force: str = "DAY"   # "DAY" or "GTC"


@app.post("/api/orders/place")
def place_order(order: OrderRequest, user: str = Depends(auth)):
    payload = {
        "client_order_id":         uuid.uuid4().hex,
        "combo_type":              "NORMAL",
        "symbol":                  order.symbol.upper(),
        "instrument_type":         "EQUITY",
        "market":                  "US",
        "order_type":              order.order_type,
        "quantity":                order.quantity,
        "side":                    order.side,
        "time_in_force":           order.time_in_force,
        "support_trading_session": "CORE",
        "entrust_type":            "QTY",
    }
    if order.limit_price and order.order_type in ("LIMIT", "STOP_LOSS_LIMIT"):
        payload["limit_price"] = order.limit_price

    return wb_place_order(get_client(), ACCOUNT_ID, payload)


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, user: str = Depends(auth)):
    return wb_cancel_order(get_client(), ACCOUNT_ID, order_id)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Serve frontend ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")