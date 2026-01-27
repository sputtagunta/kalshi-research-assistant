"""
Kalshi API Client

Fetches market data from Kalshi's public API.
API docs: https://docs.kalshi.com/
"""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass
class KalshiMarketData:
    """Parsed market data from Kalshi API."""
    ticker: str
    title: str
    rules_primary: str
    rules_secondary: Optional[str]
    expiration_time: str
    status: str
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    last_price: float
    volume: int


class KalshiAPIError(Exception):
    """Raised when Kalshi API request fails."""
    pass


def extract_ticker_from_url(url: str) -> Optional[str]:
    """
    Extract market ticker from a Kalshi URL.

    URL formats:
    - https://kalshi.com/markets/kxindiaclimate/india-climate-goals/indiaclimate-30
    - https://kalshi.com/markets/kxbtc/bitcoin-above-100k
    - https://kalshi.com/events/kxindiaclimate/markets/indiaclimate-30

    The ticker is typically the last path segment.
    """
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    if not path_parts:
        return None

    # Last segment is usually the market ticker
    ticker = path_parts[-1]

    # Validate it looks like a ticker (alphanumeric with optional hyphens)
    if re.match(r'^[a-zA-Z0-9-]+$', ticker):
        return ticker.upper()

    return None


def extract_ticker_from_input(user_input: str) -> Optional[str]:
    """
    Extract market ticker from user input.

    Handles:
    - Direct ticker: "INDIACLIMATE-30"
    - URL: "https://kalshi.com/markets/.../indiaclimate-30"
    - Description with ticker: "Check the INDIACLIMATE-30 market"
    """
    user_input = user_input.strip()

    # Check if it's a URL
    if user_input.startswith('http'):
        return extract_ticker_from_url(user_input)

    # Check if it looks like a ticker directly
    if re.match(r'^[A-Z0-9-]+$', user_input.upper()) and len(user_input) <= 50:
        return user_input.upper()

    # Try to find a ticker pattern in the text
    # Kalshi tickers are typically UPPERCASE with optional hyphens and numbers
    ticker_pattern = r'\b([A-Z][A-Z0-9-]{2,})\b'
    matches = re.findall(ticker_pattern, user_input.upper())

    # Filter out common words that might match
    common_words = {'THE', 'AND', 'FOR', 'THIS', 'WILL', 'NOT', 'YES', 'MARKET'}
    for match in matches:
        if match not in common_words:
            return match

    return None


def fetch_market(ticker: str) -> KalshiMarketData:
    """
    Fetch market data from Kalshi API.

    Args:
        ticker: Market ticker (e.g., "INDIACLIMATE-30")

    Returns:
        KalshiMarketData with market details

    Raises:
        KalshiAPIError: If API request fails
    """
    url = f"{BASE_URL}/markets/{ticker}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            raise KalshiAPIError(f"Market '{ticker}' not found on Kalshi")
        raise KalshiAPIError(f"Kalshi API error: {e}")
    except requests.exceptions.RequestException as e:
        raise KalshiAPIError(f"Failed to connect to Kalshi API: {e}")

    data = response.json()
    market = data.get('market', {})

    if not market:
        raise KalshiAPIError(f"No market data returned for ticker '{ticker}'")

    def to_float(val) -> float:
        """Convert value to float, handling None and strings."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def to_int(val) -> int:
        """Convert value to int, handling None and strings."""
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    return KalshiMarketData(
        ticker=market.get('ticker', ticker),
        title=market.get('title', market.get('yes_sub_title', 'Unknown')),
        rules_primary=market.get('rules_primary', ''),
        rules_secondary=market.get('rules_secondary'),
        expiration_time=market.get('expected_expiration_time') or market.get('latest_expiration_time', ''),
        status=market.get('status', 'unknown'),
        yes_bid=to_float(market.get('yes_bid_dollars')),
        yes_ask=to_float(market.get('yes_ask_dollars')),
        no_bid=to_float(market.get('no_bid_dollars')),
        no_ask=to_float(market.get('no_ask_dollars')),
        last_price=to_float(market.get('last_price_dollars')),
        volume=to_int(market.get('volume_fp')),
    )


def search_markets(query: str, limit: int = 10) -> list[dict]:
    """
    Search for markets matching a query.

    Args:
        query: Search term
        limit: Maximum results to return

    Returns:
        List of market summaries
    """
    url = f"{BASE_URL}/markets"
    params = {
        'status': 'open',
        'limit': limit,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise KalshiAPIError(f"Failed to search markets: {e}")

    data = response.json()
    markets = data.get('markets', [])

    # Filter by query (case-insensitive)
    query_lower = query.lower()
    matching = [
        m for m in markets
        if query_lower in m.get('title', '').lower()
        or query_lower in m.get('ticker', '').lower()
    ]

    return matching[:limit]
