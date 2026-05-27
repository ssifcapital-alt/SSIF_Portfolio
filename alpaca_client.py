import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    GetOrdersRequest,
    GetOptionContractsRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, QueryOrderStatus, ContractType, PositionIntent
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockSnapshotRequest, OptionLatestQuoteRequest

API_KEY    = os.environ["ALPACA_API_KEY"]
API_SECRET = os.environ["ALPACA_API_SECRET"]

def get_trading_client() -> TradingClient:
    return TradingClient(API_KEY, API_SECRET, paper=True)

def get_data_client() -> StockHistoricalDataClient:
    return StockHistoricalDataClient(API_KEY, API_SECRET)

def get_option_data_client() -> OptionHistoricalDataClient:
    return OptionHistoricalDataClient(API_KEY, API_SECRET)


# ── Account ────────────────────────────────────────────────────────────────────

def fetch_balance() -> dict:
    acct = get_trading_client().get_account()
    return {
        "portfolio_value":    str(acct.portfolio_value),
        "cash":               str(acct.cash),
        "buying_power":       str(acct.buying_power),
        "equity":             str(acct.equity),
        "last_equity":        str(acct.last_equity),
        "long_market_value":  str(acct.long_market_value),
        "short_market_value": str(acct.short_market_value),
        "daytrade_count":     acct.daytrade_count,
        "currency":           acct.currency,
    }


# ── Positions ──────────────────────────────────────────────────────────────────

def fetch_positions() -> list:
    positions = get_trading_client().get_all_positions()
    return [
        {
            "symbol":          p.symbol,
            "qty":             str(p.qty),
            "side":            str(p.side),
            "avg_entry_price": str(p.avg_entry_price),
            "current_price":   str(p.current_price),
            "market_value":    str(p.market_value),
            "cost_basis":      str(p.cost_basis),
            "unrealized_pl":   str(p.unrealized_pl),
            "unrealized_plpc": str(p.unrealized_plpc),
            "change_today":    str(p.change_today),
            "asset_class":     str(p.asset_class) if hasattr(p, "asset_class") else "us_equity",
        }
        for p in positions
    ]


# ── Orders ─────────────────────────────────────────────────────────────────────

def fetch_orders(limit: int = 50) -> list:
    req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
    orders = get_trading_client().get_orders(filter=req)
    return [
        {
            "id":               str(o.id),
            "client_order_id":  str(o.client_order_id),
            "symbol":           o.symbol,
            "qty":              str(o.qty),
            "filled_qty":       str(o.filled_qty),
            "side":             str(o.side),
            "order_type":       str(o.order_type),
            "status":           str(o.status),
            "time_in_force":    str(o.time_in_force),
            "limit_price":      str(o.limit_price) if o.limit_price else None,
            "filled_avg_price": str(o.filled_avg_price) if o.filled_avg_price else None,
            "submitted_at":     o.submitted_at.isoformat() if o.submitted_at else None,
            "filled_at":        o.filled_at.isoformat() if o.filled_at else None,
        }
        for o in orders
    ]


# ── Place equity order ─────────────────────────────────────────────────────────

def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    limit_price: str | None = None,
    stop_price: str | None = None,
    time_in_force: str = "day",
) -> dict:
    client = get_trading_client()
    _side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
    _tif  = TimeInForce(time_in_force.lower())

    ot = order_type.upper()
    if ot == "MARKET":
        req = MarketOrderRequest(symbol=symbol, qty=float(quantity), side=_side, time_in_force=_tif)
    elif ot == "LIMIT":
        req = LimitOrderRequest(symbol=symbol, qty=float(quantity), side=_side,
                                time_in_force=_tif, limit_price=float(limit_price))
    elif ot == "STOP":
        req = StopOrderRequest(symbol=symbol, qty=float(quantity), side=_side,
                               time_in_force=_tif, stop_price=float(stop_price))
    elif ot == "STOP_LIMIT":
        req = StopLimitOrderRequest(symbol=symbol, qty=float(quantity), side=_side,
                                    time_in_force=_tif,
                                    limit_price=float(limit_price),
                                    stop_price=float(stop_price))
    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    o = client.submit_order(req)
    return _fmt_order(o)


# ── Place options order ────────────────────────────────────────────────────────

