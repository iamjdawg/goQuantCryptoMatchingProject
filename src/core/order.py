from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from enum import Enum
import uuid

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"
    FOK = "FOK"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Order:
    def __init__(
            self,
            symbol: str,
            order_type: OrderType,
            side: OrderSide,
            quantity: Decimal,
            price: Optional[Decimal] = None,
            order_id: Optional[str] = None
    ):
        # validation
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        if order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK] and price is None:
            raise ValueError(f"Price must be specified for {order_type.value} orders")
        if price is not None and price <= 0:
            raise ValueError("Price must be greater than zero")
        
        # core attributes
        self.symbol = symbol
        self.order_id = order_id or str(uuid.uuid4())
        self.order_type = order_type
        self.side = side
        self.quantity = Decimal(str(quantity))
        self.price = Decimal(str(price)) 

        # state tracking
        self.filled_quantity = Decimal('0.0')
        self.remaining_quantity = self.quantity
        self.status = OrderStatus.PENDING

        # timestamps
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

        # for matching engine
        self.fills = []  # List to track fills

    @property
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL
    
    @property
    def is_market_order(self) -> bool:
        return self.order_type == OrderType.MARKET
    
    @property
    def is_limit_order(self) -> bool:
        return self.order_type == OrderType.LIMIT
    
    @property
    def is_ioc_order(self) -> bool:
        return self.order_type == OrderType.IOC
    
    @property
    def is_fok_order(self) -> bool:
        return self.order_type == OrderType.FOK
    
    @property
    def is_filled(self) -> bool:
        return self.remaining_quantity == 0
    
    @property
    def is_partially_filled(self) -> bool:
        return 0 < self.filled_quantity < self.quantity
    
    def can_match_with_price(self, other_price : Decimal) -> bool:
        """ 
        check if this order can be matched with another order based on price.
        """

        if self.is_market_order:
            return True
        if self.is_buy:
            return self.price >= other_price
        else: # sell
            return self.price <= other_price
        
    def fill(self, quantity: Decimal, price: Decimal) -> None:
        """
        Fill the order with a specified quantity.
        """
        if quantity <= 0:
            raise ValueError("fill quantity must be greater than zero")
        if quantity > self.remaining_quantity:
            raise ValueError("fill quantity exceeds remaining quantity")
        
        # create a fill record
        fill = Fill(
            order_id = self.order_id,
            quantity = quantity,
            price = price,
            timestamp = datetime.now(timezone.utc)
        )

        # update order state
        self.filled_quantity += quantity
        self.remaining_quantity -= quantity
        self.updated_at = fill.timestamp
        self.fills.append(fill)

        # update status
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        return fill
    
    def cancel(self) -> None:
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel an order that is {self.status.value}")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """
        convert the order to a dictionary for API responses
        """
        return{
            'order_id': self.order_id,
            'symbol': self.symbol,
            'type': self.order_type.value,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'price': str(self.price) if self.price else None,
            'filled_quantity': str(self.filled_quantity),
            'remaining_quantity': str(self.remaining_quantity),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        price_str = f"@{self.price}" if self.price else "MARKET"
        return f"{self.side.value.upper()} {self.quantity} {self.symbol} {price_str} ({self.status.value})"
    
    def __repr__(self) -> str:
        return f"Order({self.order_id[:8]}...)"
    
class Fill:
    """
    represents a fill aka partial or complete execution of an order
    """
    def __init__(self, order_id: str, quantity: Decimal, price: Decimal, timestamp: datetime):
        self.fill_id = str(uuid.uuid4())
        self.order_id = order_id
        self.quantity = Decimal(str(quantity))
        self.price = Decimal(str(price))
        self.timestamp = timestamp
    
    def to_dict(self) -> dict:
        return {
            'fill_id': self.fill_id,
            'order_id': self.order_id,
            'quantity': str(self.quantity),
            'price': str(self.price),
            'timestamp': self.timestamp.isoformat()
        }

