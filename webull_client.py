import os
from webull.core.client import ApiClient
from webull.trade.request.v2.get_account_balance_request import AccountBalanceRequest
from webull.trade.request.v2.get_account_positions_request import AccountPositionsRequest
from webull.trade.request.v2.get_order_history_request import OrderHistoryRequest
from webull.trade.request.v2.place_order_request import PlaceOrderRequest
from webull.trade.request.v2.cancel_order_request import CancelOrderRequest

WEBULL_ENDPOINT = os.environ.get("WEBULL_ENDPOINT", "https://openapi.webull.com")
ACCOUNT_ID = os.environ.get("WEBULL_ACCOUNT_ID")


def get_client() -> ApiClient:
    """
    Returns an authenticated Webull ApiClient.
    Credentials are read from environment variables — never hardcode these.
    """
    app_key    = os.environ["WEBULL_APP_KEY"]
    app_secret = os.environ["WEBULL_APP_SECRET"]

    client = ApiClient(app_key, app_secret, "us")
    client.add_endpoint("us", WEBULL_ENDPOINT)
    return client


def fetch_balance(client: ApiClient, account_id: str):
    req = AccountBalanceRequest()
    req.set_account_id(account_id)
    return client.get_response(req).json()


def fetch_positions(client: ApiClient, account_id: str):
    req = AccountPositionsRequest()
    req.set_account_id(account_id)
    return client.get_response(req).json()


def fetch_orders(client: ApiClient, account_id: str):
    req = OrderHistoryRequest()
    req.set_account_id(account_id)
    return client.get_response(req).json()


def place_order(client: ApiClient, account_id: str, order_payload: dict):
    req = PlaceOrderRequest()
    req.set_account_id(account_id)
    req.set_new_orders([order_payload])
    req.add_custom_headers_from_order([order_payload])
    return client.get_response(req).json()


def cancel_order(client: ApiClient, account_id: str, client_order_id: str):
    req = CancelOrderRequest()
    req.set_account_id(account_id)
    req.set_client_order_id(client_order_id)
    return client.get_response(req).json()