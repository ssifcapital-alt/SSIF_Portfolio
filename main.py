import os
import secrets

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from alpaca_client import (
    fetch_balance, fetch_positions, fetch_orders,
    place_order as _place_order,
    cancel_order as _cancel_order,
    fetch_quotes,
)

app = FastAPI(title="SSIF Dashboard")
security = HTTPBasic()

TEAM_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")

WATCHLIST = ["META", "GOOGL", "TSLA", "AMD", "GLD", "TLT"]


# ── Auth ───────────────────────────────────────────────────────────────────────

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


# ── Portfolio ──────────────────────────────────────────────────────────────────

@app.get("/api/balance")
def get_balance(user: str = Depends(auth)):
    return fetch_balance()

@app.get("/api/positions")
def get_positions(user: str = Depends(auth)):
    return fetch_positions()

@app.get("/api/orders")
def get_orders(user: str = Depends(auth)):
    return fetch_orders()


# ── Market data ────────────────────────────────────────────────────────────────

@app.get("/api/quotes")
def get_quotes(symbols: str = ",".join(WATCHLIST), user: str = Depends(auth)):
    """Pass ?symbols=AAPL,TSLA or defaults to watchlist."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return fetch_quotes(sym_list)


# ── Trading ────────────────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    symbol: str
    side: str                    # "BUY" or "SELL"
    order_type: str              # "MARKET", "LIMIT", "STOP", "STOP_LIMIT"
    quantity: str
    limit_price: str | None = None
    stop_price: str | None = None
    time_in_force: str = "day"   # "day" or "gtc"


@app.post("/api/orders/place")
def place_order(order: OrderRequest, user: str = Depends(auth)):
    return _place_order(
        symbol=order.symbol.upper(),
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        time_in_force=order.time_in_force,
    )

@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, user: str = Depends(auth)):
    return _cancel_order(order_id)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Temporary debug — REMOVE AFTER FIXING 401 ─────────────────────────────────

@app.get("/debug")
def debug():
    key = os.environ.get("ALPACA_API_KEY", "NOT SET")
    secret = os.environ.get("ALPACA_API_SECRET", "NOT SET")
    return {
        "key_set": key != "NOT SET",
        "key_length": len(key),
        "key_prefix": key[:6] if len(key) > 6 else key,
        "secret_set": secret != "NOT SET",
        "secret_length": len(secret),
    }


# ── Frontend ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")