import pytest
import httpx
import asyncio
from fastapi.testclient import TestClient
from src.api.rest_api import create_rest_api
from src.core.matching_engine import MatchingEngine

class TestRestAPI:
    
    @pytest.fixture
    def client(self):
        engine = MatchingEngine()
        app = create_rest_api(engine)
        return TestClient(app)
    
    def test_submit_order_endpoint(self, client):
        """Test order submission endpoint"""
        order_data = {
            'symbol': 'BTC-USDT',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': '1.0',
            'price': '50000.00'
        }
        
        response = client.post('/api/v1/orders', json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'success'
        assert 'order_id' in data
    
    def test_get_order_book(self, client):
        """Test order book endpoint"""
        # First submit some orders
        order_data = {
            'symbol': 'BTC-USDT',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': '1.0',
            'price': '50000.00'
        }
        client.post('/api/v1/orders', json=order_data)
        
        # Get order book
        response = client.get('/api/v1/orderbook/BTC-USDT')
        assert response.status_code == 200
        
        data = response.json()
        assert 'bids' in data
        assert 'asks' in data
    
    def test_get_bbo(self, client):
        """Test BBO endpoint"""
        response = client.get('/api/v1/bbo/BTC-USDT')
        assert response.status_code == 200
        
        data = response.json()
        assert 'best_bid' in data
        assert 'best_ask' in data
        assert 'spread' in data
    
    def test_invalid_order_validation(self, client):
        """Test order validation"""
        invalid_order = {
            'symbol': 'BTC-USDT',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': '0',  # Invalid quantity
            'price': '50000.00'
        }
        
        response = client.post('/api/v1/orders', json=invalid_order)
        assert response.status_code == 400
