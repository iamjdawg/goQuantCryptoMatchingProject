"""
API module for the matching engine
Handles REST and WebSocket endpoints
"""

from .rest_api import create_rest_api, CancelOrderRequest, OrderRequest, OrderResponse, MarketDataResponse, BBOResponse
from .websocket_api import (
    ConnectionManager,
    websocket_market_data_endpoint,
    websocket_trade_feed_endpoint,
    broadcast_order_book_update,
    broadcast_trade_execution,
    broadcast_bbo_update
)

__all__ = [
    'create_rest_api',
    'ConnectionManager',
    'websocket_market_data_endpoint',
    'websocket_trade_feed_endpoint',
    'broadcast_order_book_update',
    'broadcast_trade_execution',
    'broadcast_bbo_update'
]