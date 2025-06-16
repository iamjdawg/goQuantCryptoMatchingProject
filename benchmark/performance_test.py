import asyncio
import aiohttp
import time
import statistics
import psutil
import json
from decimal import Decimal
import random
from typing import List, Dict
import sys
import os

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.matching_engine import MatchingEngine
from src.core.order import OrderSide, OrderType

class PerformanceBenchmark:
    def __init__(self, rest_url="http://localhost:8000"):
        self.rest_url = rest_url
        self.session = None
        self.results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def submit_order_with_timing(self, order_data):
        """Submit order and measure response time"""
        start_time = time.perf_counter()
        
        try:
            async with self.session.post(f"{self.rest_url}/api/v1/orders", json=order_data) as response:
                result = await response.json()
                end_time = time.perf_counter()
                
                return {
                    'success': response.status == 200,
                    'latency': (end_time - start_time) * 1000,  # Convert to milliseconds
                    'result': result
                }
        except Exception as e:
            end_time = time.perf_counter()
            return {
                'success': False,
                'latency': (end_time - start_time) * 1000,
                'error': str(e)
            }
    
    async def benchmark_order_throughput(self, num_orders: int = 1000, concurrent_limit: int = 100):
        """Benchmark order submission throughput"""
        print(f"Benchmarking order throughput: {num_orders} orders, {concurrent_limit} concurrent")
        
        # Generate test orders
        orders = []
        for i in range(num_orders):
            side = 'buy' if i % 2 == 0 else 'sell'
            base_price = 50000 if side == 'buy' else 50100
            price = base_price + random.randint(-100, 100)
            
            order = {
                'symbol': 'BTC-USDT',
                'side': side,
                'order_type': 'limit',
                'quantity': str(round(random.uniform(0.1, 2.0), 3)),
                'price': str(price)
            }
            orders.append(order)
        
        # Process orders in batches
        latencies = []
        successful_orders = 0
        failed_orders = 0
        
        start_time = time.perf_counter()
        
        for i in range(0, len(orders), concurrent_limit):
            batch = orders[i:i + concurrent_limit]
            tasks = [self.submit_order_with_timing(order) for order in batch]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict):
                    latencies.append(result['latency'])
                    if result['success']:
                        successful_orders += 1
                    else:
                        failed_orders += 1
                else:
                    failed_orders += 1
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        self.results['throughput'] = {
            'total_orders': num_orders,
            'successful_orders': successful_orders,
            'failed_orders': failed_orders,
            'total_duration': total_duration,
            'orders_per_second': successful_orders / total_duration,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'median_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': self.percentile(latencies, 95) if latencies else 0,
            'p99_latency_ms': self.percentile(latencies, 99) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0
        }
        
        return self.results['throughput']
    
    def benchmark_matching_engine_direct(self, num_orders: int = 10000):
        """Benchmark matching engine directly (without API overhead)"""
        print(f"Benchmarking matching engine directly: {num_orders} orders")
        
        engine = MatchingEngine()
        
        # Generate test orders
        orders = []
        for i in range(num_orders):
            side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
            base_price = Decimal('50000') if side == OrderSide.BUY else Decimal('50100')
            price = base_price + Decimal(str(random.randint(-100, 100)))
            
            order_request = {
                'symbol': 'BTC-USDT',
                'side': side.value,
                'order_type': 'limit',
                'quantity': str(round(random.uniform(0.1, 2.0), 3)),
                'price': str(price)
            }
            orders.append(order_request)
        
        # Measure memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process orders and measure time
        latencies = []
        successful_orders = 0
        
        start_time = time.perf_counter()
        
        for order_request in orders:
            order_start = time.perf_counter()
            
            try:
                result = asyncio.run(engine.submit_order(order_request))
                order_end = time.perf_counter()
                
                latencies.append((order_end - order_start) * 1000000)  # microseconds
                if result.get('status') == 'success':
                    successful_orders += 1
            except Exception as e:
                print(f"Order failed: {e}")
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        self.results['direct_engine'] = {
            'total_orders': num_orders,
            'successful_orders': successful_orders,
            'total_duration': total_duration,
            'orders_per_second': successful_orders / total_duration,
            'avg_latency_us': statistics.mean(latencies) if latencies else 0,
            'median_latency_us': statistics.median(latencies) if latencies else 0,
            'p95_latency_us': self.percentile(latencies, 95) if latencies else 0,
            'p99_latency_us': self.percentile(latencies, 99) if latencies else 0,
            'min_latency_us': min(latencies) if latencies else 0,
            'max_latency_us': max(latencies) if latencies else 0,
            'memory_usage_mb': memory_after - memory_before
        }
        
        return self.results['direct_engine']
    
    async def benchmark_bbo_updates(self, num_updates: int = 1000):
        """Benchmark BBO calculation speed"""
        print(f"Benchmarking BBO updates: {num_updates} requests")
        
        # First, populate the order book
        await self.populate_order_book()
        
        latencies = []
        start_time = time.perf_counter()
        
        for _ in range(num_updates):
            bbo_start = time.perf_counter()
            
            try:
                async with self.session.get(f"{self.rest_url}/api/v1/bbo/BTC-USDT") as response:
                    await response.json()
                    bbo_end = time.perf_counter()
                    latencies.append((bbo_end - bbo_start) * 1000)  # milliseconds
            except Exception as e:
                print(f"BBO request failed: {e}")
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        self.results['bbo_updates'] = {
            'total_requests': num_updates,
            'total_duration': total_duration,
            'requests_per_second': num_updates / total_duration,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'median_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': self.percentile(latencies, 95) if latencies else 0,
            'p99_latency_ms': self.percentile(latencies, 99) if latencies else 0
        }
        
        return self.results['bbo_updates']
    
    async def populate_order_book(self, num_levels: int = 20):
        """Populate order book with test data"""
        tasks = []
        
        # Add buy orders
        for i in range(num_levels):
            price = 50000 - (i * 10)
            order = {
                'symbol': 'BTC-USDT',
                'side': 'buy',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': str(price)
            }
            tasks.append(self.submit_order_with_timing(order))
        
        # Add sell orders
        for i in range(num_levels):
            price = 50100 + (i * 10)
            order = {
                'symbol': 'BTC-USDT',
                'side': 'sell',
                'order_type': 'limit',
                'quantity': '1.0',
                'price': str(price)
            }
            tasks.append(self.submit_order_with_timing(order))
        
        await asyncio.gather(*tasks)
    
    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * p / 100
        lower = int(index)
        upper = lower + 1
        weight = index - lower
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def generate_report(self):
        """Generate performance report"""
        report = []
        report.append("=" * 60)
        report.append("CRYPTOCURRENCY MATCHING ENGINE PERFORMANCE REPORT")
        report.append("=" * 60)
        
        if 'throughput' in self.results:
            data = self.results['throughput']
            report.append("\n📊 API THROUGHPUT BENCHMARK")
            report.append("-" * 30)
            report.append(f"Total Orders:           {data['total_orders']:,}")
            report.append(f"Successful Orders:      {data['successful_orders']:,}")
            report.append(f"Failed Orders:          {data['failed_orders']:,}")
            report.append(f"Success Rate:           {data['successful_orders']/data['total_orders']*100:.2f}%")
            report.append(f"Duration:               {data['total_duration']:.2f} seconds")
            report.append(f"Orders per Second:      {data['orders_per_second']:.2f}")
            report.append(f"Average Latency:        {data['avg_latency_ms']:.2f} ms")
            report.append(f"Median Latency:         {data['median_latency_ms']:.2f} ms")
            report.append(f"95th Percentile:        {data['p95_latency_ms']:.2f} ms")
            report.append(f"99th Percentile:        {data['p99_latency_ms']:.2f} ms")
            report.append(f"Min Latency:            {data['min_latency_ms']:.2f} ms")
            report.append(f"Max Latency:            {data['max_latency_ms']:.2f} ms")
        
        if 'direct_engine' in self.results:
            data = self.results['direct_engine']
            report.append("\n⚡ DIRECT ENGINE BENCHMARK")
            report.append("-" * 30)
            report.append(f"Total Orders:           {data['total_orders']:,}")
            report.append(f"Successful Orders:      {data['successful_orders']:,}")
            report.append(f"Duration:               {data['total_duration']:.2f} seconds")
            report.append(f"Orders per Second:      {data['orders_per_second']:.2f}")
            report.append(f"Average Latency:        {data['avg_latency_us']:.2f} μs")
            report.append(f"Median Latency:         {data['median_latency_us']:.2f} μs")
            report.append(f"95th Percentile:        {data['p95_latency_us']:.2f} μs")
            report.append(f"99th Percentile:        {data['p99_latency_us']:.2f} μs")
            report.append(f"Memory Usage:           {data['memory_usage_mb']:.2f} MB")
        
        if 'bbo_updates' in self.results:
            data = self.results['bbo_updates']
            report.append("\n📈 BBO UPDATE BENCHMARK")
            report.append("-" * 30)
            report.append(f"Total Requests:         {data['total_requests']:,}")
            report.append(f"Duration:               {data['total_duration']:.2f} seconds")
            report.append(f"Requests per Second:    {data['requests_per_second']:.2f}")
            report.append(f"Average Latency:        {data['avg_latency_ms']:.2f} ms")
            report.append(f"Median Latency:         {data['median_latency_ms']:.2f} ms")
            report.append(f"95th Percentile:        {data['p95_latency_ms']:.2f} ms")
            report.append(f"99th Percentile:        {data['p99_latency_ms']:.2f} ms")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def save_report(self, filename: str = "performance_report.txt"):
        """Save performance report to file"""
        report = self.generate_report()
        with open(filename, 'w') as f:
            f.write(report)
        
        # Also save raw data as JSON
        json_filename = filename.replace('.txt', '.json')
        with open(json_filename, 'w') as f:
            json.dump(self.results, f, indent=2)

async def main():
    """Run comprehensive performance benchmark"""
    print("Starting Comprehensive Performance Benchmark")
    print("=" * 50)
    
    async with PerformanceBenchmark() as benchmark:
        try:
            # Test API throughput
            print("\n1. Testing API throughput...")
            await benchmark.benchmark_order_throughput(num_orders=500, concurrent_limit=50)
            
            # Test direct engine performance
            print("\n2. Testing direct engine performance...")
            benchmark.benchmark_matching_engine_direct(num_orders=5000)
            
            # Test BBO update speed
            print("\n3. Testing BBO update speed...")
            await benchmark.benchmark_bbo_updates(num_updates=1000)
            
            # Generate and display report
            report = benchmark.generate_report()
            print("\n" + report)
            
            # Save report
            benchmark.save_report("benchmark_results.txt")
            print(f"\nDetailed results saved to benchmark_results.txt and benchmark_results.json")
            
        except Exception as e:
            print(f"Benchmark failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Make sure the matching engine is running on http://localhost:8000")
    print("Press Ctrl+C to stop the benchmark\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBenchmark stopped by user")