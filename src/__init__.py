"""
GoQuant Trading System
A high-performance algorithmic trading platform with matching engine and API capabilities
"""

# Core trading components
from .core import (
    MatchingEngine,
    OrderBook,
    PriceLevel,
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    Fill,
    Trade
)

# API components
from .api import (
    create_rest_api,
    CancelOrderRequest,
    OrderRequest,
    OrderResponse,
    MarketDataResponse,
    BBOResponse,
    ConnectionManager,
    websocket_market_data_endpoint,
    websocket_trade_feed_endpoint,
    broadcast_order_book_update,
    broadcast_trade_execution,
    broadcast_bbo_update
)

__version__ = "1.0.0"

__all__ = [
    # Core components
    'MatchingEngine',
    'OrderBook', 
    'PriceLevel',
    'Order',
    'OrderType',
    'OrderSide', 
    'OrderStatus',
    'Fill',
    'Trade',
    
    # API components
    'create_rest_api',
    'ConnectionManager',
    'websocket_market_data_endpoint',
    'websocket_trade_feed_endpoint', 
    'broadcast_order_book_update',
    'broadcast_trade_execution',
    'broadcast_bbo_update'
    'CancelOrderRequest',
    'OrderRequest',
    'OrderResponse',
    'MarketDataResponse',
    'BBOResponse'
]