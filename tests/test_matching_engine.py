import pytest
import asyncio
from decimal import Decimal
from src.core.matching_engine import MatchingEngine
from src.core.order import Order, OrderSide, OrderType, OrderStatus
from src.core.trade import Trade

class TestMatchingEngine:
    
    @pytest.fixture
    def engine(self):
        return MatchingEngine()
    
    @pytest.fixture
    def sample_orders(self):
        return {
            'buy_limit': {
                'symbol': 'BTC-USDT',
                'side': 'buy',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': '50000.00'
            },
            'sell_limit': {
                'symbol': 'BTC-USDT',
                'side': 'sell',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': '50100.00'
            },
            'buy_market': {
                'symbol': 'BTC-USDT',
                'side': 'buy',
                'order_type': 'market',
                'quantity': '0.5'
            }
        }
    @pytest.mark.asyncio
    async def test_submit_limit_order(self, engine, sample_orders):
        """Test submitting a limit order"""
        result = await engine.submit_order(sample_orders['buy_limit'])
        
        assert result['status'] == 'success'
        assert 'order_id' in result
        assert result['order']['status'] == 'pending'

    @pytest.mark.asyncio
    async def test_price_time_priority(self, engine, sample_orders):
        """Test price-time priority matching"""
        # Submit first buy order
        order1 = sample_orders['buy_limit'].copy()
        order1['price'] = '50000.00'
        result1 = await engine.submit_order(order1)
        
        # Submit second buy order with same price (should be behind in time)
        order2 = sample_orders['buy_limit'].copy()
        order2['price'] = '50000.00'
        result2 = await engine.submit_order(order2)
        
        # Submit sell order that matches
        sell_order = sample_orders['sell_limit'].copy()
        sell_order['price'] = '49999.00'  # Will match with both buys
        result3 = await engine.submit_order(sell_order)
        
        # First order should be filled first due to time priority
        order1_status = engine.get_order_status(result1['order_id'])
        assert order1_status['status'] == 'filled'

    @pytest.mark.asyncio
    async def test_market_order_execution(self, engine, sample_orders):
        """Test market order immediate execution"""
        # First, place a sell limit order
        await engine.submit_order(sample_orders['sell_limit'])
        
        # Then place a market buy order
        result = await engine.submit_order(sample_orders['buy_market'])
        
        assert result['status'] == 'success'
        # Market order should be filled immediately
        order_status = engine.get_order_status(result['order_id'])
        assert order_status['status'] == 'filled'

    @pytest.mark.asyncio
    async def test_ioc_order(self, engine, sample_orders):
        """Test Immediate or Cancel order"""
        ioc_order = {
            'symbol': 'BTC-USDT',
            'side': 'buy',
            'order_type': 'ioc',
            'quantity': '1.0',
            'price': '49000.00'  # Below market, won't match
        }
        
        result = await engine.submit_order(ioc_order)
        
        # IOC order should be cancelled if not immediately filled
        order_status = engine.get_order_status(result['order_id'])
        assert order_status['status'] == 'cancelled'
    
    @pytest.mark.asyncio
    async def test_fok_order(self, engine, sample_orders):
        """Test Fill or Kill order"""
        # Place partial liquidity
        partial_sell = sample_orders['sell_limit'].copy()
        partial_sell['quantity'] = '0.5'  # Only half the quantity
        await engine.submit_order(partial_sell)
        
        # FOK order requiring full fill
        fok_order = {
            'symbol': 'BTC-USDT',
            'side': 'buy',
            'order_type': 'fok',
            'quantity': '1.0',  # More than available
            'price': '50200.00'
        }
        
        result = await engine.submit_order(fok_order)
        
        # FOK should be cancelled if cannot be fully filled
        order_status = engine.get_order_status(result['order_id'])
        assert order_status['status'] == 'cancelled'
    
    def test_bbo_calculation(self, engine, sample_orders):
        """Test Best Bid Offer calculation"""
        # Initially no BBO
        bbo = engine.get_bbo('BTC-USDT')
        assert bbo['best_bid'] is None
        assert bbo['best_ask'] is None
        
        # Add orders and check BBO
        asyncio.run(engine.submit_order(sample_orders['buy_limit']))
        asyncio.run(engine.submit_order(sample_orders['sell_limit']))
        
        bbo = engine.get_bbo('BTC-USDT')
        assert bbo['best_bid'] == '50000.00'
        assert bbo['best_ask'] == '50100.00'
        assert bbo['spread'] == '100.00'
    
    def test_order_book_depth(self, engine, sample_orders):
        """Test order book depth calculation"""
        # Add multiple orders at different price levels
        for i in range(5):
            buy_order = sample_orders['buy_limit'].copy()
            buy_order['price'] = str(Decimal('50000.00') - Decimal(str(i * 10)))
            asyncio.run(engine.submit_order(buy_order))
            
            sell_order = sample_orders['sell_limit'].copy()
            sell_order['price'] = str(Decimal('50100.00') + Decimal(str(i * 10)))
            asyncio.run(engine.submit_order(sell_order))
        
        depth = engine.get_order_book_depth('BTC-USDT', levels=3)
        
        assert len(depth['bids']) <= 3
        assert len(depth['asks']) <= 3
        # Prices should be sorted correctly
        for i in range(len(depth['bids']) - 1):
            assert Decimal(depth['bids'][i][0]) > Decimal(depth['bids'][i+1][0])
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, engine, sample_orders):
        """Test order cancellation"""
        result = await engine.submit_order(sample_orders['buy_limit'])
        order_id = result['order_id']
        
        # Cancel the order
        cancel_result = await engine.cancel_order(order_id)
        assert cancel_result['status'] == 'success'
        
        # Check order status
        order_status = engine.get_order_status(order_id)
        assert order_status['status'] == 'cancelled'
    
    def test_no_trade_through(self, engine, sample_orders):
        """Test that orders don't trade through better prices"""
        # Place multiple sell orders at different prices
        sell_orders = []
        for price in ['50000.00', '50010.00', '50020.00']:
            sell_order = sample_orders['sell_limit'].copy()
            sell_order['price'] = price
            result = asyncio.run(engine.submit_order(sell_order))
            sell_orders.append(result['order_id'])
        
        # Place a market buy order
        buy_order = sample_orders['buy_market'].copy()
        buy_order['quantity'] = '0.5'  # Should only match with best price
        result = asyncio.run(engine.submit_order(buy_order))
        
        # Should have matched with the best (lowest) sell price first
        trades = engine.get_recent_trades('BTC-USDT', 1)
        assert len(trades) == 1
        assert trades[0]['price'] == '50000.00'

        