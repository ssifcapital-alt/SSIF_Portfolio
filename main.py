import os
import secrets
import json

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from alpaca_client import (
    fetch_balance, fetch_positions, fetch_orders,
    place_order as _place_order,
    place_option_order as _place_option_order,
    cancel_order as _cancel_order,
    fetch_quotes,
    fetch_option_contracts,
    fetch_option_quotes,
)

app = FastAPI(title="SSIF Dashboard")
security = HTTPBasic()

TEAM_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")

# Default watchlist — persisted in watchlist.json if edited by team
WATCHLIST_FILE = "watchlist.json"
DEFAULT_WATCHLIST = ["META", "GOOGL", "TSLA", "AMD", "GLD", "TLT"]


def load_watchlist() -> list[str]:
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return DEFAULT_WATCHLIST


def save_watchlist(symbols: list[str]):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(symbols, f)


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


# ── Watchlist ──────────────────────────────────────────────────────────────────

@app.get("/api/watchlist")
def get_watchlist(user: str = Depends(auth)):
    return load_watchlist()

@app.post("/api/watchlist")
def update_watchlist(symbols: list[str], user: str = Depends(auth)):
    cleaned = [s.strip().upper() for s in symbols if s.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="Watchlist cannot be empty")
    save_watchlist(cleaned)
    return cleaned


# ── Market data ────────────────────────────────────────────────────────────────

@app.get("/api/quotes")
def get_quotes(symbols: str = "", user: str = Depends(auth)):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        sym_list = load_watchlist()
    return fetch_quotes(sym_list)


# ── Equity trading ─────────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: str
    limit_price: str | None = None
    stop_price: str | None = None
    time_in_force: str = "day"


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


# ── Options ────────────────────────────────────────────────────────────────────

@app.get("/api/options/contracts")
def get_option_contracts(
    underlying: str,
    expiry_gte: str | None = None,
    expiry_lte: str | None = None,
    contract_type: str | None = None,
    strike_gte: float | None = None,
    strike_lte: float | None = None,
    user: str = Depends(auth),
):
    return fetch_option_contracts(
        underlying=underlying,
        expiry_gte=expiry_gte,
        expiry_lte=expiry_lte,
        contract_type=contract_type,
        strike_gte=strike_gte,
        strike_lte=strike_lte,
    )

@app.get("/api/options/quotes")
def get_option_quotes(symbols: str, user: str = Depends(auth)):
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return fetch_option_quotes(sym_list)


class OptionOrderRequest(BaseModel):
    option_symbol: str      # full OCC symbol e.g. AAPL240119C00150000
    side: str               # "BUY" or "SELL"
    order_type: str         # "MARKET" or "LIMIT"
    quantity: int           # number of contracts
    limit_price: float | None = None
    time_in_force: str = "day"


@app.post("/api/options/place")
def place_option_order(order: OptionOrderRequest, user: str = Depends(auth)):
    return _place_option_order(
        option_symbol=order.option_symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        limit_price=order.limit_price,
        time_in_force=order.time_in_force,
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Frontend ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