def place_option_order(
    option_symbol: str,
    side: str,
    order_type: str,
    quantity: int,
    limit_price: float | None = None,
    time_in_force: str = "day",
) -> dict:
    client = get_trading_client()
    _side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
    _tif  = TimeInForce(time_in_force.lower())

    if order_type.upper() == "MARKET":
        req = MarketOrderRequest(
            symbol=option_symbol,
            qty=quantity,
            side=_side,
            time_in_force=_tif,
        )
    else:
        req = LimitOrderRequest(
            symbol=option_symbol,
            qty=quantity,
            side=_side,
            time_in_force=_tif,
            limit_price=limit_price,
        )

    o = client.submit_order(req)
    return _fmt_order(o)


# ── Get option contracts ───────────────────────────────────────────────────────

def fetch_option_contracts(
    underlying: str,
    expiry_gte: str | None = None,
    expiry_lte: str | None = None,
    contract_type: str | None = None,
    strike_gte: float | None = None,
    strike_lte: float | None = None,
) -> list:
    req = GetOptionContractsRequest(
        underlying_symbols=[underlying.upper()],
        expiration_date_gte=expiry_gte,
        expiration_date_lte=expiry_lte,
        type=ContractType(contract_type.lower()) if contract_type else None,
        strike_price_gte=strike_gte,
        strike_price_lte=strike_lte,
        limit=100,
    )
    contracts = get_trading_client().get_option_contracts(req)
    results = []
    for c in contracts:
        results.append({
            "symbol":      c.symbol,
            "name":        c.name if hasattr(c, "name") else c.symbol,
            "underlying":  c.underlying_symbol,
            "expiry":      str(c.expiration_date),
            "strike":      str(c.strike_price),
            "type":        str(c.type),
            "open_interest": str(c.open_interest) if hasattr(c, "open_interest") and c.open_interest else "—",
        })
    return results


# ── Cancel order ───────────────────────────────────────────────────────────────

def cancel_order(order_id: str) -> dict:
    get_trading_client().cancel_order_by_id(order_id)
    return {"cancelled": order_id}


# ── Market data — equities ─────────────────────────────────────────────────────

def fetch_quotes(symbols: list[str]) -> dict:
    client = get_data_client()
    req   = StockSnapshotRequest(symbol_or_symbols=symbols)
    snaps = client.get_stock_snapshot(req)
    result = {}
    for sym, snap in snaps.items():
        result[sym] = {
            "last":       float(snap.latest_trade.price) if snap.latest_trade else None,
            "bid":        float(snap.latest_quote.bid_price) if snap.latest_quote else None,
            "ask":        float(snap.latest_quote.ask_price) if snap.latest_quote else None,
            "open":       float(snap.daily_bar.open) if snap.daily_bar else None,
            "high":       float(snap.daily_bar.high) if snap.daily_bar else None,
            "low":        float(snap.daily_bar.low) if snap.daily_bar else None,
            "close":      float(snap.daily_bar.close) if snap.daily_bar else None,
            "prev_close": float(snap.previous_daily_bar.close) if snap.previous_daily_bar else None,
            "volume":     int(snap.daily_bar.volume) if snap.daily_bar else None,
        }
    return result


# ── Market data — options ──────────────────────────────────────────────────────

def fetch_option_quotes(symbols: list[str]) -> dict:
    client = get_option_data_client()
    req    = OptionLatestQuoteRequest(symbol_or_symbols=symbols)
    quotes = client.get_option_latest_quote(req)
    result = {}
    for sym, q in quotes.items():
        result[sym] = {
            "bid": float(q.bid_price) if q.bid_price else None,
            "ask": float(q.ask_price) if q.ask_price else None,
            "mid": round((float(q.bid_price) + float(q.ask_price)) / 2, 2)
                   if q.bid_price and q.ask_price else None,
        }
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_order(o) -> dict:
    return {
        "id":              str(o.id),
        "client_order_id": str(o.client_order_id),
        "symbol":          o.symbol,
        "qty":             str(o.qty),
        "side":            str(o.side),
        "order_type":      str(o.order_type),
        "status":          str(o.status),
        "submitted_at":    o.submitted_at.isoformat() if o.submitted_at else None,
    }
