import os
from decimal import Decimal

class Config:
    # API Configuration
    REST_HOST = os.getenv('REST_HOST', '0.0.0.0')
    REST_PORT = int(os.getenv('REST_PORT', 8000))
    
    WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', 8001))
    
    # Matching Engine Configuration
    MAX_ORDERS_PER_SECOND = int(os.getenv('MAX_ORDERS_PER_SECOND', 10000))
    MAX_ORDER_BOOK_DEPTH = int(os.getenv('MAX_ORDER_BOOK_DEPTH', 1000))
    
    # Performance Configuration
    ORDER_BOOK_DEPTH_LEVELS = int(os.getenv('ORDER_BOOK_DEPTH_LEVELS', 10))
    RECENT_TRADES_LIMIT = int(os.getenv('RECENT_TRADES_LIMIT', 100))
    
    # Fee Configuration (for bonus features)
    MAKER_FEE_RATE = Decimal(os.getenv('MAKER_FEE_RATE', '0.001'))  # 0.1%
    TAKER_FEE_RATE = Decimal(os.getenv('TAKER_FEE_RATE', '0.002'))  # 0.2%
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'matching_engine.log')
    
    # Database Configuration (for persistence bonus)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///matching_engine.db')
    
    # Supported Trading Pairs
    SUPPORTED_SYMBOLS = [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'ADA-USDT', 
        'DOT-USDT', 'XRP-USDT', 'LTC-USDT', 'LINK-USDT'
    ]
    
    # Order Validation
    MIN_ORDER_QUANTITY = Decimal('0.00000001')  # 1 satoshi equivalent
    MAX_ORDER_QUANTITY = Decimal('1000000')     # 1 million
    MIN_ORDER_PRICE = Decimal('0.00000001')
    MAX_ORDER_PRICE = Decimal('1000000')
    
    # Rate Limiting
    RATE_LIMIT_ORDERS_PER_MINUTE = int(os.getenv('RATE_LIMIT_ORDERS_PER_MINUTE', 1000))
    RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', 6000))
    
    # WebSocket Configuration
    MAX_WEBSOCKET_CONNECTIONS = int(os.getenv('MAX_WEBSOCKET_CONNECTIONS', 1000))
    WEBSOCKET_HEARTBEAT_INTERVAL = int(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', 30))
    
    # Development/Testing
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('TESTING', 'False').lower() == 'true'