import os
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

# Your approved Webull API endpoint — replace with the URL from your approval email
WEBULL_ENDPOINT = os.environ.get("WEBULL_ENDPOINT", "https://openapi.webull.com")

ACCOUNT_ID = os.environ.get("WEBULL_ACCOUNT_ID")


def get_client() -> TradeClient:
    """
    Returns an authenticated Webull TradeClient.
    Credentials are read from environment variables — never hardcode these.
    """
    app_key    = os.environ["WEBULL_APP_KEY"]
    app_secret = os.environ["WEBULL_APP_SECRET"]

    api_client = ApiClient(app_key, app_secret, "us")
    api_client.add_endpoint("us", WEBULL_ENDPOINT)

    return TradeClient(api_client)
