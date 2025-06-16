from collections import defaultdict, deque
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Deque
import heapq
import logging
from .order import Order, OrderType, OrderSide, OrderStatus
from .trade import Trade

class PriceLevel:
    """
    Represents a price level in the order book.
    Contains a priority queue of orders at that price.
    """
    def __init__(self, price: Decimal):
        self.price = price
        self.orders: Deque[Order] = deque()  # fifo queue for time priority
        self.total_quantity: Decimal = Decimal('0.0')

    def add_order(self, order: Order):
        """Add an order to this price level."""
        self.orders.append(order)
        self.total_quantity += order.remaining_quantity

    def remove_order(self, order: Order):
        """Remove an order from this price level. returns true if found and removed"""
        try:
            self.orders.remove(order)
            self.total_quantity -= order.remaining_quantity
            return True 
        except ValueError:
            return False
        
    def get_first_order(self) -> Optional[Order]:
        """Get the oldest order without removing it"""
        if self.orders:
            return self.orders[0]
        return None
        
    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def pop_first_order(self) -> Optional[Order]:
        if self.orders:
            order = self.orders.popleft()
            self.total_quantity -= order.remaining_quantity
            return order
        return None
    
logger = logging.getLogger(__name__)

class OrderBook:
    """
    order book with price-time priority matching
        Uses heaps for efficient best price access and price levels for FIFO ordering.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        # price levels: using dict for O(1) access by price
        self.bid_levels: Dict[Decimal, PriceLevel] = {} # buy orders
        self.ask_levels: Dict[Decimal, PriceLevel] = {} # sell orders

        # heaps for best price access
        self.bid_prices: List[Decimal] = []  # max-heap for bids
        self.ask_prices: List[Decimal] = []

        # order lookup for fast access
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        
        # best bid/offer cache
        self._best_bid: Optional[Decimal] = None
        self._best_ask: Optional[Decimal] = None

    def add_order(self, order: Order) -> List[Trade]:
        """
        add an order to the book. returns list of trades if order is marketable
        """
        if order.symbol != self.symbol:
            raise ValueError(f"Order symbol {order.symbol} does not match order book symbol {self.symbol}")
        
        # store order for lookup
        self.orders[order.order_id] = order
        # check if order is marketable
        trades = []
        if self._is_marketable(order):
            trades = self._match_order(order)
        
        # add remaining quantity to book if its resting order type
        if order.remaining_quantity > 0 and order.order_type in [OrderType.LIMIT]:
            self._add_to_book(order)
        
        return trades
    
    def cancel_order(self, order_id: str) -> bool:
        """ returns true if successfully cancelled """
        order = self.orders.get(order_id)
        if not order:
            return False
        removed = self._remove_from_book(order)
        if removed:
            order.cancel()
            return True
        return False
    
    def get_best_bid(self) -> Optional[Decimal]:
        """Get the highest bid price."""
        self._update_best_prices()
        return self._best_bid
    
    def get_best_ask(self) -> Optional[Decimal]:
        """Get the lowest ask price."""
        self._update_best_prices()
        return self._best_ask
    
    def get_spread(self) -> Optional[Decimal]:
        """Get the bid-ask spread."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return ask - bid
        return None
    
    def get_bbo(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Get Best Bid and Offer (BBO)."""
        return self.get_best_bid(), self.get_best_ask()
    
    def get_depth(self, levels: int = 10) -> Dict:
        """
        get order book depth upto specified levels
        """
        self._update_best_prices()

        # get bid levels
        bids = []
        bid_prices_sorted = sorted([p for p in self.bid_levels.keys() if not self.bid_levels[p].is_empty()], reverse=True)
        for price in bid_prices_sorted[:levels]:
            level = self.bid_levels[price]
            bids.append([str(price), str(level.total_quantity)])

        # get ask levels
        asks = []
        ask_prices_sorted = sorted([p for p in self.ask_levels.keys() if not self.ask_levels[p].is_empty()])
        for price in ask_prices_sorted[:levels]:
            level = self.ask_levels[price]
            asks.append([str(price), str(level.total_quantity)])
        
        return {
            'symbol': self.symbol,
            'bids': bids,
            'asks': asks
        }

    def _is_marketable(self, order: Order) -> bool:
        """check if an order can be matched immediately"""
        if order.is_market_order:
            return True
        
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if order.is_buy and best_ask and order.price >= best_ask:
            return True
        elif order.is_sell and best_bid and order.price <= best_bid:
            return True
        
        return False
    
    def _match_order(self, incoming_order : Order) -> List[Trade]:
        """
        Match an incoming order against the book.
        Implements price-time priority and internal order protection.
        """
        trades = []
        
        if incoming_order.is_buy:
            # match against asks(sell orders)
            opposing_levels = self.ask_levels
            opposing_prices = self.ask_prices
            price_comparator = lambda price : price <= (incoming_order.price or Decimal('inf'))
        else:
            # match against bids(buy orders)
            opposing_levels = self.bid_levels
            opposing_prices = self.bid_prices
            price_comparator = lambda price : price >= (incoming_order.price or Decimal('0.0'))

        # Continue matching while there are opposing orders and incoming order has remaining quantity
        while incoming_order.remaining_quantity > 0:
            # get best opposing price level
            best_price = self._get_best_opposing_price(incoming_order.is_buy)
            if not best_price:
                break

            # check if match at this price is possible
            if not incoming_order.is_market_order and not price_comparator(best_price):
                break

            # get the price level
            price_level = opposing_levels[best_price]
            if price_level.is_empty():
                self._remove_price_level(best_price, incoming_order.is_buy)
                continue

            # match with orders at this price level
            while not price_level.is_empty() and incoming_order.remaining_quantity > 0:
                resting_order = price_level.get_first_order()
                if not resting_order:
                    break

                # figure out the trade quantity
                trade_quantity = min(incoming_order.remaining_quantity, resting_order.remaining_quantity)
                trade_price = resting_order.price

                trade = Trade(
                    symbol=self.symbol,
                    price=trade_price,
                    quantity=trade_quantity,
                    maker_order_id=resting_order.order_id,  # resting order
                    taker_order_id=incoming_order.order_id,  # incoming order
                    aggressor_side=incoming_order.side  # side of the incoming order
                )
                trades.append(trade)

                # fill both orders
                resting_order.fill(trade_quantity, trade_price)
                incoming_order.fill(trade_quantity, trade_price)

                # remove resting order if fully filled
                if resting_order.is_filled:
                    price_level.pop_first_order()
                else:
                    price_level.total_quantity -= trade_quantity
            
            if price_level.is_empty():
                self._remove_empty_price_level(best_price, incoming_order.is_buy)
            
        
        # handle IOC and FOK orders
        if incoming_order.order_type == OrderType.IOC and incoming_order.remaining_quantity > 0:
            # cancel remaining quantity
            incoming_order.cancel()
        elif incoming_order.order_type == OrderType.FOK and not incoming_order.is_filled:
            incoming_order.cancel()
        return trades
    
    def _add_to_book(self, order: Order):
        """Add order to the appropriate side of the book."""
        if order.is_buy:
            levels = self.bid_levels
            prices = self.bid_prices
        else:
            levels = self.ask_levels
            prices = self.ask_prices
        
        price = order.price
        
        # Create price level if it doesn't exist
        if price not in levels:
            levels[price] = PriceLevel(price)
            if order.is_buy:
                heapq.heappush(prices, -price)  # Negative for max-heap
            else:
                heapq.heappush(prices, price)
        
        # Add order to price level
        levels[price].add_order(order)
    
    def _remove_from_book(self, order: Order) -> bool:
        """Remove order from the book."""
        if order.is_buy:
            levels = self.bid_levels
        else:
            levels = self.ask_levels
        
        price = order.price
        if price in levels:
            level = levels[price]
            removed = level.remove_order(order)
            
            # Remove empty price level
            if level.is_empty():
                self._remove_empty_price_level(price, order.is_buy)
            
            return removed
        
        return False
    
    def _get_best_opposing_price(self, is_buy_order: bool) -> Optional[Decimal]:
        """Get the best price on the opposing side."""
        if is_buy_order:
            return self.get_best_ask()
        else:
            return self.get_best_bid()
    
    def _remove_empty_price_level(self, price: Decimal, from_buy_side: bool):
        """Remove empty price level and update heaps."""
        if from_buy_side:
            if price in self.bid_levels:
                del self.bid_levels[price]
        else:
            if price in self.ask_levels:
                del self.ask_levels[price]
        
        # Note: We don't remove from heaps immediately for performance
        # Instead, we handle empty levels when accessing the heap
    
    def _update_best_prices(self):
        """Update cached best bid and ask prices."""
        # Update best bid (highest buy price)
        self._best_bid = None
        while self.bid_prices:
            price = -self.bid_prices[0]  # Convert back from negative
            if price in self.bid_levels and not self.bid_levels[price].is_empty():
                self._best_bid = price
                break
            else:
                heapq.heappop(self.bid_prices)  # Remove stale price
        
        # Update best ask (lowest sell price)
        self._best_ask = None
        while self.ask_prices:
            price = self.ask_prices[0]
            if price in self.ask_levels and not self.ask_levels[price].is_empty():
                self._best_ask = price
                break
            else:
                heapq.heappop(self.ask_prices)  # Remove stale price
