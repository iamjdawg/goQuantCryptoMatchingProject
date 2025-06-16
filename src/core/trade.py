from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid
from .order import OrderSide

class Trade:
    """
    represents a trade execution between two orders
    """
    def __init__(
        self,
        symbol: str,
        price: Decimal,
        quantity: Decimal,
        maker_order_id: str, # passive order which was resting in the book
        taker_order_id: str, # aggressive order which took the passive order
        aggressor_side: OrderSide, # side of the incoming order (taker), buy or sell
        trade_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.trade_id = trade_id or str(uuid.uuid4())
        self.symbol = symbol
        self.price = Decimal(str(price))
        self.quantity = Decimal(str(quantity))
        self.maker_order_id = maker_order_id  # The resting order
        self.taker_order_id = taker_order_id  # The incoming order
        self.aggressor_side = aggressor_side  # Side of the incoming order
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary for API responses and WebSocket streaming."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'trade_id': self.trade_id,
            'price': str(self.price),
            'quantity': str(self.quantity),
            'aggressor_side': self.aggressor_side.value,
            'maker_order_id': self.maker_order_id,
            'taker_order_id': self.taker_order_id
        }
    
    def __str__(self) -> str:
        return f"Trade: {self.quantity} {self.symbol} @ {self.price} ({self.aggressor_side.value} aggressor)"
    
    def __repr__(self) -> str:
        return f"Trade({self.trade_id[:8]}...)"