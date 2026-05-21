import os
import uuid
import secrets

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from webull_client import get_client, ACCOUNT_ID

app = FastAPI(title="SSIF Dashboard")
security = HTTPBasic()

# ── Auth ──────────────────────────────────────────────────────────────────────
# Set DASHBOARD_PASSWORD in Render's environment variables panel
TEAM_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")


def auth(creds: HTTPBasicCredentials = Depends(security)):
    """HTTP Basic Auth — shared team password."""
    valid = secrets.compare_digest(
        creds.password.encode("utf-8"),
        TEAM_PASSWORD.encode("utf-8")
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
    """Account balance, buying power, and P&L summary."""
    client = get_client()
    res = client.account_v2.get_account_balance(ACCOUNT_ID)
    return res.json()


@app.get("/api/positions")
def get_positions(user: str = Depends(auth)):
    """All open positions with cost basis and unrealised P&L."""
    client = get_client()
    res = client.account_v2.get_account_position(ACCOUNT_ID)
    return res.json()


@app.get("/api/orders")
def get_orders(user: str = Depends(auth)):
    """Order history — recent filled, cancelled, and open orders."""
    client = get_client()
    res = client.order_v2.get_order_list(ACCOUNT_ID)
    return res.json()


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
    """Place a new order on the paper trading account."""
    client = get_client()

    payload = {
        "client_order_id":        uuid.uuid4().hex,
        "combo_type":             "NORMAL",
        "symbol":                 order.symbol.upper(),
        "instrument_type":        "EQUITY",
        "market":                 "US",
        "order_type":             order.order_type,
        "quantity":               order.quantity,
        "side":                   order.side,
        "time_in_force":          order.time_in_force,
        "support_trading_session":"CORE",
        "entrust_type":           "QTY",
    }

    if order.limit_price and order.order_type in ("LIMIT", "STOP_LOSS_LIMIT"):
        payload["limit_price"] = order.limit_price

    res = client.order_v2.place_order(ACCOUNT_ID, [payload])
    return res.json()


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, user: str = Depends(auth)):
    """Cancel an open order by its client_order_id."""
    client = get_client()
    res = client.order_v2.cancel_order(ACCOUNT_ID, order_id)
    return res.json()


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Used by Render and UptimeRobot to keep the service warm."""
    return {"status": "ok"}


# ── Serve frontend ─────────────────────────────────────────────────────────────
# Static files (CSS, JS if separated) live in /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")
