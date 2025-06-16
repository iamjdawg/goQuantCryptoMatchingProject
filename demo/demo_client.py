import asyncio
import aiohttp
import websockets
import json
import random
from decimal import Decimal
import time

class MatchingEngineDemo:
    def __init__(self, rest_url="http://localhost:8000", ws_url="ws://localhost:8001"):
        self.rest_url = rest_url
        self.ws_url = ws_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def submit_order(self, order_data):
        """Submit an order via REST API"""
        async with self.session.post(f"{self.rest_url}/api/v1/orders", json=order_data) as response:
            return await response.json()
    
    async def get_order_book(self, symbol):
        """Get order book via REST API"""
        async with self.session.get(f"{self.rest_url}/api/v1/orderbook/{symbol}") as response:
            return await response.json()
    
    async def get_bbo(self, symbol):
        """Get Best Bid Offer via REST API"""
        async with self.session.get(f"{self.rest_url}/api/v1/bbo/{symbol}") as response:
            return await response.json()
    
    async def get_trades(self, symbol, limit=10):
        """Get recent trades via REST API"""
        async with self.session.get(f"{self.rest_url}/api/v1/trades/{symbol}?limit={limit}") as response:
            return await response.json()
    
    async def listen_to_market_data(self, symbol, duration=30):
        """Listen to market data via WebSocket"""
        uri = f"{self.ws_url}/ws/market-data"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Subscribe to symbol
                subscribe_msg = {
                    "action": "subscribe",
                    "channel": "orderbook",
                    "symbol": symbol
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                print(f"Listening to {symbol} market data for {duration} seconds...")
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get('channel') == 'orderbook':
                            print(f"Order Book Update - {data['symbol']}")
                            print(f"  Best Bid: {data.get('best_bid', 'N/A')}")
                            print(f"  Best Ask: {data.get('best_ask', 'N/A')}")
                            print(f"  Spread: {data.get('spread', 'N/A')}")
                            print("-" * 40)
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    async def listen_to_trades(self, symbol, duration=30):
        """Listen to trade executions via WebSocket"""
        uri = f"{self.ws_url}/ws/trades"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Subscribe to trades
                subscribe_msg = {
                    "action": "subscribe",
                    "channel": "trades",
                    "symbol": symbol
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                print(f"Listening to {symbol} trades for {duration} seconds...")
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get('channel') == 'trades':
                            print(f"Trade Executed - {data['symbol']}")
                            print(f"  Price: {data['price']}")
                            print(f"  Quantity: {data['quantity']}")
                            print(f"  Side: {data['aggressor_side']}")
                            print(f"  Time: {data['timestamp']}")
                            print("-" * 40)
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            print(f"WebSocket error: {e}")

async def demo_basic_functionality():
    """Demonstrate basic matching engine functionality"""
    print("=== Basic Functionality Demo ===")
    
    async with MatchingEngineDemo() as demo:
        symbol = "BTC-USDT"
        
        # 1. Check initial state
        print("1. Checking initial order book...")
        order_book = await demo.get_order_book(symbol)
        print(f"Initial bids: {len(order_book.get('bids', []))}")
        print(f"Initial asks: {len(order_book.get('asks', []))}")
        
        # 2. Submit buy limit orders
        print("\n2. Submitting buy limit orders...")
        buy_orders = []
        for i in range(3):
            price = Decimal('50000') - Decimal(str(i * 100))
            order_data = {
                'symbol': symbol,
                'side': 'buy',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': str(price)
            }
            result = await demo.submit_order(order_data)
            buy_orders.append(result['order_id'])
            print(f"  Buy order at ${price}: {result['status']}")
        
        # 3. Submit sell limit orders
        print("\n3. Submitting sell limit orders...")
        sell_orders = []
        for i in range(3):
            price = Decimal('50200') + Decimal(str(i * 100))
            order_data = {
                'symbol': symbol,
                'side': 'sell',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': str(price)
            }
            result = await demo.submit_order(order_data)
            sell_orders.append(result['order_id'])
            print(f"  Sell order at ${price}: {result['status']}")
        
        # 4. Check BBO
        print("\n4. Checking Best Bid Offer...")
        bbo = await demo.get_bbo(symbol)
        print(f"  Best Bid: ${bbo.get('best_bid', 'N/A')}")
        print(f"  Best Ask: ${bbo.get('best_ask', 'N/A')}")
        print(f"  Spread: ${bbo.get('spread', 'N/A')}")
        
        # 5. Execute market order to create trade
        print("\n5. Executing market buy to create trade...")
        market_order = {
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': '0.5'
        }
        result = await demo.submit_order(market_order)
        print(f"  Market order result: {result['status']}")
        
        # 6. Check recent trades
        print("\n6. Checking recent trades...")
        trades = await demo.get_trades(symbol, 5)
        for trade in trades:
            print(f"  Trade: {trade['quantity']} @ ${trade['price']} - {trade['aggressor_side']}")

async def demo_order_types():
    """Demonstrate different order types"""
    print("\n=== Order Types Demo ===")
    
    async with MatchingEngineDemo() as demo:
        symbol = "ETH-USDT"
        
        # Set up initial liquidity
        print("Setting up initial liquidity...")
        await demo.submit_order({
            'symbol': symbol,
            'side': 'sell',
            'order_type': 'limit',
            'quantity': '2.0',
            'price': '3000.00'
        })
        
        # Test IOC order
        print("\n1. Testing IOC (Immediate or Cancel) order...")
        ioc_order = {
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'ioc',
            'quantity': '1.0',
            'price': '2950.00'  # Below market, should cancel
        }
        result = await demo.submit_order(ioc_order)
        print(f"  IOC result: {result['status']}")
        
        # Test FOK order
        print("\n2. Testing FOK (Fill or Kill) order...")
        fok_order = {
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'fok',
            'quantity': '5.0',  # More than available
            'price': '3100.00'
        }
        result = await demo.submit_order(fok_order)
        print(f"  FOK result: {result['status']}")
        
        # Test successful market order
        print("\n3. Testing market order...")
        market_order = {
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': '1.0'
        }
        result = await demo.submit_order(market_order)
        print(f"  Market order result: {result['status']}")

async def demo_websocket_feeds():
    """Demonstrate WebSocket market data and trade feeds"""
    print("\n=== WebSocket Feeds Demo ===")
    
    symbol = "BTC-USDT"
    
    # Start WebSocket listeners in background
    async def generate_orders():
        """Generate random orders to create market activity"""
        await asyncio.sleep(5)  # Wait for listeners to connect
        
        async with MatchingEngineDemo() as demo:
            for i in range(10):
                # Random buy order
                buy_price = random.uniform(49500, 49800)
                buy_order = {
                    'symbol': symbol,
                    'side': 'buy',
                    'order_type': 'limit',
                    'quantity': str(round(random.uniform(0.1, 1.0), 2)),
                    'price': str(round(buy_price, 2))
                }
                await demo.submit_order(buy_order)
                
                # Random sell order
                sell_price = random.uniform(50200, 50500)
                sell_order = {
                    'symbol': symbol,
                    'side': 'sell',
                    'order_type': 'limit',
                    'quantity': str(round(random.uniform(0.1, 1.0), 2)),
                    'price': str(round(sell_price, 2))
                }
                await demo.submit_order(sell_order)
                
                # Occasionally create trades with market orders
                if i % 3 == 0:
                    market_order = {
                        'symbol': symbol,
                        'side': random.choice(['buy', 'sell']),
                        'order_type': 'market',
                        'quantity': str(round(random.uniform(0.1, 0.5), 2))
                    }
                    await demo.submit_order(market_order)
                
                await asyncio.sleep(2)
    
    # Run WebSocket listeners and order generator concurrently
    async with MatchingEngineDemo() as demo:
        await asyncio.gather(
            demo.listen_to_market_data(symbol, 30),
            demo.listen_to_trades(symbol, 30),
            generate_orders()
        )

async def performance_test():
    """Simple performance test"""
    print("\n=== Performance Test ===")
    
    async with MatchingEngineDemo() as demo:
        symbol = "BTC-USDT"
        num_orders = 100
        
        print(f"Submitting {num_orders} orders...")
        start_time = time.time()
        
        tasks = []
        for i in range(num_orders):
            side = 'buy' if i % 2 == 0 else 'sell'
            base_price = 50000 if side == 'buy' else 50100
            price = base_price + random.randint(-50, 50)
            
            order_data = {
                'symbol': symbol,
                'side': side,
                'order_type': 'limit',
                'quantity': str(round(random.uniform(0.1, 1.0), 2)),
                'price': str(price)
            }
            task = demo.submit_order(order_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        successful_orders = sum(1 for r in results if r.get('status') == 'success')
        duration = end_time - start_time
        
        print(f"Results:")
        print(f"  Total orders: {num_orders}")
        print(f"  Successful: {successful_orders}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Orders per second: {successful_orders / duration:.2f}")

async def main():
    """Main demo function"""
    print("Starting Cryptocurrency Matching Engine Demo")
    print("=" * 50)
    
    try:
        await demo_basic_functionality()
        await asyncio.sleep(2)
        
        await demo_order_types()
        await asyncio.sleep(2)
        
        await performance_test()
        await asyncio.sleep(2)
        
        print("\nStarting WebSocket demo (will run for 30 seconds)...")
        await demo_websocket_feeds()
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Make sure the matching engine is running on:")
    print("  REST API: http://localhost:8000")
    print("  WebSocket: ws://localhost:8001")
    print("\nPress Ctrl+C to stop the demo\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo stopped by user")