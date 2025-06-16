import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Callable, Any
import json

from .order import Order, OrderType, OrderSide, OrderStatus
from .trade import Trade
from .orderbook import OrderBook

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchingEngine:
    """
    Core matching engine for processing orders and executing trades.
    """
    def __init__(self):
        # order books for each symbol
        self.order_books: Dict[str, OrderBook] = {}

        # trade history
        self.trades: List[Trade] = []
        self.trade_history: Dict[str, List[Trade]] = defaultdict(list)

        # order tracking
        self.all_orders : Dict[str, Order] = {}
        
        # event callbacks for real-time updates
        self.market_data_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        
        # Performance metrics
        self.total_orders_processed = 0
        self.total_trades_executed = 0
        
        logger.info("Matching engine initialized")

    async def start(self):
        """
        Initialize and start the matching engine.
        Called during application startup.
        """
        # Set running flag
        self._is_running = True
        logger.info("Matching engine started")
        return True
    
    async def stop(self):
        """
        Gracefully stop the matching engine.
        Called during application shutdown.
        """
        # Perform any cleanup needed
        self._is_running = False
        logger.info("Matching engine stopped")
        return True
    
    @property
    def is_running(self):
        """Check if matching engine is running."""
        return getattr(self, '_is_running', False)
    
    @property
    def symbols(self):
        """Return dictionary of active symbols and their order books."""
        return self.order_books

    def get_or_create_orderbook(self, symbol: str) -> OrderBook:
        """Get existing order book or create new one for symbol."""
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol)
            logger.info(f"Created new order book for {symbol}")
        return self.order_books[symbol]
    
    async def submit_order(self, order_request : dict) -> dict:
        """
        Submit a new order to the matching engine.
        :param order_request: Dictionary containing order details
        :return: Order details including order ID and status
        """
        try:
            # Create order object from request
            order = self._create_order_from_request(order_request)
            
            # Validate order
            if order.remaining_quantity <= 0:
                raise ValueError("Order quantity must be positive")
            
            # get order book
            order_book = self.get_or_create_orderbook(order.symbol)
            
            # store order BEFORE processing (important for order lookup)
            self.all_orders[order.order_id] = order
            
            logger.info(f"Processing order {order.order_id}: {order.side.value} {order.remaining_quantity} {order.symbol} @ {order.price}")
            
            # Process order and get trades
            trades = order_book.add_order(order)
            
            # Update metrics
            self.total_orders_processed += 1
            self.total_trades_executed += len(trades)

            # Store trades
            for trade in trades:
                self.trades.append(trade)
                self.trade_history[trade.symbol].append(trade)
                logger.info(f"Trade executed: {trade.quantity} {trade.symbol} @ {trade.price}")

            # notify subscribers
            await self._notify_market_data_update(order.symbol)
            for trade in trades:
                await self._notify_trade_execution(trade)

            # Enhanced logging
            if trades:
                logger.info(f"Order {order.order_id} generated {len(trades)} trades. Status: {order.status.value}, Remaining: {order.remaining_quantity}")
            else:
                logger.info(f"Order {order.order_id} added to book. Status: {order.status.value}, Remaining: {order.remaining_quantity}")

            result = {
                'order' : order.to_dict(),
                'trades' : [trade.to_dict() for trade in trades],
                'status': 'success'
            }

            return result
        
        except Exception as e:
            logger.error(f"Error processing order: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an existing order."""
        try:
            order = self.all_orders.get(order_id)
            if not order:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} not found'
                }
            
            # Check if order can be cancelled
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} cannot be cancelled (status: {order.status.value})'
                }
            
            # Get order book and cancel
            order_book = self.order_books.get(order.symbol)
            if order_book:
                cancelled = order_book.cancel_order(order_id)
                if cancelled:
                    logger.info(f"Cancelled order {order_id}")
                    await self._notify_market_data_update(order.symbol)
                    
                    return {
                        'status': 'success',
                        'order': order.to_dict()
                    }
            
            return {
                'status': 'error',
                'message': 'Failed to cancel order'
            }
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_order_book_depth(self, symbol: str, levels: int = 10) -> dict:
        """Get order book depth for a symbol."""
        order_book = self.order_books.get(symbol)
        if not order_book:
            return {
                'symbol': symbol,
                'bids': [],
                'asks': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        depth = order_book.get_depth(levels)
        depth['timestamp'] = datetime.now(timezone.utc).isoformat()
        return depth
    
    def get_bbo(self, symbol: str) -> dict:
        """Get Best Bid and Offer for a symbol."""
        order_book = self.order_books.get(symbol)
        if not order_book:
            return {
                'symbol': symbol,
                'best_bid': None,
                'best_ask': None,
                'spread': None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        best_bid, best_ask = order_book.get_bbo()
        spread = order_book.get_spread()
        
        return {
            'symbol': symbol,
            'best_bid': str(best_bid) if best_bid else None,
            'best_ask': str(best_ask) if best_ask else None,
            'spread': str(spread) if spread else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        """Get recent trades for a symbol."""
        trades = self.trade_history.get(symbol, [])
        recent_trades = trades[-limit:] if trades else []
        return [trade.to_dict() for trade in recent_trades]
    
    def get_order_status(self, order_id: str) -> dict:
        """Get status of a specific order."""
        order = self.all_orders.get(order_id)
        if not order:
            return {
                'status': 'error',
                'message': 'Order not found'
            }
        
        return {
            'status': 'success',
            'order': order.to_dict()
        }
    
    async def get_statistics(self) -> dict:
        """Get engine statistics."""
        active_symbols = list(self.order_books.keys())
        
        stats = {
            'total_orders_processed': self.total_orders_processed,
            'total_trades_executed': self.total_trades_executed,
            'active_symbols': active_symbols,
            'total_symbols': len(active_symbols),
            'uptime': datetime.now(timezone.utc).isoformat()
        }
        
        # Add per-symbol stats
        for symbol in active_symbols:
            order_book = self.order_books[symbol]
            bbo = order_book.get_bbo()
            stats[f'{symbol}_best_bid'] = str(bbo[0]) if bbo[0] else None
            stats[f'{symbol}_best_ask'] = str(bbo[1]) if bbo[1] else None
            stats[f'{symbol}_trades'] = len(self.trade_history.get(symbol, []))
        
        return stats
    
    def subscribe_to_market_data(self, callback: Callable):
        """Subscribe to market data updates."""
        self.market_data_callbacks.append(callback)
    
    def subscribe_to_trades(self, callback: Callable):
        """Subscribe to trade execution updates."""
        self.trade_callbacks.append(callback)
    
    def _create_order_from_request(self, request: dict) -> Order:
        """Create Order object from request dictionary."""
        # Required fields
        symbol = request.get('symbol')
        order_type_str = request.get('order_type', '').lower()
        side_str = request.get('side', '').lower()
        quantity = request.get('quantity')
        price = request.get('price')
        
        # Validation
        if not symbol:
            raise ValueError("Symbol is required")
        
        # Convert symbol to uppercase for consistency
        symbol = symbol.upper()
        
        if order_type_str not in ['market', 'limit', 'ioc', 'fok']:
            raise ValueError(f"Invalid order type: {order_type_str}")
        
        if side_str not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {side_str}")
        
        if not quantity or quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Convert to enums
        order_type = OrderType(order_type_str.upper())  # Ensure uppercase for enum
        side = OrderSide(side_str.upper())  # Ensure uppercase for enum

        # Safely convert quantity to Decimal
        try:
            decimal_quantity = Decimal(str(quantity))
            if decimal_quantity <= 0:
                raise ValueError("Quantity must be greater than zero")
        except (ValueError, InvalidOperation) as e:
            logger.error(f"Invalid quantity format: {quantity}, error: {e}")
            raise ValueError(f"Invalid quantity format: {quantity}")

        # Handle price - market orders don't need price
        decimal_price = None
        if order_type != OrderType.MARKET:  # Only require price for non-market orders
            if price is None:
                raise ValueError(f"Price is required for {order_type_str} orders")
            try:
                decimal_price = Decimal(str(price))
                if decimal_price <= 0:
                    raise ValueError("Price must be greater than zero")
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Invalid price format: {price}, error: {e}")
                raise ValueError(f"Invalid price format: {price}")

        # Create order
        order = Order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=decimal_quantity,
            price=decimal_price,
            order_id=request.get('order_id')  # Optional custom order ID
        )
        
        # Log order creation for debugging
        logger.debug(f"Created order: {order.order_id} - {side.value} {decimal_quantity} {symbol} @ {decimal_price}")
        
        return order
    
    async def _notify_market_data_update(self, symbol: str):
        """Notify all market data subscribers of an update."""
        if not self.market_data_callbacks:
            return
        
        try:
            # Get updated market data
            depth_data = self.get_order_book_depth(symbol)
            bbo_data = self.get_bbo(symbol)
            
            # Combine data
            market_data = {
                'type': 'market_data_update',
                'symbol': symbol,
                'depth': depth_data,
                'bbo': bbo_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Notify all subscribers
            for callback in self.market_data_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(market_data)
                    else:
                        callback(market_data)
                except Exception as e:
                    logger.error(f"Error in market data callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying market data update: {e}")

    async def _notify_trade_execution(self, trade: Trade):
        """Notify all trade subscribers of a new trade."""
        if not self.trade_callbacks:
            return
        
        try:
            trade_data = {
                'type': 'trade_execution',
                **trade.to_dict()
            }
            
            # Notify all subscribers
            for callback in self.trade_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(trade_data)
                    else:
                        callback(trade_data)
                except Exception as e:
                    logger.error(f"Error in trade callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying trade execution: {e}")

# Global matching engine instance
matching_engine = MatchingEngine()


